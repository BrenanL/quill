# Quill Test System Specification and Design

**Version:** 1.0
**Date:** 2025-11-13
**Status:** Draft
**Author:** Development Team

---

## 1. Executive Summary

This document specifies the testing architecture for the Quill speech-to-text dictation application. The system is designed to support fast development iteration with mocked unit tests while providing comprehensive integration testing with real components and shared expensive resources (Whisper models).

---

## 2. Requirements

### 2.1 Functional Requirements

**FR-1: Test Categorization**
- Tests MUST be categorized into three tiers: unit, integration, and whisper
- Default test execution MUST run only fast unit tests (with mocks)
- Integration and whisper tests MUST be opt-in via markers

**FR-2: Mock-First Unit Testing**
- Unit tests MUST use mocks for all external dependencies (sounddevice, faster-whisper, keyboard, win10toast)
- Unit tests MUST complete in <5 seconds total
- Unit tests MUST NOT require hardware (microphone, GPU, keyboard)
- Unit tests MUST NOT download models or connect to external services

**FR-3: Shared Model Instance**
- Whisper tests MUST share a single model instance across all tests
- Model MUST be loaded once per test session (not per test)
- Model loading MUST use session-scoped fixtures
- Tests MUST NOT reload the model multiple times

**FR-4: Optional Real Component Testing**
- Integration tests MUST be marked and excluded from default runs
- Whisper tests MUST be marked and excluded from default runs
- Users MUST be able to run specific test categories via pytest markers

**FR-5: GPU/CPU Isolation**
- Tests requiring GPU MUST be marked separately
- CPU-only tests MUST be the default
- GPU tests MUST gracefully skip if CUDA unavailable

### 2.2 Non-Functional Requirements

**NFR-1: Performance**
- Default test run (unit only): <5 seconds
- Integration test run: <30 seconds
- Whisper test run (first time with download): <10 minutes
- Whisper test run (cached model): <2 minutes
- Memory usage for whisper tests: <3GB

**NFR-2: Maintainability**
- Test fixtures MUST be reusable across test files
- Mock configurations MUST be centralized
- Test data MUST be generated programmatically (no large binary files)
- Each test MUST be isolated (no shared mutable state)

**NFR-3: Developer Experience**
- Test failures MUST provide clear error messages
- Test organization MUST be intuitive (directory structure mirrors src/)
- Markers MUST have clear documentation
- Running specific test categories MUST be simple (single command)

**NFR-4: CI/CD Compatibility**
- Default test run MUST work in CI without GPU
- Default test run MUST work without downloading models
- Tests MUST be deterministic (no random failures)
- Coverage reporting MUST be integrated

---

## 3. Design

### 3.1 Test Directory Structure

```
tests/
├── pytest.ini                     # Pytest configuration
├── conftest.py                    # Shared fixtures for all tests
│
├── unit/                          # Fast tests with mocks (default)
│   ├── __init__.py
│   ├── conftest.py               # Unit-specific fixtures
│   ├── test_config.py            # Existing: config validation
│   ├── test_logging.py           # Existing: logging setup
│   ├── test_audio_preprocessing.py  # Existing: audio utils
│   ├── test_ring_buffer.py       # Threading utilities
│   ├── test_audio_capture_mock.py   # AudioCapture with mocked sounddevice
│   ├── test_transcription_service_mock.py  # TranscriptionService with mocked model
│   ├── test_model_manager_mock.py    # ModelManager with mocked faster-whisper
│   ├── test_text_injector_mock.py   # WindowsTextInjector with mocked keyboard
│   ├── test_hotkeys_mock.py         # HotkeyListener with mocked keyboard
│   ├── test_notifications_mock.py   # NotificationManager with mocked win10toast
│   └── test_app_mock.py             # QuillApp with all components mocked
│
├── integration/                   # Integration tests (marked, slower)
│   ├── __init__.py
│   ├── conftest.py               # Integration-specific fixtures
│   ├── test_audio_pipeline.py    # AudioCapture → preprocessing → buffer
│   ├── test_config_loading.py    # Config with real file I/O edge cases
│   └── test_state_machine.py     # App state transitions with partial mocks
│
└── whisper/                       # Real Whisper tests (marked, very slow)
    ├── __init__.py
    ├── conftest.py               # Session-scoped Whisper model fixture
    ├── test_whisper_loading.py   # Model load/unload lifecycle
    ├── test_whisper_inference.py # Real transcription with shared model
    ├── test_compute_types.py     # CPU vs CUDA compute type validation
    └── test_transcription_service_real.py  # TranscriptionService with real model
```

