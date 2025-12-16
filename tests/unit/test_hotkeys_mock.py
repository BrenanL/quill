"""
Unit tests for HotkeyListener with mocked keyboard library.
"""

import pytest
from unittest.mock import Mock, patch, call

from Quill.hotkeys.listener import HotkeyListener
from Quill.utils.errors import HotkeyError

pytestmark = pytest.mark.unit


class TestHotkeyListenerMocked:
    """Unit tests for HotkeyListener using mocked keyboard."""

    def test_init_with_config(self, mock_config):
        """Test initialization with configuration."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)

        assert listener.toggle_hotkey == "ctrl+shift+d"
        assert listener.emergency_hotkey == "ctrl+shift+esc"
        assert listener.app is mock_app
        assert listener.is_recording is False

    @patch('keyboard.add_hotkey')
    def test_start_registers_hotkeys(self, mock_add_hotkey, mock_config):
        """Test that start() registers hotkeys."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Should register both hotkeys
        assert mock_add_hotkey.call_count == 2

        # Verify hotkeys were registered
        calls = mock_add_hotkey.call_args_list
        registered_keys = [call[0][0] for call in calls]

        assert "ctrl+shift+d" in registered_keys
        assert "ctrl+shift+esc" in registered_keys

    @patch('keyboard.add_hotkey')
    @patch('keyboard.remove_hotkey')
    def test_stop_removes_hotkeys(self, mock_remove_hotkey, mock_add_hotkey, mock_config):
        """Test that stop() removes registered hotkeys."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()
        listener.stop()

        # Should remove both hotkeys
        assert mock_remove_hotkey.call_count == 2

    @patch('keyboard.add_hotkey')
    def test_toggle_recording_calls_app_start(self, mock_add_hotkey, mock_config):
        """Test that toggle hotkey starts recording when idle."""
        mock_app = Mock()
        mock_app.transcription_service.prepare.return_value = {"status": "ready"}

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Get the callback for toggle hotkey
        toggle_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+d":
                toggle_callback = call_args[0][1]
                break

        assert toggle_callback is not None

        # Simulate hotkey press
        toggle_callback()

        # Should start recording
        mock_app.start_recording.assert_called_once()
        assert listener.is_recording is True

    @patch('keyboard.add_hotkey')
    def test_toggle_recording_calls_app_stop(self, mock_add_hotkey, mock_config):
        """Test that toggle hotkey stops recording when recording."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)
        listener.is_recording = True  # Simulate already recording
        listener.start()

        # Get the callback for toggle hotkey
        toggle_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+d":
                toggle_callback = call_args[0][1]
                break

        # Simulate hotkey press
        toggle_callback()

        # Should stop recording
        mock_app.stop_recording.assert_called_once()
        assert listener.is_recording is False

    @patch('keyboard.add_hotkey')
    def test_toggle_hotkey_multiple_presses(self, mock_add_hotkey, mock_config):
        """Test toggle hotkey with multiple presses (start/stop/start)."""
        mock_app = Mock()
        mock_app.transcription_service.prepare.return_value = {"status": "ready"}

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Get toggle callback
        toggle_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+d":
                toggle_callback = call_args[0][1]
                break

        # First press - start
        toggle_callback()
        assert listener.is_recording is True
        assert mock_app.start_recording.call_count == 1

        # Second press - stop
        toggle_callback()
        assert listener.is_recording is False
        assert mock_app.stop_recording.call_count == 1

        # Third press - start again
        toggle_callback()
        assert listener.is_recording is True
        assert mock_app.start_recording.call_count == 2

    @patch('keyboard.add_hotkey')
    def test_emergency_stop_calls_app(self, mock_add_hotkey, mock_config):
        """Test that emergency stop hotkey calls app.emergency_stop()."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)
        listener.is_recording = True
        listener.start()

        # Get emergency callback
        emergency_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+esc":
                emergency_callback = call_args[0][1]
                break

        assert emergency_callback is not None

        # Simulate emergency stop
        emergency_callback()

        # Should call emergency stop
        mock_app.emergency_stop.assert_called_once()
        assert listener.is_recording is False

    @patch('keyboard.add_hotkey')
    def test_emergency_stop_when_not_recording(self, mock_add_hotkey, mock_config):
        """Test emergency stop when not recording."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Get emergency callback
        emergency_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+esc":
                emergency_callback = call_args[0][1]
                break

        # Simulate emergency stop when not recording
        emergency_callback()

        # Should still call emergency stop
        mock_app.emergency_stop.assert_called_once()

    @patch('keyboard.add_hotkey')
    def test_service_error_prevents_recording(self, mock_add_hotkey, mock_config):
        """Test that service error prevents recording from starting."""
        mock_app = Mock()
        mock_app.transcription_service.prepare.return_value = {"status": "error"}

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Get toggle callback
        toggle_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+d":
                toggle_callback = call_args[0][1]
                break

        # Try to start recording
        toggle_callback()

        # Should NOT start recording
        mock_app.start_recording.assert_not_called()
        assert listener.is_recording is False

        # Should show notification
        mock_app.show_notification.assert_called()

    @patch('keyboard.add_hotkey')
    def test_service_loading_allows_recording(self, mock_add_hotkey, mock_config):
        """Test that service loading state still allows recording."""
        mock_app = Mock()
        mock_app.transcription_service.prepare.return_value = {"status": "loading"}

        listener = HotkeyListener(mock_config, mock_app)
        listener.start()

        # Get toggle callback
        toggle_callback = None
        for call_args in mock_add_hotkey.call_args_list:
            if call_args[0][0] == "ctrl+shift+d":
                toggle_callback = call_args[0][1]
                break

        # Start recording
        toggle_callback()

        # Should start recording even if loading
        mock_app.start_recording.assert_called_once()
        assert listener.is_recording is True

    def test_different_hotkey_configurations(self, mock_config):
        """Test initialization with different hotkey configurations."""
        mock_app = Mock()

        # Test different combinations
        test_cases = [
            ("ctrl+alt+r", "ctrl+alt+esc"),
            ("shift+f12", "ctrl+shift+f12"),
            ("ctrl+`", "ctrl+shift+`"),
        ]

        for toggle, emergency in test_cases:
            mock_config.hotkeys.toggle_recording = toggle
            mock_config.hotkeys.emergency_stop = emergency

            listener = HotkeyListener(mock_config, mock_app)

            assert listener.toggle_hotkey == toggle
            assert listener.emergency_hotkey == emergency

    @patch('keyboard.add_hotkey')
    def test_start_multiple_times(self, mock_add_hotkey, mock_config):
        """Test that calling start() multiple times works correctly."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)

        listener.start()
        first_count = mock_add_hotkey.call_count

        listener.start()  # Call again
        second_count = mock_add_hotkey.call_count

        # Should register hotkeys again
        assert second_count == first_count * 2

    @patch('keyboard.add_hotkey')
    @patch('keyboard.remove_hotkey')
    def test_stop_without_start(self, mock_remove_hotkey, mock_add_hotkey, mock_config):
        """Test that stop() without start() doesn't crash."""
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)

        # Should not raise exception
        listener.stop()

        # Should not call remove since nothing was added
        mock_remove_hotkey.assert_not_called()

    @patch('keyboard.add_hotkey')
    def test_hotkey_registration_exception_handling(self, mock_add_hotkey, mock_config):
        """Test handling of hotkey registration failures."""
        mock_add_hotkey.side_effect = Exception("Hotkey already registered")
        mock_app = Mock()

        listener = HotkeyListener(mock_config, mock_app)

        # Should raise HotkeyError
        with pytest.raises(HotkeyError, match="Failed to register hotkeys"):
            listener.start()
