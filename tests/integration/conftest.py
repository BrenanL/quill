# tests/integration/conftest.py
"""
Integration test specific fixtures.
"""

import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def real_audio_capture_config():
    """Configuration suitable for real AudioCapture testing."""
    from Quill.config.schema import Config

    return Config(
        audio={
            "sample_rate": 16000,
            "channels": 1,
            "chunk_duration_ms": 100,
            "noise_gate_threshold": 0.01,
        },
        transcription={
            "model_size": "tiny",  # Use tiny for faster integration tests
            "device": "cpu",
            "compute_type": "int8",
        },
        # Other config sections use defaults
    )

@pytest.fixture
def integration_temp_dirs():
    """Temporary directories for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        dirs = {
            "models": base / "models",
            "logs": base / "logs",
            "config": base / "config",
        }

        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        yield dirs
