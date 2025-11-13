"""Transcription service with model lifecycle management."""

import time
import threading
from typing import Optional, Dict, Any
import numpy as np
from loguru import logger

from ..utils.errors import TranscriptionError
from .model_manager import ModelManager


class TranscriptionService:
    """
    Always-running transcription service that manages model lifecycle.

    This service runs in a separate thread and provides:
    - prepare(): Signal that transcription will be needed (triggers background loading)
    - transcribe(): Perform transcription (blocking)
    - Model lifecycle management (auto-unload on idle)
    """

    def __init__(self, config):
        """
        Initialize transcription service.

        Args:
            config: Configuration object
        """
        self.config = config
        self.model_manager = ModelManager(models_dir="models")

        self.state = "idle"  # idle, loading, ready, error
        self.state_lock = threading.Lock()
        self.last_used: Optional[float] = None

        self.loader_thread: Optional[threading.Thread] = None

    def health_check(self) -> Dict[str, Any]:
        """
        Check if service is alive.

        Returns:
            Service health status
        """
        with self.state_lock:
            return {
                "status": "ok",
                "state": self.state,
                "model_loaded": self.model_manager.is_loaded(),
                "model_size": self.model_manager.current_size,
            }

    def prepare(self) -> Dict[str, str]:
        """
        Signal that transcription will be needed soon.

        Triggers background model loading if not loaded.
        Returns immediately (non-blocking).

        Returns:
            Status dictionary
        """
        with self.state_lock:
            if self.state == "ready":
                logger.debug("Model already ready")
                return {"status": "ready"}

            if self.state == "loading":
                logger.debug("Model already loading")
                return {"status": "loading"}

            if self.state == "idle":
                # Start loading model in background
                logger.info("Starting background model load")

                self.loader_thread = threading.Thread(
                    target=self._load_model_background, daemon=True
                )
                self.loader_thread.start()

                return {"status": "loading"}

            return {"status": self.state}

    def _load_model_background(self) -> None:
        """Background model loading (runs in separate thread)."""
        try:
            with self.state_lock:
                self.state = "loading"

            logger.info("Loading model in background...")

            # Load model (this takes 3-5 seconds)
            self.model_manager.load_model(
                model_size=self.config.transcription.model_size,
                device=self.config.transcription.device,
                compute_type=self.config.transcription.compute_type,
            )

            with self.state_lock:
                self.state = "ready"

            logger.info("Model loaded and ready")

        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            with self.state_lock:
                self.state = "error"

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio (blocking).

        Will wait if model is still loading.

        Args:
            audio: Audio data (numpy array, 16kHz, mono)

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        # Wait for model to be ready (if still loading)
        max_wait = 30  # seconds
        waited = 0
        while self.state == "loading" and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1

        if self.state != "ready":
            raise TranscriptionError(f"Model not ready (state: {self.state})")

        try:
            # Run transcription
            logger.debug(f"Transcribing {len(audio)} samples...")

            segments, info = self.model_manager.current_model.transcribe(
                audio,
                language=self.config.transcription.language,
                beam_size=5,
                vad_filter=False,  # Disabled for MVP
            )

            # Concatenate all segments
            text = " ".join([seg.text for seg in segments])

            # Update last used timestamp
            self.last_used = time.time()

            logger.info(f"Transcription complete: '{text[:50]}...'")

            return text.strip()

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def check_idle_timeout(self) -> None:
        """
        Check if model should be unloaded due to inactivity.

        Called periodically by idle monitor thread.
        """
        if self.state != "ready" or not self.last_used:
            return

        idle_minutes = self.config.transcription.lifecycle.unload_after_minutes

        # -1 means immediate unload (but we keep it for one transcription)
        # 0 means never unload
        if idle_minutes == 0:
            return

        idle_time = time.time() - self.last_used
        timeout = idle_minutes * 60 if idle_minutes > 0 else 0

        if idle_time > timeout:
            logger.info(f"Model idle for {idle_time:.0f}s, unloading")

            with self.state_lock:
                self.model_manager.unload_model()
                self.state = "idle"
                self.last_used = None

    def shutdown(self) -> None:
        """Shutdown service and clean up resources."""
        logger.info("Shutting down transcription service")

        with self.state_lock:
            self.model_manager.unload_model()
            self.state = "idle"
