"""
Unit tests for WindowsTextInjector with mocked keyboard library.
"""

import pytest

# Mock pyperclip for tests
import sys
from unittest.mock import MagicMock
mock_pyperclip = MagicMock()
sys.modules["pyperclip"] = mock_pyperclip

from unittest.mock import Mock, patch, call

from Quill.injection.windows import WindowsTextInjector
from Quill.utils.errors import InjectionError

pytestmark = pytest.mark.unit


class TestWindowsTextInjectorMocked:
    """Unit tests for WindowsTextInjector using mocked keyboard."""

    @patch('keyboard.write')
    def test_inject_simple_text(self, mock_write, mock_config):
        """Test injecting simple text."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        injector.inject("Hello world")

        mock_write.assert_called_once_with("Hello world", delay=0.01)

    @patch('keyboard.write')
    def test_inject_empty_string(self, mock_write, mock_config):
        """Test injecting empty string."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        injector.inject("")

        # Empty string causes early return
        mock_write.assert_not_called()

    @patch('keyboard.write')
    def test_inject_with_special_characters(self, mock_write, mock_config):
        """Test injecting text with special characters."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = "Hello! @world #test $100 %done"
        injector.inject(text)

        mock_write.assert_called_once_with(text, delay=0.01)

    @patch('keyboard.write')
    def test_inject_with_newlines(self, mock_write, mock_config):
        """Test injecting text with newlines."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = "Line 1\nLine 2\nLine 3"
        injector.inject(text)

        mock_write.assert_called_once_with(text, delay=0.01)

    @patch('keyboard.write')
    def test_inject_with_unicode(self, mock_write, mock_config):
        """Test injecting Unicode text."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = "Hello 世界 🎤 café"
        injector.inject(text)

        mock_write.assert_called_once_with(text, delay=0.01)

    @patch('keyboard.write')
    def test_inject_respects_typing_speed(self, mock_write, mock_config):
        """Test that typing speed configuration is used."""
        mock_config.text_injection.typing_speed_cps = 50

        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )
        injector.inject("Test")

        # Delay should be calculated based on typing speed
        # delay = 1 / typing_speed_cps = 1 / 50 = 0.02
        mock_write.assert_called_once_with("Test", delay=0.02)

    @patch('keyboard.write')
    def test_inject_with_zero_typing_speed(self, mock_write, mock_config):
        """Test with zero typing speed (instant)."""
        mock_config.text_injection.typing_speed_cps = 0

        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )
        injector.inject("Fast")

        mock_write.assert_called_once_with("Fast", delay=0.01)

    @patch('keyboard.write')
    def test_inject_keyboard_method(self, mock_write, mock_config):
        """Test that keyboard method is used by default."""
        mock_config.text_injection.method = "keyboard"

        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )
        injector.inject("Test")

        mock_write.assert_called_once()

    @patch('keyboard.write')
    @patch('pyperclip.copy')
    @patch('pyperclip.paste')
    @patch('keyboard.send')
    def test_inject_clipboard_fallback(self, mock_send, mock_paste, mock_copy,
                                       mock_write, mock_config):
        """Test fallback to clipboard when keyboard fails."""
        # Make keyboard.write fail
        mock_write.side_effect = Exception("Keyboard injection failed")
        mock_paste.return_value = "old clipboard"

        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        # Should fallback to clipboard and not raise
        injector.inject("Test text")

        # Should have copied to clipboard
        mock_copy.assert_called()
        # Should have sent Ctrl+V
        mock_send.assert_called()

    @patch('keyboard.write')
    def test_inject_keyboard_failure_raises_error(self, mock_write, mock_config):
        """Test that keyboard failure with no fallback raises error."""
        # Make keyboard fail
        mock_write.side_effect = Exception("Keyboard error")

        # Disable clipboard fallback by making it also fail
        with patch('pyperclip.copy', side_effect=Exception("Clipboard error")):
            injector = WindowsTextInjector(
                typing_speed_cps=mock_config.text_injection.typing_speed_cps,
                key_delay_ms=mock_config.text_injection.key_delay_ms
            )

            with pytest.raises(InjectionError, match="All injection methods failed"):
                injector.inject("Test")

    @patch('keyboard.write')
    def test_inject_long_text(self, mock_write, mock_config):
        """Test injecting long text."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        long_text = "A" * 10000
        injector.inject(long_text)

        mock_write.assert_called_once_with(long_text, delay=0.01)

    @patch('keyboard.write')
    def test_inject_multiline_text(self, mock_write, mock_config):
        """Test injecting multiline text."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = """This is a
        multiline
        text with
        multiple lines"""

        injector.inject(text)

        mock_write.assert_called_once_with(text, delay=0.01)

    @patch('keyboard.write')
    def test_inject_tabs_and_spaces(self, mock_write, mock_config):
        """Test injecting text with tabs and spaces."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = "Line1\tTabbed\t\tDouble\n    Indented"
        injector.inject(text)

        mock_write.assert_called_once_with(text, delay=0.01)

    def test_init_with_different_methods(self, mock_config):
        """Test initialization with different injection methods."""
        # Keyboard method
        mock_config.text_injection.method = "keyboard"
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )
        assert injector.method == "keyboard"

        # Clipboard method
        mock_config.text_injection.method = "clipboard"
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )
        assert injector.method == "clipboard"

    @patch('keyboard.write')
    def test_inject_strips_no_text(self, mock_write, mock_config):
        """Test that injector doesn't strip text (preserves whitespace)."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        text = "  Leading and trailing  "
        injector.inject(text)

        # Should preserve whitespace
        mock_write.assert_called_once_with(text, delay=0.01)

    @patch('keyboard.write')
    def test_multiple_injections(self, mock_write, mock_config):
        """Test multiple sequential injections."""
        injector = WindowsTextInjector(
            typing_speed_cps=mock_config.text_injection.typing_speed_cps,
            key_delay_ms=mock_config.text_injection.key_delay_ms
        )

        injector.inject("First")
        injector.inject("Second")
        injector.inject("Third")

        assert mock_write.call_count == 3
        assert mock_write.call_args_list == [
            call("First", delay=0.01),
            call("Second", delay=0.01),
            call("Third", delay=0.01),
        ]
