"""
Voice Activity Detection using Silero VAD.

Detects speech boundaries with minimum chunk duration for accurate transcription.
"""

import numpy as np
import torch
from typing import Optional, List
from loguru import logger


# Silero VAD requires exactly this many samples per call
SILERO_CHUNK_SAMPLES = 512  # For 16kHz sample rate (32ms)


class VADDetector:
    """
    Detects speech segments using Silero VAD with minimum duration constraints.

    Accumulates audio until:
    1. VAD detects end of speech (natural pause)
    2. AND minimum chunk duration is met

    Force-chunks at maximum duration even if speech continues.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        min_chunk_seconds: float = 5.0,
        max_chunk_seconds: float = 30.0,
        speech_threshold: float = 0.5,
        min_silence_ms: int = 500,
    ):
        """
        Initialize VAD detector.

        Args:
            sample_rate: Audio sample rate (must be 16000 for Silero)
            min_chunk_seconds: Minimum audio duration before allowing transcription
            max_chunk_seconds: Maximum duration before forcing transcription
            speech_threshold: VAD threshold (0-1, higher = stricter)
            min_silence_ms: Minimum silence duration to consider speech ended
        """
        self.sample_rate = sample_rate
        self.min_chunk_samples = int(sample_rate * min_chunk_seconds)
        self.max_chunk_samples = int(sample_rate * max_chunk_seconds)
        self.speech_threshold = speech_threshold
        self.min_silence_samples = int(sample_rate * min_silence_ms / 1000)

        # Load Silero VAD model
        logger.info("Loading Silero VAD model...")
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True,
        )
        self.model.eval()
        logger.info("Silero VAD model loaded")

        # State
        self.audio_buffer: List[np.ndarray] = []
        self.total_samples = 0
        self.consecutive_silence = 0
        self.speech_detected = False

        # VAD processing buffer (for accumulating to 512 samples)
        self.vad_buffer = np.array([], dtype=np.float32)

    def _process_vad_chunks(self, audio: np.ndarray) -> bool:
        """
        Process audio through VAD in 512-sample chunks.

        Returns True if any chunk contains speech.
        """
        # Add to VAD buffer
        self.vad_buffer = np.concatenate([self.vad_buffer, audio])

        any_speech = False

        # Process complete 512-sample chunks
        while len(self.vad_buffer) >= SILERO_CHUNK_SAMPLES:
            chunk = self.vad_buffer[:SILERO_CHUNK_SAMPLES]
            self.vad_buffer = self.vad_buffer[SILERO_CHUNK_SAMPLES:]

            # Run VAD on this chunk
            audio_tensor = torch.from_numpy(chunk).float()
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()

            if speech_prob >= self.speech_threshold:
                any_speech = True

        return any_speech

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Process an audio chunk and return complete segment if ready.

        Args:
            audio_chunk: Audio data (float32, mono, 16kHz)

        Returns:
            Complete audio segment if ready for transcription, None otherwise
        """
        # Add to buffer
        self.audio_buffer.append(audio_chunk)
        self.total_samples += len(audio_chunk)

        # Check VAD (processes in 512-sample chunks as required by Silero)
        is_speech = self._process_vad_chunks(audio_chunk)

        if is_speech:
            self.speech_detected = True
            self.consecutive_silence = 0
        else:
            self.consecutive_silence += len(audio_chunk)

        # Check if we should emit a segment
        has_min_duration = self.total_samples >= self.min_chunk_samples
        has_max_duration = self.total_samples >= self.max_chunk_samples
        speech_ended = (
            self.speech_detected
            and self.consecutive_silence >= self.min_silence_samples
        )

        # Emit segment if: (speech ended AND min duration met) OR max duration reached
        if (speech_ended and has_min_duration) or has_max_duration:
            segment = np.concatenate(self.audio_buffer)

            # Trim trailing silence (but keep a bit for context)
            if speech_ended and self.consecutive_silence > self.min_silence_samples:
                trim_samples = self.consecutive_silence - (self.sample_rate // 10)  # Keep 100ms
                if trim_samples > 0 and trim_samples < len(segment):
                    segment = segment[:-trim_samples]

            # Reset state
            self.audio_buffer = []
            self.total_samples = 0
            self.consecutive_silence = 0
            self.speech_detected = False

            # Only return if we have meaningful audio
            if len(segment) >= self.sample_rate:  # At least 1 second
                return segment

        return None

    def get_remaining(self) -> Optional[np.ndarray]:
        """Get any remaining buffered audio."""
        if self.audio_buffer and self.total_samples >= self.sample_rate:  # At least 1s
            segment = np.concatenate(self.audio_buffer)
            self.audio_buffer = []
            self.total_samples = 0
            self.consecutive_silence = 0
            self.speech_detected = False
            return segment
        return None

    def reset(self):
        """Reset detector state."""
        self.audio_buffer = []
        self.total_samples = 0
        self.consecutive_silence = 0
        self.speech_detected = False
        self.vad_buffer = np.array([], dtype=np.float32)
        # Reset VAD model state
        self.model.reset_states()
