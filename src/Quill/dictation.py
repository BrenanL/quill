#!/usr/bin/env python3
"""
Quill Simple Dictation Service

A minimal, streaming dictation service that:
- Listens for hotkey (Ctrl+Shift+D) to start/stop recording
- Detects pauses in speech and transcribes segments immediately
- Injects text as you speak (streaming)

Usage:
    python -m Quill.dictation
"""

import sys
import time
import threading
from typing import Optional, List

import numpy as np
import sounddevice as sd
import keyboard
from faster_whisper import WhisperModel


# =============================================================================
# Configuration (hardcoded for simplicity)
# =============================================================================

HOTKEY = "ctrl+shift+d"
MODEL_SIZE = "base"           # "base" is better for streaming than "tiny"
DEVICE = "cpu"                # Or "cuda" if available
COMPUTE_TYPE = "int8"         # CPU-compatible
SAMPLE_RATE = 16000           # Whisper requirement

# Streaming mode
STREAMING_ENABLED = True      # Set to True for VAD-based chunking
                              # Set to False for batch mode (transcribe all at end)

# VAD settings (only used if STREAMING_ENABLED=True)
MIN_CHUNK_SECONDS = 5.0       # Minimum audio before transcribing (for accuracy)
MAX_CHUNK_SECONDS = 30.0      # Force transcribe after this duration
VAD_THRESHOLD = 0.5           # Speech detection sensitivity (0-1)
MIN_SILENCE_MS = 700          # Silence duration to consider speech ended

# Auto-stop settings
AUTO_STOP_SILENCE_SECONDS = 20  # Auto-stop recording after this much silence


# =============================================================================
# PauseDetector - detects pauses in speech using RMS energy
# =============================================================================

class PauseDetector:
    """Detects pauses in speech using simple RMS energy threshold."""

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = 0.02,
        min_pause_ms: int = 500,
        max_segment_s: int = 10,
    ):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.min_pause_samples = int(sample_rate * min_pause_ms / 1000)
        self.max_segment_samples = int(sample_rate * max_segment_s)

        self.consecutive_silent = 0
        self.total_samples = 0
        self.segment_audio: List[np.ndarray] = []

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Process an audio chunk and return a complete segment if pause detected.

        Args:
            audio_chunk: Audio data (float32, mono)

        Returns:
            Complete audio segment if pause detected, None otherwise
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_chunk**2))

        # Track silence
        if rms < self.silence_threshold:
            self.consecutive_silent += len(audio_chunk)
        else:
            self.consecutive_silent = 0

        # Add to buffer
        self.segment_audio.append(audio_chunk)
        self.total_samples += len(audio_chunk)

        # Check for pause (silence threshold met and we have audio)
        pause_detected = (
            self.consecutive_silent >= self.min_pause_samples
            and len(self.segment_audio) > 1
            and self.total_samples > self.min_pause_samples  # Don't trigger on initial silence
        )

        # Check for max duration (force chunk)
        max_reached = self.total_samples >= self.max_segment_samples

        if pause_detected or max_reached:
            # Concatenate audio (exclude trailing silence for pause detection)
            if pause_detected and len(self.segment_audio) > 1:
                # Keep speech, exclude trailing silence chunks
                segment = np.concatenate(self.segment_audio[:-1])
            else:
                segment = np.concatenate(self.segment_audio)

            # Reset state
            self.segment_audio = []
            self.consecutive_silent = 0
            self.total_samples = 0

            # Only return if we have meaningful audio
            if len(segment) > self.sample_rate * 0.3:  # At least 0.3s
                return segment

        return None

    def get_remaining(self) -> Optional[np.ndarray]:
        """Get any remaining buffered audio."""
        if self.segment_audio:
            segment = np.concatenate(self.segment_audio)
            self.segment_audio = []
            self.consecutive_silent = 0
            self.total_samples = 0

            # Only return if meaningful
            if len(segment) > self.sample_rate * 0.3:
                return segment

        return None

    def reset(self):
        """Reset detector state."""
        self.segment_audio = []
        self.consecutive_silent = 0
        self.total_samples = 0


