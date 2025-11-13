"""Windows text injection using keyboard simulation."""

import time
from loguru import logger

from ..utils.errors import InjectionError


class WindowsTextInjector:
    """Inject text into Windows applications."""

    def __init__(self, typing_speed_cps: int = 0, key_delay_ms: int = 10):
        """
        Initialize text injector.

        Args:
            typing_speed_cps: Characters per second (0 = instant)
            key_delay_ms: Delay between key events in milliseconds
        """
        self.typing_speed = typing_speed_cps
        self.key_delay = key_delay_ms / 1000.0  # Convert to seconds

        # Try to import keyboard library
        try:
            import keyboard as kb
            self.keyboard = kb
            self.method = "keyboard"
            logger.info("Text injection using keyboard library")
        except ImportError:
            # Fallback to pyperclip + simulated paste
            try:
                import pyperclip
                self.pyperclip = pyperclip
                self.method = "clipboard"
                logger.warning("keyboard library not available, using clipboard fallback")
            except ImportError:
                raise InjectionError("No text injection method available (need keyboard or pyperclip)")

    def inject(self, text: str) -> None:
        """
        Inject text at cursor position.

        Args:
            text: Text to inject

        Raises:
            InjectionError: If injection fails
        """
        if not text:
            return

        try:
            if self.method == "keyboard":
                self._inject_via_keyboard(text)
            else:
                self._inject_via_clipboard(text)

            logger.info(f"Injected {len(text)} characters")

        except Exception as e:
            # Try clipboard fallback
            if self.method == "keyboard":
                logger.warning(f"Keyboard injection failed, trying clipboard: {e}")
                try:
                    self._inject_via_clipboard(text)
                    return
                except Exception as e2:
                    raise InjectionError(f"All injection methods failed: {e}, {e2}")

            raise InjectionError(f"Text injection failed: {e}")

    def _inject_via_keyboard(self, text: str) -> None:
        """Inject text via keyboard simulation."""
        # Small delay to allow window focus
        time.sleep(0.05)

        # Type the text
        self.keyboard.write(text, delay=self.key_delay)

        # Calculate typing delay if needed
        if self.typing_speed > 0:
            delay_per_char = 1.0 / self.typing_speed
            total_delay = delay_per_char * len(text)
            time.sleep(total_delay)

    def _inject_via_clipboard(self, text: str) -> None:
        """Inject text via clipboard + Ctrl+V."""
        # Save current clipboard
        try:
            old_clipboard = self.pyperclip.paste()
        except Exception:
            old_clipboard = ""

        # Copy text to clipboard
        self.pyperclip.copy(text)

        # Small delay
        time.sleep(0.05)

        # Simulate Ctrl+V using keyboard if available
        if hasattr(self, 'keyboard'):
            self.keyboard.send('ctrl+v')
        else:
            # Without keyboard library, we can't paste automatically
            # User will need to manually paste
            logger.warning("Text copied to clipboard (manual paste required)")
            return

        # Restore old clipboard (optional)
        time.sleep(0.1)
        try:
            self.pyperclip.copy(old_clipboard)
        except Exception:
            pass
