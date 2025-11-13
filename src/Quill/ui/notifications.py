"""Toast notifications for Windows."""

import sys
from typing import Optional
from loguru import logger


class NotificationManager:
    """Manage toast notifications."""

    def __init__(self, enabled: bool = True, duration: int = 3):
        """
        Initialize notification manager.

        Args:
            enabled: Whether notifications are enabled
            duration: Default notification duration in seconds
        """
        self.enabled = enabled
        self.duration = duration

        # Try platform-specific notification
        if sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                self.toaster = ToastNotifier()
                self.method = "win10toast"
            except ImportError:
                logger.warning("win10toast not available, notifications disabled")
                self.method = "none"
        else:
            self.method = "none"

    def show(self, title: str, message: str, duration: Optional[int] = None) -> None:
        """
        Show notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Duration in seconds (optional)
        """
        if not self.enabled:
            return

        duration = duration or self.duration

        try:
            if self.method == "win10toast":
                # Show toast (non-blocking)
                self.toaster.show_toast(
                    title,
                    message,
                    duration=duration,
                    threaded=True,
                )
            else:
                # Fallback to console
                logger.info(f"[Notification] {title}: {message}")

        except Exception as e:
            logger.warning(f"Failed to show notification: {e}")

    def show_recording_started(self) -> None:
        """Show recording started notification."""
        self.show("Quill", "🔴 Recording...", duration=0)

    def show_processing(self) -> None:
        """Show processing notification."""
        self.show("Quill", "⚙️ Processing...", duration=0)

    def show_success(self) -> None:
        """Show success notification."""
        self.show("Quill", "✅ Text inserted", duration=self.duration)

    def show_error(self, error: str) -> None:
        """Show error notification."""
        self.show("Quill", f"⚠️ Error: {error[:50]}", duration=5)
