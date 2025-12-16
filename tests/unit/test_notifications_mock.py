"""
Unit tests for NotificationManager with mocked win10toast.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Create mock win10toast module
mock_win10toast = MagicMock()
sys.modules['win10toast'] = mock_win10toast

from Quill.ui.notifications import NotificationManager

pytestmark = pytest.mark.unit


class TestNotificationManagerMocked:
    """Unit tests for NotificationManager using mocked win10toast."""

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_init_creates_toaster(self, mock_toaster_class, mock_config):
        """Test initialization creates ToastNotifier."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )

        mock_toaster_class.assert_called_once()
        assert manager.toaster is mock_instance

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_notification_calls_toaster(self, mock_toaster_class, mock_config):
        """Test that show() calls toaster.show_toast()."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show("Test Title", "Test message")

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]  # positional args
        assert call_args[0] == "Test Title"
        assert call_args[1] == "Test message"

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_notification_with_duration(self, mock_toaster_class, mock_config):
        """Test notification duration from config."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(enabled=True, duration=5)
        manager.show("Title", "Message")

        call_args = mock_instance.show_toast.call_args[1]
        assert call_args["duration"] == 5

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_notification_when_disabled(self, mock_toaster_class, mock_config):
        """Test that notifications don't show when disabled in config."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(enabled=False, duration=3)
        manager.show("Title", "Message")

        # Should not call show_toast
        mock_instance.show_toast.assert_not_called()

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_recording_notification(self, mock_toaster_class, mock_config):
        """Test showing recording started notification."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show_recording_started()

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "Recording" in call_args[1]

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_processing_notification(self, mock_toaster_class, mock_config):
        """Test showing processing notification."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show_processing()

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "Processing" in call_args[1]

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_success_notification(self, mock_toaster_class, mock_config):
        """Test showing success notification."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show_success()

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "inserted" in call_args[1].lower()

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_error_notification(self, mock_toaster_class, mock_config):
        """Test showing error notification."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show_error("Test error message")

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "Error" in call_args[1] or "error" in call_args[1]
        assert "Test error message" in call_args[1]

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_show_model_loading_notification(self, mock_toaster_class, mock_config):
        """Test showing model loading notification (if method exists)."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )

        # Skip test if method doesn't exist
        if not hasattr(manager, 'show_model_loading'):
            pytest.skip("show_model_loading method not implemented")

        manager.show_model_loading("small")

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "small" in call_args[1]
        assert "Loading" in call_args[1] or "loading" in call_args[1]

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_multiple_notifications(self, mock_toaster_class, mock_config):
        """Test showing multiple notifications in sequence."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )

        manager.show_recording_started()
        manager.show_processing()
        manager.show_success()

        assert mock_instance.show_toast.call_count == 3

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_notification_failure_doesnt_crash(self, mock_toaster_class, mock_config):
        """Test that notification failures don't crash the app."""
        mock_instance = MagicMock()
        mock_instance.show_toast.side_effect = Exception("Toast failed")
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )

        # Should not raise exception
        manager.show("Title", "Message")

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_long_message_truncation(self, mock_toaster_class, mock_config):
        """Test that long messages are handled."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )

        long_message = "A" * 1000
        manager.show("Title", long_message)

        # Should still call show_toast (let toaster handle truncation)
        mock_instance.show_toast.assert_called_once()

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_empty_message(self, mock_toaster_class, mock_config):
        """Test showing notification with empty message."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show("Title", "")

        mock_instance.show_toast.assert_called_once()

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_unicode_in_notifications(self, mock_toaster_class, mock_config):
        """Test notifications with Unicode characters."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show("🎤 Quill", "Recording... 🔴")

        mock_instance.show_toast.assert_called_once()
        call_args = mock_instance.show_toast.call_args[0]
        assert "🎤" in call_args[0]
        assert "🔴" in call_args[1]

    @patch('sys.platform', 'win32')
    @patch('win10toast.ToastNotifier')
    def test_notification_threading(self, mock_toaster_class, mock_config):
        """Test that notifications use threaded mode."""
        mock_instance = MagicMock()
        mock_toaster_class.return_value = mock_instance

        manager = NotificationManager(
            enabled=mock_config.ui.show_notifications,
            duration=mock_config.ui.notification_duration_seconds
        )
        manager.show("Title", "Message")

        call_args = mock_instance.show_toast.call_args[1]
        # Should use threaded mode to not block
        assert call_args.get("threaded", False) is True