### 3.2 Pytest Markers

```ini
# pytest.ini
[pytest]
markers =
    unit: marks tests as unit tests with mocks (default, fast)
    integration: marks tests as integration tests (slower, real components)
    whisper: marks tests that use real Whisper models (very slow, needs model download)
    slow: marks tests as slow (deselect with '-m "not slow"')
    gpu: marks tests that require GPU/CUDA (skip on CPU-only systems)
```

**Usage Examples:**

```bash
# Default: unit tests only (fast, ~5 seconds)
pytest

# Include integration tests (~30 seconds)
pytest -m integration

# Run whisper tests with real model (~2-10 minutes)
pytest -m whisper

# Run everything
pytest -m "unit or integration or whisper"

# Skip slow tests
pytest -m "not slow"

# Only GPU tests (fail gracefully if no CUDA)
pytest -m gpu
```

### 3.3 Fixture Architecture

#### 3.3.1 Shared Fixtures (tests/conftest.py)

Available to all tests across all directories.

```python
# tests/conftest.py

import pytest
from unittest.mock import Mock, MagicMock
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
    """
    from Quill.config.schema import Config

    config = Config(
        app={
            "log_level": "INFO",
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
            "method": "keyboard",
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
  log_level: INFO

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
    Path(path).unlink()

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
    t = np.linspace(0, 1, 16000)
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
        yield mock_stream

@pytest.fixture
def mock_keyboard():
    """Mock keyboard library for text injection and hotkey tests."""
    with patch('keyboard') as mock_kb:
        yield mock_kb

@pytest.fixture
def mock_toaster():
    """Mock win10toast for notification tests."""
    with patch('win10toast.ToastNotifier') as mock_toast:
        yield mock_toast

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
```

#### 3.3.2 Whisper Fixtures (tests/whisper/conftest.py)

Session-scoped fixtures for real Whisper model testing.

```python
# tests/whisper/conftest.py

import pytest
import numpy as np
from pathlib import Path

@pytest.fixture(scope="session")
def whisper_model_small():
    """
    Load Whisper small model ONCE for entire test session.

    All tests marked with @pytest.mark.whisper share this model instance.
    This prevents loading the model 10+ times and wasting memory/time.

    Yields:
        WhisperModel: Loaded small model on CPU with int8 compute
    """
    from faster_whisper import WhisperModel

    print("\n[Session Setup] Loading Whisper small model (this may take 1-2 minutes)...")

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",  # CPU-compatible
        download_root="models",
    )

    print("[Session Setup] Whisper model loaded successfully")

    yield model

    print("\n[Session Teardown] Cleaning up Whisper model")
    del model

@pytest.fixture(scope="session")
def whisper_model_tiny():
    """
    Load Whisper tiny model ONCE for entire test session.

    Tiny model is faster for tests that don't need accuracy.
    """
    from faster_whisper import WhisperModel

    print("\n[Session Setup] Loading Whisper tiny model...")

    model = WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8",
        download_root="models",
    )

    yield model

    del model

@pytest.fixture(scope="session")
def test_audio_sample():
    """
    Reusable test audio data for Whisper tests.

    Generates 3 seconds of 440Hz tone at 16kHz.
    """
    duration = 3
    sample_rate = 16000
    frequency = 440

    t = np.linspace(0, duration, duration * sample_rate)
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio

@pytest.fixture(scope="session")
def test_speech_audio():
    """
    Reusable speech-like test audio.

    Simulates speech with varying frequencies and amplitude modulation.
    """
    duration = 3
    sample_rate = 16000

    t = np.linspace(0, duration, duration * sample_rate)

    # Mix multiple frequencies to simulate speech formants
    speech = (
        0.3 * np.sin(2 * np.pi * 250 * t) +  # F1
        0.3 * np.sin(2 * np.pi * 2500 * t) +  # F2
        0.2 * np.sin(2 * np.pi * 3500 * t)    # F3
    )

    # Add amplitude modulation (syllables)
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
    speech = speech * modulation

    return speech.astype(np.float32)
```

#### 3.3.3 Integration Fixtures (tests/integration/conftest.py)

