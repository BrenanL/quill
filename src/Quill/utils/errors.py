"""
Custom exception types for Quill.

All exceptions inherit from QuillError for consistent error handling.
"""


class QuillError(Exception):
    """Base exception for all Quill errors."""

    pass


class ConfigError(QuillError):
    """Configuration-related errors (invalid config, missing fields, etc.)."""

    pass


class AudioCaptureError(QuillError):
    """Audio capture errors (device not found, permission denied, etc.)."""

    pass


class TranscriptionError(QuillError):
    """Transcription errors (model load failed, inference failed, etc.)."""

    pass


class InjectionError(QuillError):
    """Text injection errors (injection failed, no active window, etc.)."""

    pass


class HotkeyError(QuillError):
    """Hotkey-related errors (conflict, invalid binding, etc.)."""

    pass


class ModelError(QuillError):
    """Model management errors (download failed, load failed, OOM, etc.)."""

    pass
