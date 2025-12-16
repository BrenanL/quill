"""
Unit tests for QuillApp with all components mocked.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from Quill.app import QuillApp

pytestmark = pytest.mark.unit


class TestQuillAppMocked:
    """Unit tests for QuillApp with all components mocked."""

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_init_creates_all_components(self, mock_notif_class, mock_hotkey_class,
                                        mock_injector_class, mock_audio_class,
                                        mock_trans_class, mock_setup_logging,
                                        mock_load_config, mock_config):
        """Test that initialization creates all components."""
        mock_load_config.return_value = mock_config

        app = QuillApp("config.yaml")

        # Verify all components were created
        mock_trans_class.assert_called_once_with(mock_config)
        mock_audio_class.assert_called_once()
        mock_injector_class.assert_called_once_with(mock_config)
        mock_hotkey_class.assert_called_once()
        mock_notif_class.assert_called_once_with(mock_config)

        assert app.state == "idle"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_start_recording_changes_state(self, mock_notif_class, mock_hotkey_class,
                                          mock_injector_class, mock_audio_class,
                                          mock_trans_class, mock_config):
        """Test that start_recording changes state and starts audio."""
        mock_audio = Mock()
        mock_audio_class.return_value = mock_audio

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.start_recording()

        assert app.state == "recording"
        mock_audio.start.assert_called_once()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_start_recording_shows_notification(self, mock_notif_class, mock_hotkey_class,
                                                mock_injector_class, mock_audio_class,
                                                mock_trans_class, mock_config):
        """Test that start_recording shows notification."""
        mock_notif = Mock()
        mock_notif_class.return_value = mock_notif

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.start_recording()

        mock_notif.show_recording_started.assert_called_once()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_start_recording_when_already_recording(self, mock_notif_class, mock_hotkey_class,
                                                    mock_injector_class, mock_audio_class,
                                                    mock_trans_class, mock_config):
        """Test that start_recording when already recording is a no-op."""
        mock_audio = Mock()
        mock_audio_class.return_value = mock_audio

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"

        app.start_recording()

        # Should not call start again
        mock_audio.start.assert_not_called()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_stop_recording_gets_audio(self, mock_notif_class, mock_hotkey_class,
                                      mock_injector_class, mock_audio_class,
                                      mock_trans_class, mock_config):
        """Test that stop_recording gets audio from capture."""
        mock_audio = Mock()
        mock_audio.stop.return_value = None
        mock_audio.get_recorded_audio.return_value = np.zeros(16000, dtype=np.float32)
        mock_audio_class.return_value = mock_audio

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"
        app.stop_recording()

        mock_audio.stop.assert_called_once()
        mock_audio.get_recorded_audio.assert_called_once()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_stop_recording_changes_to_processing(self, mock_notif_class, mock_hotkey_class,
                                                  mock_injector_class, mock_audio_class,
                                                  mock_trans_class, mock_config):
        """Test that stop_recording changes state to processing."""
        mock_audio = Mock()
        mock_audio.get_recorded_audio.return_value = np.zeros(16000, dtype=np.float32)
        mock_audio_class.return_value = mock_audio

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"
        app.stop_recording()

        assert app.state == "processing"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    @patch('threading.Thread')
    def test_stop_recording_starts_transcription_thread(self, mock_thread_class,
                                                        mock_notif_class, mock_hotkey_class,
                                                        mock_injector_class, mock_audio_class,
                                                        mock_trans_class, mock_config):
        """Test that stop_recording starts transcription in background thread."""
        mock_audio = Mock()
        mock_audio.get_recorded_audio.return_value = np.zeros(16000, dtype=np.float32)
        mock_audio_class.return_value = mock_audio

        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"
        app.stop_recording()

        # Should create and start thread
        mock_thread_class.assert_called()
        mock_thread.start.assert_called_once()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_transcribe_and_inject_workflow(self, mock_notif_class, mock_hotkey_class,
                                           mock_injector_class, mock_audio_class,
                                           mock_trans_class, mock_config, mock_audio_data):
        """Test the full transcribe and inject workflow."""
        # Setup mocks
        mock_trans = Mock()
        mock_trans.transcribe.return_value = "transcribed text"
        mock_trans_class.return_value = mock_trans

        mock_injector = Mock()
        mock_injector_class.return_value = mock_injector

        mock_notif = Mock()
        mock_notif_class.return_value = mock_notif

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")

        # Call transcribe_and_inject directly (normally called in thread)
        app._transcribe_and_inject(mock_audio_data)

        # Verify workflow
        mock_trans.transcribe.assert_called_once_with(mock_audio_data)
        mock_injector.inject.assert_called_once_with("transcribed text")
        mock_notif.show_success.assert_called_once()
        assert app.state == "idle"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_transcribe_and_inject_handles_errors(self, mock_notif_class, mock_hotkey_class,
                                                  mock_injector_class, mock_audio_class,
                                                  mock_trans_class, mock_config, mock_audio_data):
        """Test that errors in transcription are handled gracefully."""
        # Setup mocks
        mock_trans = Mock()
        mock_trans.transcribe.side_effect = Exception("Transcription failed")
        mock_trans_class.return_value = mock_trans

        mock_notif = Mock()
        mock_notif_class.return_value = mock_notif

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")

        # Should not raise exception
        app._transcribe_and_inject(mock_audio_data)

        # Should show error notification
        mock_notif.show_error.assert_called_once()
        assert app.state == "error"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_emergency_stop(self, mock_notif_class, mock_hotkey_class,
                           mock_injector_class, mock_audio_class,
                           mock_trans_class, mock_config):
        """Test emergency stop functionality."""
        mock_audio = Mock()
        mock_audio_class.return_value = mock_audio

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"
        app.emergency_stop()

        # Should stop audio
        mock_audio.stop.assert_called_once()
        # Should reset state
        assert app.state == "idle"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_show_notification_delegates_to_manager(self, mock_notif_class, mock_hotkey_class,
                                                    mock_injector_class, mock_audio_class,
                                                    mock_trans_class, mock_config):
        """Test that show_notification delegates to NotificationManager."""
        mock_notif = Mock()
        mock_notif_class.return_value = mock_notif

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.show_notification("Test message")

        mock_notif.show.assert_called_once()

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_state_transitions(self, mock_notif_class, mock_hotkey_class,
                              mock_injector_class, mock_audio_class,
                              mock_trans_class, mock_config):
        """Test state machine transitions."""
        mock_audio = Mock()
        mock_audio.get_recorded_audio.return_value = np.zeros(100, dtype=np.float32)
        mock_audio_class.return_value = mock_audio

        mock_trans = Mock()
        mock_trans.transcribe.return_value = "text"
        mock_trans_class.return_value = mock_trans

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")

        # idle -> recording
        assert app.state == "idle"
        app.start_recording()
        assert app.state == "recording"

        # recording -> processing
        app.stop_recording()
        assert app.state == "processing"

        # processing -> idle (after transcription)
        app._transcribe_and_inject(np.zeros(100, dtype=np.float32))
        assert app.state == "idle"

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_empty_audio_handling(self, mock_notif_class, mock_hotkey_class,
                                  mock_injector_class, mock_audio_class,
                                  mock_trans_class, mock_config):
        """Test handling of empty audio (no speech detected)."""
        mock_audio = Mock()
        mock_audio.get_recorded_audio.return_value = np.array([], dtype=np.float32)
        mock_audio_class.return_value = mock_audio

        mock_notif = Mock()
        mock_notif_class.return_value = mock_notif

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app.state = "recording"
        app.stop_recording()

        # Should handle empty audio gracefully
        # Either skip transcription or show appropriate message
        # State should return to idle
        assert app.state in ["idle", "processing"]

    @patch('Quill.app.ConfigManager.load_with_defaults')
    @patch('Quill.app.setup_logging')
    @patch('Quill.app.TranscriptionService')
    @patch('Quill.app.AudioCapture')
    @patch('Quill.app.WindowsTextInjector')
    @patch('Quill.app.HotkeyListener')
    @patch('Quill.app.NotificationManager')
    def test_transcription_returns_empty_string(self, mock_notif_class, mock_hotkey_class,
                                                mock_injector_class, mock_audio_class,
                                                mock_trans_class, mock_config, mock_audio_data):
        """Test handling when transcription returns empty string."""
        mock_trans = Mock()
        mock_trans.transcribe.return_value = ""
        mock_trans_class.return_value = mock_trans

        mock_injector = Mock()
        mock_injector_class.return_value = mock_injector

        mock_load_config.return_value = mock_config
        
        app = QuillApp("config.yaml")
        app._transcribe_and_inject(mock_audio_data)

        # Should still inject empty string (or skip injection)
        # Implementation detail - either is acceptable
        # Should return to idle state
        assert app.state == "idle"