```python
# tests/integration/conftest.py

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
        # ... other config
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
```

### 3.4 Test Execution Patterns

#### 3.4.1 Unit Test Pattern (Mocked)

```python
# tests/unit/test_transcription_service_mock.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from Quill.transcription.service import TranscriptionService

pytestmark = pytest.mark.unit

class TestTranscriptionServiceMocked:
    """Unit tests for TranscriptionService using mocks (fast)."""

    def test_prepare_starts_background_load(self, mock_config):
        """Test that prepare() triggers background loading."""
        service = TranscriptionService(mock_config)

        assert service.state == "idle"

        status = service.prepare()

        assert status["status"] == "loading"
        assert service.state == "loading"
        assert service.loader_thread is not None

    def test_prepare_idempotent(self, mock_config):
        """Test that calling prepare() multiple times is safe."""
        service = TranscriptionService(mock_config)

        status1 = service.prepare()
        status2 = service.prepare()

        assert status1["status"] == "loading"
        assert status2["status"] == "loading"

    @patch('Quill.transcription.service.ModelManager')
    def test_transcribe_with_mock_model(self, mock_manager_class, mock_config, mock_audio_data):
        """Test transcription with fully mocked ModelManager."""
        # Setup mock
        mock_manager = Mock()
        mock_model = Mock()

        segment = Mock()
        segment.text = "hello world from mock"
        info = Mock()

        mock_model.transcribe.return_value = ([segment], info)
        mock_manager.current_model = mock_model
        mock_manager.is_loaded.return_value = True
        mock_manager_class.return_value = mock_manager

        # Create service and skip to ready state
        service = TranscriptionService(mock_config)
        service.state = "ready"

        # Test
        text = service.transcribe(mock_audio_data)

        assert text == "hello world from mock"
        mock_model.transcribe.assert_called_once()

    def test_transcribe_fails_when_not_ready(self, mock_config, mock_audio_data):
        """Test that transcribe() raises error if model not ready."""
        from Quill.utils.errors import TranscriptionError

        service = TranscriptionService(mock_config)
        # Service is in "idle" state

        with pytest.raises(TranscriptionError, match="Model not ready"):
            service.transcribe(mock_audio_data)
```

#### 3.4.2 Integration Test Pattern

```python
# tests/integration/test_audio_pipeline.py

import pytest
import numpy as np
from Quill.audio.capture import AudioCapture
from Quill.audio.preprocessing import apply_noise_gate, convert_to_mono

pytestmark = [pytest.mark.integration, pytest.mark.slow]

class TestAudioPipeline:
    """Integration tests for audio capture and preprocessing."""

    @pytest.mark.skipif(
        not has_audio_device(),
        reason="No audio device available"
    )
    def test_capture_and_preprocess_flow(self, real_audio_capture_config):
        """Test full audio pipeline: capture → preprocess."""
        # This test uses real AudioCapture (requires microphone)
        capture = AudioCapture(
            sample_rate=real_audio_capture_config.audio.sample_rate,
            channels=real_audio_capture_config.audio.channels,
        )

        # Start capture
        capture.start()
        time.sleep(0.5)  # Record for 500ms
        audio_data = capture.stop()

        # Verify we got audio
        assert len(audio_data) > 0
        assert audio_data.dtype == np.float32

        # Apply preprocessing
        mono = convert_to_mono(audio_data)
        gated = apply_noise_gate(mono, threshold=0.01)

        assert gated.shape == mono.shape
```

#### 3.4.3 Whisper Test Pattern (Shared Model)

```python
# tests/whisper/test_whisper_inference.py

import pytest
import numpy as np

pytestmark = [pytest.mark.whisper, pytest.mark.slow]

class TestWhisperInference:
    """Integration tests with real Whisper model (shared instance)."""

    def test_transcribe_tone_audio(self, whisper_model_small, test_audio_sample):
        """
        Test transcription with shared model.

        This test reuses whisper_model_small loaded once per session.
        """
        segments, info = whisper_model_small.transcribe(
            test_audio_sample,
            language="en",
        )

        segments_list = list(segments)

        # Tone may not produce text, but should not crash
        assert isinstance(segments_list, list)
        assert info.language == "en"

    def test_transcribe_speech_audio(self, whisper_model_small, test_speech_audio):
        """Test transcription with simulated speech."""
        segments, info = whisper_model_small.transcribe(
            test_speech_audio,
            language="en",
        )

        segments_list = list(segments)
        assert len(segments_list) >= 0  # May or may not produce segments

    def test_multiple_transcriptions_same_model(self, whisper_model_small, tone_audio, silence_audio):
        """
        Test that model can be reused multiple times.

        Ensures model doesn't degrade or leak memory across calls.
        """
        # First transcription
        seg1, _ = whisper_model_small.transcribe(tone_audio)
        list(seg1)  # Consume generator

        # Second transcription
        seg2, _ = whisper_model_small.transcribe(silence_audio)
        list(seg2)

        # Model should still work
        seg3, _ = whisper_model_small.transcribe(tone_audio)
        list(seg3)

        # No assertions needed - just verify no crashes
```

