"""
Tests for configuration schema and manager.
"""

import pytest
from pathlib import Path
import tempfile
from pydantic import ValidationError

from Quill.config import (
    Config,
    AppConfig,
    TranscriptionConfig,
    AudioConfig,
    HotkeysConfig,
    ConfigManager,
)

pytestmark = pytest.mark.unit


class TestConfigSchema:
    """Test Pydantic config schemas."""

    def test_default_config(self):
        """Test that default config is valid."""
        config = Config()
        assert config.app.log_level == "info"
        assert config.transcription.model_size == "small"
        assert config.audio.sample_rate == 16000
        assert config.hotkeys.toggle_recording == "ctrl+shift+d"

    def test_app_config_validation(self):
        """Test AppConfig validation."""
        # Valid config
        app = AppConfig(log_level="debug", log_max_size_mb=20)
        assert app.log_level == "debug"
        assert app.log_max_size_mb == 20

        # Invalid log level
        with pytest.raises(ValidationError):
            AppConfig(log_level="invalid")

        # Invalid log size (negative)
        with pytest.raises(ValidationError):
            AppConfig(log_max_size_mb=-1)

    def test_transcription_config_validation(self):
        """Test TranscriptionConfig validation."""
        # Valid config
        trans = TranscriptionConfig(model_size="medium", device="cpu")
        assert trans.model_size == "medium"
        assert trans.device == "cpu"

        # Invalid model size
        with pytest.raises(ValidationError):
            TranscriptionConfig(model_size="invalid")

        # Invalid device
        with pytest.raises(ValidationError):
            TranscriptionConfig(device="invalid")

    def test_audio_config_validation(self):
        """Test AudioConfig validation."""
        # Valid config
        audio = AudioConfig(sample_rate=16000, channels=1)
        assert audio.sample_rate == 16000
        assert audio.channels == 1

        # Invalid sample rate (negative)
        with pytest.raises(ValidationError):
            AudioConfig(sample_rate=-1)

        # Invalid channels (too many)
        with pytest.raises(ValidationError):
            AudioConfig(channels=3)

        # Invalid vad_threshold (out of range)
        with pytest.raises(ValidationError):
            AudioConfig(vad_threshold=1.5)

    def test_hotkeys_config_validation(self):
        """Test HotkeysConfig validation."""
        # Valid config
        hotkeys = HotkeysConfig(
            toggle_recording="ctrl+alt+r", emergency_stop="ctrl+shift+q"
        )
        assert hotkeys.toggle_recording == "ctrl+alt+r"

        # Invalid hotkey format (no modifier)
        with pytest.raises(ValidationError):
            HotkeysConfig(toggle_recording="r")

    def test_config_forbids_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            Config(unknown_field="value")

    def test_lifecycle_config(self):
        """Test lifecycle configuration."""
        config = Config()
        assert config.transcription.lifecycle.lazy_load is True
        assert config.transcription.lifecycle.unload_after_minutes == 5

        # Test -1 (immediate unload)
        trans = TranscriptionConfig()
        trans.lifecycle.unload_after_minutes = -1
        assert trans.lifecycle.unload_after_minutes == -1

        # Test invalid (too negative)
        with pytest.raises(ValidationError):
            TranscriptionConfig(lifecycle={"unload_after_minutes": -2})

    def test_mock_config_fixture_is_valid(self, mock_config):
        """Ensure mock_config fixture is schema-compliant.

        This prevents future fixture mismatches from silently breaking tests.
        The mock_config fixture is used throughout the test suite, so it must
        always comply with the schema defined in src/Quill/config/schema.py.
        """
        # Verify it's a valid Config instance
        assert isinstance(mock_config, Config)

        # Verify critical fields match schema constraints
        assert mock_config.app.log_level in ["debug", "info", "warning", "error"]
        assert mock_config.transcription.model_size in ["tiny", "base", "small", "medium", "large"]
        assert mock_config.transcription.device in ["cuda", "cpu"]
        assert mock_config.text_injection.method in ["win32", "clipboard"]

        # Verify hotkey format (must have '+' separator)
        assert "+" in mock_config.hotkeys.toggle_recording
        assert "+" in mock_config.hotkeys.emergency_stop


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_load_valid_config(self):
        """Test loading a valid config file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  log_level: "debug"
  log_max_size_mb: 20

transcription:
  model_size: "medium"
  device: "cpu"
            """)
            temp_path = f.name

        try:
            config = ConfigManager.load(temp_path)
            assert config.app.log_level == "debug"
            assert config.app.log_max_size_mb == 20
            assert config.transcription.model_size == "medium"
            assert config.transcription.device == "cpu"
        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            ConfigManager.load("nonexistent.yaml")

    def test_load_with_defaults(self):
        """Test load_with_defaults returns defaults for missing file."""
        config = ConfigManager.load_with_defaults("nonexistent.yaml")
        assert isinstance(config, Config)
        assert config.app.log_level == "info"  # Default value

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse YAML"):
                ConfigManager.load(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_config_values(self):
        """Test loading YAML with invalid config values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app:
  log_level: "invalid_level"
            """)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="validation failed"):
                ConfigManager.load(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_save_config(self):
        """Test saving config to file."""
        config = Config()
        config.app.log_level = "debug"
        config.transcription.model_size = "large"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name

        try:
            manager = ConfigManager()
            manager.save(config, temp_path)

            # Verify file was created and can be loaded
            loaded_config = ConfigManager.load(temp_path)
            assert loaded_config.app.log_level == "debug"
            assert loaded_config.transcription.model_size == "large"
        finally:
            Path(temp_path).unlink()

    def test_validate_valid_config(self):
        """Test validating a valid config dict."""
        config_data = {
            "app": {"log_level": "info"},
            "transcription": {"model_size": "small"},
            "audio": {"sample_rate": 16000},
            "hotkeys": {"toggle_recording": "ctrl+shift+d"},
            "text_injection": {"method": "win32"},
            "ui": {"show_notifications": True},
            "advanced": {"max_recording_duration_seconds": 300},
        }

        is_valid, error = ConfigManager.validate(config_data)
        assert is_valid
        assert error is None

    def test_validate_invalid_config(self):
        """Test validating an invalid config dict."""
        config_data = {
            "app": {"log_level": "invalid_level"},
        }

        is_valid, error = ConfigManager.validate(config_data)
        assert not is_valid
        assert error is not None
        assert "validation" in error.lower()

    def test_load_empty_config_file(self):
        """Test loading an empty config file returns defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name

        try:
            config = ConfigManager.load(temp_path)
            assert isinstance(config, Config)
            assert config.app.log_level == "info"  # Default
        finally:
            Path(temp_path).unlink()
