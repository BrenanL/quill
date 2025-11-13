"""
Configuration schema for Quill using Pydantic.

Defines all configuration sections and validates YAML config files.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging


class AppConfig(BaseModel):
    """Application-level settings."""

    auto_start: bool = Field(
        default=False, description="Auto-start service when Windows logs in"
    )
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="Log level for application"
    )
    log_file: str = Field(default="logs/Quill.log", description="Log file location")
    log_max_size_mb: int = Field(
        default=10, description="Maximum log file size before rotation (MB)", gt=0
    )


class LifecycleConfig(BaseModel):
    """Model lifecycle management settings."""

    lazy_load: bool = Field(
        default=True, description="Load model when first needed (not at startup)"
    )
    unload_after_minutes: int = Field(
        default=5,
        description=(
            "Unload model after this many minutes of inactivity. "
            "0 = keep always, -1 = unload immediately"
        ),
        ge=-1,
    )
    show_progress: bool = Field(
        default=True, description="Show progress during model download/loading"
    )


class TranscriptionConfig(BaseModel):
    """Transcription engine settings."""

    backend: Literal["faster-whisper"] = Field(
        default="faster-whisper", description="Transcription backend (only faster-whisper in MVP)"
    )
    model_size: Literal["tiny", "base", "small", "medium", "large"] = Field(
        default="small", description="Whisper model size"
    )
    device: Literal["cuda", "cpu"] = Field(
        default="cuda", description="Compute device (cuda for GPU, cpu for CPU)"
    )
    compute_type: Literal["float16", "int8", "int8_float16"] = Field(
        default="float16", description="Compute type for inference"
    )
    language: str = Field(default="en", description="Language code (English only in MVP)")
    lifecycle: LifecycleConfig = Field(
        default_factory=LifecycleConfig, description="Model lifecycle management"
    )

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """Validate device and fall back to CPU if CUDA not available."""
        if v == "cuda":
            try:
                import torch

                if not torch.cuda.is_available():
                    logging.warning("CUDA not available, falling back to CPU")
                    return "cpu"
            except ImportError:
                logging.warning("PyTorch not installed, falling back to CPU")
                return "cpu"
        return v


class AudioConfig(BaseModel):
    """Audio capture settings."""

    sample_rate: int = Field(
        default=16000, description="Sample rate (Hz) - Whisper expects 16kHz", gt=0
    )
    channels: int = Field(default=1, description="Number of channels (1 = mono)", ge=1, le=2)
    chunk_duration_seconds: int = Field(
        default=5, description="Chunk duration in seconds for processing", gt=0
    )
    vad_threshold: float = Field(
        default=0.0,
        description="Voice Activity Detection threshold (0.0 = disabled, 1.0 = very aggressive)",
        ge=0.0,
        le=1.0,
    )
    noise_gate_threshold: float = Field(
        default=0.01,
        description="Noise gate: drop audio below this amplitude",
        ge=0.0,
        le=1.0,
    )


class HotkeysConfig(BaseModel):
    """Hotkey bindings."""

    toggle_recording: str = Field(
        default="ctrl+shift+d", description="Toggle recording on/off"
    )
    emergency_stop: str = Field(
        default="ctrl+shift+esc", description="Emergency stop (force stop if stuck)"
    )

    @field_validator("toggle_recording", "emergency_stop")
    @classmethod
    def validate_hotkey_format(cls, v: str) -> str:
        """Validate hotkey format (modifier+modifier+key)."""
        if not v or "+" not in v:
            raise ValueError(f"Invalid hotkey format: '{v}'. Expected format: 'modifier+key'")
        return v.lower()


class TextInjectionConfig(BaseModel):
    """Text injection settings."""

    method: Literal["win32", "clipboard"] = Field(
        default="win32", description="Injection method (win32 = Windows API, clipboard = fallback)"
    )
    typing_speed_cps: int = Field(
        default=0,
        description="Typing speed simulation (characters per second, 0 = instant)",
        ge=0,
    )
    key_delay_ms: int = Field(
        default=10, description="Delay between key events (milliseconds)", ge=0
    )


class UIConfig(BaseModel):
    """User interface settings."""

    tray_icon_theme: Literal["auto", "light", "dark"] = Field(
        default="auto", description="Tray icon theme"
    )
    show_notifications: bool = Field(
        default=True, description="Show notifications for state changes"
    )
    notification_duration_seconds: int = Field(
        default=3, description="Notification duration (seconds)", gt=0
    )
    success_flash_duration_ms: int = Field(
        default=1000, description="Flash success icon duration (milliseconds)", gt=0
    )


class AdvancedConfig(BaseModel):
    """Advanced settings."""

    max_recording_duration_seconds: int = Field(
        default=300, description="Maximum recording duration (seconds)", gt=0
    )
    audio_queue_size: int = Field(
        default=50, description="Audio queue size (number of chunks)", gt=0
    )
    model_load_retries: int = Field(
        default=3, description="Retry attempts for model loading", ge=0
    )
    transcription_timeout_seconds: int = Field(
        default=60, description="Timeout for transcription (seconds)", gt=0
    )


class Config(BaseModel):
    """Root configuration object."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    app: AppConfig = Field(default_factory=AppConfig, description="Application settings")
    transcription: TranscriptionConfig = Field(
        default_factory=TranscriptionConfig, description="Transcription settings"
    )
    audio: AudioConfig = Field(default_factory=AudioConfig, description="Audio settings")
    hotkeys: HotkeysConfig = Field(default_factory=HotkeysConfig, description="Hotkey settings")
    text_injection: TextInjectionConfig = Field(
        default_factory=TextInjectionConfig, description="Text injection settings"
    )
    ui: UIConfig = Field(default_factory=UIConfig, description="UI settings")
    advanced: AdvancedConfig = Field(
        default_factory=AdvancedConfig, description="Advanced settings"
    )
