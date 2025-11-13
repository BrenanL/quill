"""Main Quill application."""

import threading
import time
from pathlib import Path
from typing import Optional
from loguru import logger

from .config import ConfigManager
from .transcription import TranscriptionService
from .audio import AudioCapture
from .injection import WindowsTextInjector
from .hotkeys import HotkeyListener
from .ui import NotificationManager
from .utils.logging import setup_logging
from .utils.errors import QuillError


class QuillApp:
    """Main Quill application orchestrator."""

    def __init__(self, config_path: str | Path = "config.yaml"):
        """
        Initialize Quill application.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = ConfigManager.load_with_defaults(config_path)

        # Setup logging
        setup_logging(
            log_file=self.config.app.log_file,
            log_level=self.config.app.log_level.upper(),
            max_size_mb=self.config.app.log_max_size_mb,
        )

        logger.info("=" * 60)
        logger.info("Quill Starting...")
        logger.info("=" * 60)

        # State
        self.state = "idle"  # idle, recording, processing
        self.state_lock = threading.Lock()

        # Initialize components
        self.transcription_service = TranscriptionService(self.config)
        self.audio_capture = AudioCapture(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            chunk_duration_seconds=self.config.audio.chunk_duration_seconds,
            noise_gate_threshold=self.config.audio.noise_gate_threshold,
            queue_size=self.config.advanced.audio_queue_size,
        )
        self.text_injector = WindowsTextInjector(
            typing_speed_cps=self.config.text_injection.typing_speed_cps,
            key_delay_ms=self.config.text_injection.key_delay_ms,
        )
        self.notifications = NotificationManager(
            enabled=self.config.ui.show_notifications,
            duration=self.config.ui.notification_duration_seconds,
        )
        self.hotkey_listener = HotkeyListener(
            toggle_recording=self.config.hotkeys.toggle_recording,
            emergency_stop=self.config.hotkeys.emergency_stop,
        )

        # Threads
        self.transcription_thread: Optional[threading.Thread] = None
        self.idle_monitor_thread: Optional[threading.Thread] = None
        self.running = False

        logger.info("Quill initialized successfully")

    def start(self) -> None:
        """Start Quill application."""
        try:
            self.running = True

            # Start idle monitor
            self.idle_monitor_thread = threading.Thread(
                target=self._idle_monitor_loop, daemon=True
            )
            self.idle_monitor_thread.start()

            # Start hotkey listener
            self.hotkey_listener.start(
                on_toggle=self._on_toggle_recording,
                on_emergency=self._on_emergency_stop,
            )

            logger.info("Quill started successfully")
            logger.info(f"Hotkey: {self.config.hotkeys.toggle_recording}")

            # Keep alive
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.shutdown()

    def _on_toggle_recording(self) -> None:
        """Handle toggle recording hotkey."""
        with self.state_lock:
            if self.state == "idle":
                self._start_recording()
            elif self.state == "recording":
                self._stop_recording()
            else:
                logger.warning(f"Cannot toggle recording in state: {self.state}")

    def _start_recording(self) -> None:
        """Start recording (called from hotkey thread)."""
        logger.info("Starting recording...")

        try:
            # Prepare transcription service
            service_status = self.transcription_service.prepare()

            if service_status["status"] == "error":
                self.notifications.show_error("Transcription service error")
                logger.error("Cannot start recording: service error")
                return

            # Start audio capture
            self.audio_capture.start()
            self.state = "recording"

            # Show notification
            self.notifications.show_recording_started()

            logger.info(f"Recording started (service: {service_status['status']})")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}", exc_info=True)
            self.notifications.show_error(str(e))
            self.state = "idle"

    def _stop_recording(self) -> None:
        """Stop recording and start transcription (called from hotkey thread)."""
        logger.info("Stopping recording...")

        try:
            # Stop audio capture
            audio_data = self.audio_capture.stop()
            self.state = "processing"

            # Show processing notification
            self.notifications.show_processing()

            # Start transcription in background
            self.transcription_thread = threading.Thread(
                target=self._transcribe_and_inject,
                args=(audio_data,),
                daemon=True,
            )
            self.transcription_thread.start()

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}", exc_info=True)
            self.notifications.show_error(str(e))
            self.state = "idle"

    def _transcribe_and_inject(self, audio_data) -> None:
        """Transcribe audio and inject text (runs in background thread)."""
        try:
            logger.info("Transcribing audio...")

            # Transcribe
            text = self.transcription_service.transcribe(audio_data)

            if not text:
                logger.warning("No text transcribed")
                self.notifications.show_error("No speech detected")
                return

            logger.info(f"Transcribed: '{text[:100]}...'")

            # Inject text
            logger.info("Injecting text...")
            self.text_injector.inject(text)

            # Show success
            self.notifications.show_success()

            logger.info("Text injection complete")

        except Exception as e:
            logger.error(f"Transcription/injection failed: {e}", exc_info=True)
            self.notifications.show_error(str(e))

        finally:
            with self.state_lock:
                self.state = "idle"

    def _on_emergency_stop(self) -> None:
        """Handle emergency stop hotkey."""
        logger.warning("Emergency stop triggered")

        with self.state_lock:
            if self.state == "recording":
                try:
                    self.audio_capture.cleanup()
                except Exception as e:
                    logger.error(f"Error during emergency stop: {e}")

            self.state = "idle"

        self.notifications.show("Quill", "⏹️ Emergency stop")

    def _idle_monitor_loop(self) -> None:
        """Monitor for idle timeout (runs in background thread)."""
        while self.running:
            time.sleep(60)  # Check every minute
            try:
                self.transcription_service.check_idle_timeout()
            except Exception as e:
                logger.error(f"Error in idle monitor: {e}")

    def shutdown(self) -> None:
        """Shutdown Quill application."""
        logger.info("Shutting down Quill...")

        self.running = False

        # Cleanup components
        try:
            self.audio_capture.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up audio: {e}")

        try:
            self.transcription_service.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down transcription: {e}")

        try:
            self.hotkey_listener.stop()
        except Exception as e:
            logger.warning(f"Error stopping hotkeys: {e}")

        logger.info("Quill shutdown complete")
