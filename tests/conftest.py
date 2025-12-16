# tests/conftest.py
"""
Shared fixtures for all tests across all directories.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import numpy as np

# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """
    Mock configuration for unit tests.

    Returns a valid Config object with safe defaults (CPU, int8).

    IMPORTANT: This fixture MUST always comply with the schema in
    src/Quill/config/schema.py. If you modify this fixture, ensure
    all values pass schema validation (see test_mock_config_fixture_is_valid).
    """
    from Quill.config.schema import Config

    config = Config(
        app={
            "log_level": "info",
            "log_file": "logs/test.log",
            "log_max_size_mb": 10,
        },
        transcription={
            "model_size": "small",
            "device": "cpu",
            "compute_type": "int8",
            "language": "en",
            "lifecycle": {
                "lazy_load": True,
                "unload_after_minutes": 5,
            }
        },
        audio={
            "sample_rate": 16000,
            "channels": 1,
            "chunk_duration_ms": 100,
            "noise_gate_threshold": 0.01,
        },
        hotkeys={
            "toggle_recording": "ctrl+shift+d",
            "emergency_stop": "ctrl+shift+esc",
        },
        text_injection={
            "method": "win32",
            "typing_speed_cps": 0,
        },
        ui={
            "show_notifications": True,
            "notification_duration_seconds": 3,
        },
    )

    return config

@pytest.fixture
def temp_config_file():
    """Temporary YAML config file for file I/O tests."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
app:
  log_level: info

transcription:
  model_size: small
  device: cpu
  compute_type: int8
  language: en
  lifecycle:
    lazy_load: true
    unload_after_minutes: 5

audio:
  sample_rate: 16000
  channels: 1

hotkeys:
  toggle_recording: ctrl+shift+d
  emergency_stop: ctrl+shift+esc
        """)
        path = f.name

    yield Path(path)
    Path(path).unlink(missing_ok=True)

# ============================================================================
# Audio Fixtures
# ============================================================================

@pytest.fixture
def mock_audio_data():
    """
    Mock audio data for unit tests.

    Returns 1 second of random audio at 16kHz, mono, float32.
    """
    return np.random.randn(16000).astype(np.float32)

@pytest.fixture
def silence_audio():
    """1 second of silence."""
    return np.zeros(16000, dtype=np.float32)

@pytest.fixture
def tone_audio():
    """1 second of 440Hz tone (A note)."""
    t = np.linspace(0, 1, 16000, dtype=np.float32)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)

# ============================================================================
# Mock Component Fixtures
# ============================================================================

@pytest.fixture
def mock_whisper_model():
    """
    Mock WhisperModel for unit tests.

    Simulates faster-whisper.WhisperModel without loading real model.
    """
    mock = Mock()

    def mock_transcribe(audio, **kwargs):
        segment = Mock()
        segment.text = "mock transcription result"
        info = Mock()
        info.language = "en"
        return [segment], info

    mock.transcribe = Mock(side_effect=mock_transcribe)
    return mock

@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice for AudioCapture tests."""
    with patch('sounddevice.InputStream') as mock_stream:
        # Create a mock instance that InputStream returns
        mock_instance = MagicMock()
        mock_instance.__enter__ = Mock(return_value=mock_instance)
        mock_instance.__exit__ = Mock(return_value=False)
        mock_stream.return_value = mock_instance
        yield mock_stream

@pytest.fixture
def mock_keyboard():
    """Mock keyboard library for text injection and hotkey tests."""
    with patch('keyboard.add_hotkey') as mock_add, \
         patch('keyboard.remove_hotkey') as mock_remove, \
         patch('keyboard.write') as mock_write:
        yield {
            'add_hotkey': mock_add,
            'remove_hotkey': mock_remove,
            'write': mock_write
        }

@pytest.fixture
def mock_toaster():
    """Mock win10toast for notification tests."""
    with patch('win10toast.ToastNotifier') as mock_toast:
        mock_instance = MagicMock()
        mock_toast.return_value = mock_instance
        yield mock_instance

# ============================================================================
# Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_models_dir():
    """Temporary models directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def temp_logs_dir():
    """Temporary logs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
