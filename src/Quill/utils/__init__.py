"""Utility modules for Quill."""

from .errors import (
    QuillError,
    ConfigError,
    AudioCaptureError,
    TranscriptionError,
    InjectionError,
    HotkeyError,
    ModelError,
)
from .logging import setup_logging, get_logger

__all__ = [
    "QuillError",
    "ConfigError",
    "AudioCaptureError",
    "TranscriptionError",
    "InjectionError",
    "HotkeyError",
    "ModelError",
    "setup_logging",
    "get_logger",
]
