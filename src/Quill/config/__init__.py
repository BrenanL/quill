"""Configuration management for Quill."""

from .schema import (
    Config,
    AppConfig,
    TranscriptionConfig,
    AudioConfig,
    HotkeysConfig,
    TextInjectionConfig,
    UIConfig,
    AdvancedConfig,
    LifecycleConfig,
)
from .manager import ConfigManager

__all__ = [
    "Config",
    "AppConfig",
    "TranscriptionConfig",
    "AudioConfig",
    "HotkeysConfig",
    "TextInjectionConfig",
    "UIConfig",
    "AdvancedConfig",
    "LifecycleConfig",
    "ConfigManager",
]
