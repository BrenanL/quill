"""Global hotkey listener."""

from typing import Callable, Optional
from loguru import logger

from ..utils.errors import HotkeyError


class HotkeyListener:
    """Listen for global hotkeys using keyboard library."""

    def __init__(self, toggle_recording: str, emergency_stop: str):
        """
        Initialize hotkey listener.

        Args:
            toggle_recording: Hotkey for toggle recording (e.g., "ctrl+shift+d")
            emergency_stop: Emergency stop hotkey
        """
        self.toggle_hotkey = toggle_recording.lower()
        self.emergency_hotkey = emergency_stop.lower()

        self.is_recording = False
        self.on_toggle_callback: Optional[Callable] = None
        self.on_emergency_callback: Optional[Callable] = None

        try:
            import keyboard as kb
            self.keyboard = kb
        except ImportError:
            raise HotkeyError("keyboard library not available")

    def start(self, on_toggle: Callable, on_emergency: Callable) -> None:
        """
        Start listening for hotkeys.

        Args:
            on_toggle: Callback for toggle recording
            on_emergency: Callback for emergency stop
        """
        self.on_toggle_callback = on_toggle
        self.on_emergency_callback = on_emergency

        try:
            # Register hotkeys
            self.keyboard.add_hotkey(self.toggle_hotkey, self._on_toggle_pressed)
            self.keyboard.add_hotkey(self.emergency_hotkey, self._on_emergency_pressed)

            logger.info(f"Hotkeys registered: {self.toggle_hotkey}, {self.emergency_hotkey}")

        except Exception as e:
            raise HotkeyError(f"Failed to register hotkeys: {e}")

    def _on_toggle_pressed(self) -> None:
        """Handle toggle recording hotkey."""
        if self.on_toggle_callback:
            try:
                self.on_toggle_callback()
            except Exception as e:
                logger.error(f"Error in toggle callback: {e}")

    def _on_emergency_pressed(self) -> None:
        """Handle emergency stop hotkey."""
        if self.on_emergency_callback:
            try:
                self.on_emergency_callback()
            except Exception as e:
                logger.error(f"Error in emergency callback: {e}")

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        try:
            self.keyboard.remove_hotkey(self.toggle_hotkey)
            self.keyboard.remove_hotkey(self.emergency_hotkey)
            logger.info("Hotkeys unregistered")
        except Exception as e:
            logger.warning(f"Error stopping hotkeys: {e}")