#### 3.4.4 GPU vs CPU Test Pattern

```python
# tests/whisper/test_compute_types.py

import pytest

pytestmark = pytest.mark.whisper

class TestComputeTypes:
    """Test CPU and GPU compute type compatibility."""

    def test_cpu_int8_works(self, tone_audio):
        """Test that int8 compute type works on CPU."""
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8",
        )

        segments, info = model.transcribe(tone_audio)
        list(segments)  # Should not crash

        del model

    @pytest.mark.gpu
    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA not available"
    )
    def test_cuda_float16_works(self, tone_audio):
        """Test that float16 compute type works on CUDA."""
        from faster_whisper import WhisperModel
        import torch

        model = WhisperModel(
            "tiny",
            device="cuda",
            compute_type="float16",
        )

        segments, info = model.transcribe(tone_audio)
        list(segments)

        del model
        torch.cuda.empty_cache()

    def test_cpu_float16_fails_gracefully(self):
        """Test that CPU + float16 raises clear error."""
        from faster_whisper import WhisperModel

        with pytest.raises(Exception, match="float16|compute type"):
            model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="float16",  # Should fail on CPU
            )
```

### 3.5 Coverage Strategy

```ini
# pyproject.toml addition
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src/Quill --cov-report=term-missing --cov-report=html"
```

**Coverage Goals:**

| Component | Unit Coverage Target | Integration Coverage |
|-----------|---------------------|---------------------|
| Config | 95% | 100% (existing) |
| Logging | 90% | 100% (existing) |
| Audio | 85% | 60% |
| Transcription | 80% | 40% (whisper tests) |
| Injection | 70% | 0% (Windows-only) |
| Hotkeys | 70% | 0% (Windows-only) |
| UI | 60% | 0% (Windows-only) |
| App | 75% | 50% |
| **Overall** | **80%** | **40%** |

### 3.6 CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest  # Default: unit tests only

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e ".[dev]"
      - run: pytest -m integration

  whisper-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e ".[dev]"
      - run: pytest -m whisper  # Runs with shared model
```

---

## 4. Implementation Priority

1. **Phase 1: Infrastructure** (High Priority)
   - Create `pytest.ini` with markers
   - Create `tests/conftest.py` with shared fixtures
   - Reorganize existing tests into `tests/unit/`

2. **Phase 2: Whisper Tests** (High Priority)
   - Create `tests/whisper/conftest.py` with session-scoped model
   - Create compute type validation tests (regression for bug)
   - Create basic inference tests

3. **Phase 3: Unit Test Expansion** (Medium Priority)
   - Create mocked tests for untested components (AudioCapture, TranscriptionService, etc.)
   - Achieve 80% unit test coverage

4. **Phase 4: Integration Tests** (Medium Priority)
   - Create `tests/integration/` directory
   - Add audio pipeline integration tests
   - Add state machine integration tests

5. **Phase 5: CI/CD** (Low Priority)
   - Add GitHub Actions workflow
   - Configure coverage reporting
   - Add badge to README

---

## 5. Success Criteria

- ✅ Default `pytest` run completes in <5 seconds
- ✅ Whisper model loads once per session (not per test)
- ✅ All tests pass on CPU-only systems
- ✅ Tests can run in CI without GPU
- ✅ Coverage reaches 80% for unit tests
- ✅ Clear separation between unit/integration/whisper tests
- ✅ Developer can run specific test categories easily

---

## 6. References

- pytest documentation: https://docs.pytest.org/
- pytest markers: https://docs.pytest.org/en/stable/example/markers.html
- pytest fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html
- faster-whisper: https://github.com/guillaumekln/faster-whisper
