"""Audio capture using sounddevice."""

import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from loguru import logger

from ..utils.errors import AudioCaptureError
from ..utils.threading import RingBuffer
from .preprocessing import resample_audio, apply_noise_gate, convert_to_mono


class AudioCapture:
    """Captures audio from microphone using sounddevice."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_seconds: float = 0.1,
        noise_gate_threshold: float = 0.01,
        queue_size: int = 50,
    ):
        """
        Initialize audio capture.

        Args:
            sample_rate: Target sample rate (Hz)
            channels: Number of channels (1=mono, 2=stereo)
            chunk_duration_seconds: Duration of each audio chunk
            noise_gate_threshold: Noise gate threshold
            queue_size: Maximum queue size
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration_seconds
        self.noise_gate_threshold = noise_gate_threshold

        self.buffer = RingBuffer(maxsize=queue_size)
        self.stream: Optional[sd.InputStream] = None
        self.is_recording = False

        # Detect default device
        try:
            self.device_info = sd.query_devices(kind="input")
            logger.info(f"Audio input device: {self.device_info['name']}")
        except Exception as e:
            raise AudioCaptureError(f"No audio input device found: {e}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """
        Callback for sounddevice stream.

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Status flags
        """
        if status:
            logger.warning(f"Audio callback status: {status}")

        if not self.is_recording:
            return

        # Copy data (sounddevice reuses buffer)
        audio_chunk = indata.copy()

        # Convert to mono if needed
        if audio_chunk.ndim > 1:
            audio_chunk = convert_to_mono(audio_chunk)

        # Apply noise gate
        if self.noise_gate_threshold > 0.0:
            audio_chunk = apply_noise_gate(audio_chunk, self.noise_gate_threshold)

        # Add to buffer (non-blocking)
        try:
            self.buffer.put(audio_chunk, block=False)
        except Exception as e:
            logger.warning(f"Buffer full, dropping audio chunk: {e}")

    def start(self) -> None:
        """
        Start audio capture.

        Raises:
            AudioCaptureError: If capture fails to start
        """
        if self.is_recording:
            logger.warning("Already recording")
            return

        try:
            # Clear buffer
            self.buffer.clear()

            # Calculate chunk size
            chunk_size = int(self.sample_rate * self.chunk_duration)

            # Create stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=chunk_size,
                dtype=np.float32,
            )

            # Start stream
            self.stream.start()
            self.is_recording = True

            logger.info(f"Audio capture started (sr={self.sample_rate}, ch={self.channels})")

        except Exception as e:
            raise AudioCaptureError(f"Failed to start audio capture: {e}")

    def stop(self) -> np.ndarray:
        """
        Stop audio capture and return recorded audio.

        Returns:
            Recorded audio as numpy array

        Raises:
            AudioCaptureError: If no audio was recorded
        """
        if not self.is_recording:
            logger.warning("Not recording")
            return np.array([], dtype=np.float32)

        try:
            # Stop recording
            self.is_recording = False

            # Stop stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Get all audio from buffer
            chunks = self.buffer.get_all()

            if not chunks:
                raise AudioCaptureError("No audio data recorded")

            # Concatenate all chunks
            audio = np.concatenate(chunks)

            logger.info(f"Audio capture stopped ({len(audio)} samples, {len(audio)/self.sample_rate:.2f}s)")

            return audio

        except Exception as e:
            raise AudioCaptureError(f"Failed to stop audio capture: {e}")

    def cleanup(self) -> None:
        """Clean up audio resources."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error cleaning up audio stream: {e}")
            finally:
                self.stream = None

        self.is_recording = False
        self.buffer.clear()

    @staticmethod
    def list_devices() -> list:
        """
        List all available audio input devices.

        Returns:
            List of device dictionaries
        """
        try:
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
            return input_devices
        except Exception as e:
            logger.error(f"Failed to list audio devices: {e}")
            return []
