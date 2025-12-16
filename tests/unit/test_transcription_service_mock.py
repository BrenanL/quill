"""
Unit tests for TranscriptionService with mocked ModelManager.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import time
import threading

from Quill.transcription.service import TranscriptionService
from Quill.utils.errors import TranscriptionError

pytestmark = pytest.mark.unit


class TestTranscriptionServiceMocked:
    """Unit tests for TranscriptionService using mocks (fast)."""

    def test_init_starts_in_idle_state(self, mock_config):
        """Test that service initializes in idle state."""
        service = TranscriptionService(mock_config)

        assert service.state == "idle"
        assert service.loader_thread is None
        assert service.last_used is None

    def test_health_check_returns_status(self, mock_config):
        """Test health_check() returns current state."""
        service = TranscriptionService(mock_config)

        status = service.health_check()

        assert status["status"] == "ok"
        assert status["state"] == "idle"
        assert status["model_loaded"] is False

    @patch('Quill.transcription.service.ModelManager')
    def test_prepare_starts_background_load(self, mock_manager_class, mock_config):
        """Test that prepare() triggers background loading."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = False
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        assert service.state == "idle"

        status = service.prepare()

        assert status["status"] == "loading"
        assert service.state == "loading"
        assert service.loader_thread is not None
        assert service.loader_thread.is_alive()

        # Wait for thread to complete
        service.loader_thread.join(timeout=2)

    @patch('Quill.transcription.service.ModelManager')
    def test_prepare_idempotent_when_loading(self, mock_manager_class, mock_config):
        """Test that calling prepare() multiple times while loading is safe."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = False

        # Make load_model slow so we can test concurrent prepares
        def slow_load(*args, **kwargs):
            time.sleep(0.1)

        mock_manager.load_model.side_effect = slow_load
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)

        status1 = service.prepare()
        status2 = service.prepare()  # Should not start second thread

        assert status1["status"] == "loading"
        assert status2["status"] == "loading"

        # Should only have one loader thread
        assert service.loader_thread is not None

        service.loader_thread.join(timeout=2)

    @patch('Quill.transcription.service.ModelManager')
    def test_prepare_returns_ready_when_already_loaded(self, mock_manager_class, mock_config):
        """Test that prepare() returns ready if model already loaded."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        service.state = "ready"  # Simulate already loaded

        status = service.prepare()

        assert status["status"] == "ready"
        # Should not start loader thread
        assert service.loader_thread is None

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_with_mock_model(self, mock_manager_class, mock_config, mock_audio_data):
        """Test transcription with fully mocked ModelManager."""
        # Setup mock
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager.transcribe.return_value = "hello world from mock"
        mock_manager_class.return_value = mock_manager

        # Create service and set to ready state
        service = TranscriptionService(mock_config)
        service.state = "ready"

        # Test
        text = service.transcribe(mock_audio_data)

        assert text == "hello world from mock"
        mock_manager.transcribe.assert_called_once_with(mock_audio_data)
        assert service.last_used is not None

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_fails_when_not_ready(self, mock_manager_class, mock_config, mock_audio_data):
        """Test that transcribe() raises error if model not ready."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = False
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        # Service is in "idle" state

        with pytest.raises(TranscriptionError, match="Model not ready"):
            service.transcribe(mock_audio_data)

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_waits_for_loading(self, mock_manager_class, mock_config, mock_audio_data):
        """Test that transcribe() waits if model is still loading."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager.transcribe.return_value = "loaded and transcribed"
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        service.state = "loading"

        # Start a thread that will change state to ready after a delay
        def set_ready():
            time.sleep(0.1)
            service.state = "ready"

        threading.Thread(target=set_ready, daemon=True).start()

        # Should wait and succeed
        text = service.transcribe(mock_audio_data)
        assert text == "loaded and transcribed"

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_timeout_when_loading_too_long(self, mock_manager_class, mock_config, mock_audio_data):
        """Test that transcribe() times out if loading takes too long."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        service.state = "loading"
        # Don't change state - should timeout

        with pytest.raises(TranscriptionError, match="Model not ready"):
            service.transcribe(mock_audio_data)

    @patch('Quill.transcription.service.ModelManager')
    def test_check_idle_timeout_unloads_model(self, mock_manager_class, mock_config):
        """Test that check_idle_timeout() unloads model after timeout."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager_class.return_value = mock_manager

        # Set timeout to 0 minutes for testing
        mock_config.transcription.lifecycle.unload_after_minutes = 0

        service = TranscriptionService(mock_config)
        service.state = "ready"
        service.last_used = time.time() - 60  # 60 seconds ago

        service.check_idle_timeout()

        # Should have unloaded
        mock_manager.unload_model.assert_called_once()
        assert service.state == "idle"

    @patch('Quill.transcription.service.ModelManager')
    def test_check_idle_timeout_respects_timeout_setting(self, mock_manager_class, mock_config):
        """Test that timeout setting is respected."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager_class.return_value = mock_manager

        # Set timeout to 5 minutes
        mock_config.transcription.lifecycle.unload_after_minutes = 5

        service = TranscriptionService(mock_config)
        service.state = "ready"
        service.last_used = time.time() - 60  # Only 1 minute ago

        service.check_idle_timeout()

        # Should NOT have unloaded (only 1 minute, need 5)
        mock_manager.unload_model.assert_not_called()
        assert service.state == "ready"

    @patch('Quill.transcription.service.ModelManager')
    def test_check_idle_timeout_disabled(self, mock_manager_class, mock_config):
        """Test that timeout=0 means never unload."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager_class.return_value = mock_manager

        # Set timeout to 0 (disabled)
        mock_config.transcription.lifecycle.unload_after_minutes = 0

        service = TranscriptionService(mock_config)
        service.state = "ready"
        service.last_used = time.time() - 3600  # 1 hour ago

        service.check_idle_timeout()

        # Should NOT unload (timeout disabled)
        mock_manager.unload_model.assert_not_called()

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_updates_last_used(self, mock_manager_class, mock_config, mock_audio_data):
        """Test that transcribe() updates last_used timestamp."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = True
        mock_manager.transcribe.return_value = "test"
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        service.state = "ready"

        before = time.time()
        service.transcribe(mock_audio_data)
        after = time.time()

        assert service.last_used is not None
        assert before <= service.last_used <= after

    @patch('Quill.transcription.service.ModelManager')
    def test_state_transitions(self, mock_manager_class, mock_config):
        """Test state transitions: idle -> loading -> ready."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = False
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)

        # Start in idle
        assert service.state == "idle"

        # Prepare triggers loading
        service.prepare()
        assert service.state == "loading"

        # Wait for load to complete
        service.loader_thread.join(timeout=2)
        assert service.state == "ready"

    @patch('Quill.transcription.service.ModelManager')
    def test_error_state_on_load_failure(self, mock_manager_class, mock_config):
        """Test that service enters error state if model load fails."""
        mock_manager = Mock()
        mock_manager.is_loaded.return_value = False
        mock_manager.load_model.side_effect = Exception("GPU OOM")
        mock_manager_class.return_value = mock_manager

        service = TranscriptionService(mock_config)
        service.prepare()

        # Wait for load to fail
        service.loader_thread.join(timeout=2)

        assert service.state == "error"