# =============================================================================
# DictationService - main orchestrator
# =============================================================================

class DictationService:
    """Simple streaming dictation service."""

    def __init__(self, streaming: bool = STREAMING_ENABLED):
        self.streaming = streaming
        self.model: Optional[WhisperModel] = None
        self.vad_detector = None  # Lazy load to avoid slow startup if not needed

        # For batch mode (non-streaming)
        self.audio_buffer: List[np.ndarray] = []

        self.is_recording = False
        self.stream: Optional[sd.InputStream] = None
        self.lock = threading.Lock()

        # Text formatting state
        self.last_injected_char = ""  # Track last char for spacing decisions

        # Auto-stop state
        self.silence_start_time: Optional[float] = None  # When silence began

    def _init_vad(self):
        """Initialize VAD detector (lazy load)."""
        if self.vad_detector is None and self.streaming:
            from .audio.vad_detector import VADDetector
            self.vad_detector = VADDetector(
                sample_rate=SAMPLE_RATE,
                min_chunk_seconds=MIN_CHUNK_SECONDS,
                max_chunk_seconds=MAX_CHUNK_SECONDS,
                speech_threshold=VAD_THRESHOLD,
                min_silence_ms=MIN_SILENCE_MS,
            )

    def load_model(self):
        """Load Whisper model."""
        print(f"Loading Whisper model ({MODEL_SIZE})...", end=" ", flush=True)
        self.model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            download_root="models",
        )
        print("done")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio segment."""
        if self.model is None:
            return ""

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            beam_size=3,  # Faster than default 5
            vad_filter=False,
        )

        text = " ".join([seg.text for seg in segments]).strip()
        return text

    def _normalize_text_for_injection(self, text: str) -> str:
        """Normalize text for injection, ensuring proper spacing with previous chunk."""
        if not text:
            return text
        text = text.strip()
        if not text:
            return text

        # Add space if needed based on previous chunk's last character
        if self.last_injected_char:
            needs_space = False
            if self.last_injected_char in '.!?':  # After sentence-ending punctuation
                needs_space = True
            elif self.last_injected_char in ',;:':  # After comma/semicolon/colon
                needs_space = True
            elif self.last_injected_char.isalnum() and text[0].isalnum():  # Word boundaries
                needs_space = True
            if needs_space:
                text = " " + text
        return text

    def inject_text(self, text: str):
        """Inject text at cursor position."""
        if not text:
            return

        # Normalize spacing with previous chunk
        text = self._normalize_text_for_injection(text)
        if not text:
            return

        try:
            keyboard.write(text, delay=0.01)
            # Track last character for next chunk's spacing
            self.last_injected_char = text[-1] if text else ""
            print(f">>> Injected {len(text)} characters")
        except Exception as e:
            print(f">>> Injection failed: {e}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Audio stream callback - processes chunks for VAD/buffering."""
        if status:
            print(f"Audio status: {status}")

        if not self.is_recording:
            return

        # Flatten to mono
        audio_chunk = indata.flatten().astype(np.float32)

        if self.streaming and self.vad_detector is not None:
            # Streaming mode: process through VAD detector
            segment = self.vad_detector.process_chunk(audio_chunk)

            if segment is not None:
                # Speech segment complete - transcribe and inject in background
                self.silence_start_time = None  # Reset silence timer on speech
                threading.Thread(
                    target=self._process_segment,
                    args=(segment,),
                    daemon=True,
                ).start()

            # Check for auto-stop on extended silence
            silence_samples = self.vad_detector.consecutive_silence
            auto_stop_samples = int(AUTO_STOP_SILENCE_SECONDS * SAMPLE_RATE)
            if silence_samples >= auto_stop_samples:
                # Extended silence detected - auto-stop
                threading.Thread(target=self._auto_stop, daemon=True).start()
        else:
            # Batch mode: just buffer all audio
            self.audio_buffer.append(audio_chunk)

    def _process_segment(self, audio: np.ndarray):
        """Process a complete audio segment (transcribe and inject)."""
        duration = len(audio) / SAMPLE_RATE
        print(f">>> Speech segment ({duration:.1f}s) - transcribing...")
        text = self.transcribe(audio)
        if text:
            print(f'    "{text}"')
            self.inject_text(text)
        else:
            print("    (no speech detected)")

    def _auto_stop(self):
        """Auto-stop recording due to extended silence."""
        if not self.is_recording:
            return
        print(f"\n[Auto-stopped: no speech for {AUTO_STOP_SILENCE_SECONDS}s]")
        self.stop_recording()

    def start_recording(self):
        """Start recording."""
        with self.lock:
            if self.is_recording:
                return

            # Reset state
            self.audio_buffer = []
            self.last_injected_char = ""
            self.silence_start_time = None
            if self.vad_detector is not None:
                self.vad_detector.reset()

            self.is_recording = True

            # Create and start audio stream
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                callback=self._audio_callback,
                blocksize=int(SAMPLE_RATE * 0.1),  # 100ms chunks
                dtype=np.float32,
            )
            self.stream.start()

            mode = "streaming (VAD)" if self.streaming else "batch"
            print(f"\n[Recording started - {mode} mode]")

    def stop_recording(self):
        """Stop recording and process remaining audio."""
        with self.lock:
            if not self.is_recording:
                return

            self.is_recording = False

            # Stop stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            print("[Recording stopped]")

            if self.streaming and self.vad_detector is not None:
                # Streaming mode: process any remaining audio from VAD detector
                remaining = self.vad_detector.get_remaining()
                if remaining is not None:
                    print(">>> Final segment - transcribing...")
                    text = self.transcribe(remaining)
                    if text:
                        print(f'    "{text}"')
                        self.inject_text(text)
                    else:
                        print("    (no speech detected)")
            else:
                # Batch mode: transcribe all buffered audio at once
                if self.audio_buffer:
                    audio = np.concatenate(self.audio_buffer)
                    duration = len(audio) / SAMPLE_RATE
                    print(f">>> Transcribing {duration:.1f}s of audio...")
                    text = self.transcribe(audio)
                    if text:
                        print(f'    "{text}"')
                        self.inject_text(text)
                    else:
                        print("    (no speech detected)")
                    self.audio_buffer = []
                else:
                    print("    (no audio recorded)")

            print("\nReady. Press Ctrl+Shift+D to start recording.")

    def toggle_recording(self):
        """Toggle recording state."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def run(self):
        """Run the dictation service."""
        print("=" * 50)
        print("Quill Dictation Service")
        print("=" * 50)

        # Load model
        self.load_model()

        # Initialize VAD if streaming
        if self.streaming:
            print("Loading VAD model...", end=" ", flush=True)
            self._init_vad()
            print("done")

        # Show mode
        if self.streaming:
            print(f"\nMode: STREAMING (VAD-based)")
            print(f"  Min chunk: {MIN_CHUNK_SECONDS}s, Max chunk: {MAX_CHUNK_SECONDS}s")
        else:
            print(f"\nMode: BATCH (transcribe at end)")
            print("  (Edit STREAMING_ENABLED=True in dictation.py to enable streaming)")

        # Register hotkey
        keyboard.add_hotkey(HOTKEY, self.toggle_recording)
        print(f"\nHotkey: {HOTKEY.upper()}")
        print("Ready. Press Ctrl+Shift+D to start recording.")
        print("Press Ctrl+C to exit.\n")

        try:
            # Keep running
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            if self.is_recording:
                self.stop_recording()
            keyboard.remove_hotkey(HOTKEY)
            print("Goodbye!")


# =============================================================================
# Entry point
# =============================================================================

def main():
    """Main entry point."""
    service = DictationService()
    service.run()


if __name__ == "__main__":
    main()
