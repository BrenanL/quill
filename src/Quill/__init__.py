"""Quill - Local speech-to-text dictation tool."""

__version__ = "0.1.0"

from .app import QuillApp
from .config import Config, ConfigManager

__all__ = ["QuillApp", "Config", "ConfigManager", "__version__"]
