# Quill Test System

This directory contains the comprehensive test suite for Quill, organized into three tiers: unit, integration, and whisper tests.

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/                    # Fast unit tests with mocks (<5 seconds total)
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_logging.py
│   ├── test_audio.py
│   ├── test_audio_capture_mock.py
│   ├── test_transcription_service_mock.py
│   ├── test_model_manager_mock.py
│   ├── test_text_injector_mock.py
│   ├── test_hotkeys_mock.py
│   ├── test_notifications_mock.py
│   └── test_app_mock.py
├── integration/             # Integration tests (slower, real components)
│   ├── conftest.py
│   └── test_audio_pipeline.py
└── whisper/                 # Real Whisper model tests (very slow)
    ├── conftest.py          # Session-scoped model fixtures
    ├── test_whisper_inference.py
    └── test_compute_types.py
```

## Test Categories

### Unit Tests (Fast, Mocked)
- **Marker:** `@pytest.mark.unit`
- **Speed:** <5 seconds total
- **Purpose:** Test individual components with all external dependencies mocked
- **Hardware:** No special requirements (CPU only, no GPU, no microphone)
- **Model Download:** Not required

### Integration Tests (Moderate Speed)
- **Marker:** `@pytest.mark.integration`
- **Speed:** <30 seconds
- **Purpose:** Test component interactions with real (non-mocked) implementations
- **Hardware:** No special requirements
- **Model Download:** Not required

### Whisper Tests (Slow, Real Models)
- **Marker:** `@pytest.mark.whisper`
- **Speed:** 2-10 minutes (first run with download), <2 minutes (cached)
- **Purpose:** Test real Whisper model loading and inference
- **Hardware:** CPU sufficient, GPU optional
- **Model Download:** Required (~500MB for small model)

## Running Tests

### Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/WSL
# OR
.venv\Scripts\activate  # Windows

# Install test dependencies (if not already installed)
pip install -e ".[dev]"
```

### Quick Start (Unit Tests Only)

Default behavior runs only fast unit tests:

```bash
pytest
```

This will:
- Run all unit tests with mocks
- Complete in <5 seconds
- NOT download any models
- NOT require GPU or microphone

### Run Specific Test Categories

```bash
# Unit tests only (fast, default)
pytest

# Integration tests only
pytest -m integration

# Whisper tests only (downloads models on first run)
pytest -m whisper

# Everything (unit + integration + whisper)
pytest -m "unit or integration or whisper"

# Skip slow tests
pytest -m "not slow"

# GPU tests only (requires CUDA)
pytest -m gpu
```

### Run Specific Test Files

```bash
# Run a specific test file
pytest tests/unit/test_config.py

# Run a specific test class
pytest tests/unit/test_config.py::TestConfigSchema

# Run a specific test
pytest tests/unit/test_config.py::TestConfigSchema::test_default_config
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src/Quill --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Verbose Output

```bash
# Show detailed output
pytest -v

# Show print statements
pytest -s

# Show both
pytest -vs
```

## Whisper Model Tests

### First-Time Setup

The first time you run whisper tests, models will be downloaded:

```bash
pytest -m whisper
```

This will:
1. Download the "tiny" and "small" Whisper models (~500MB total)
2. Store them in `models/` directory
3. Run all whisper tests with the shared model instance

**Expected time:**
- First run: 5-10 minutes (includes download)
- Subsequent runs: 1-2 minutes (uses cached models)

### Important: Session-Scoped Models

Whisper tests use **session-scoped fixtures** to avoid reloading models:
- The model is loaded ONCE at the start of the test session
- All whisper tests share the same model instance
- Model is unloaded when all tests complete

This design saves significant time and memory.

### Running Whisper Tests Manually

```bash
# Run all whisper tests
pytest -m whisper -v

# Run specific whisper test file
pytest tests/whisper/test_whisper_inference.py -v

# Run with GPU (if available)
pytest -m "whisper and gpu" -v
```

### GPU Tests

GPU-specific tests are marked with `@pytest.mark.gpu` and skipped by default. To run them:

```bash
# Run GPU tests only
pytest -m gpu

# Run all whisper tests including GPU
pytest -m whisper
```

GPU tests will automatically skip if CUDA is not available.

## Test Performance Targets

| Test Category | Target Time | Max Acceptable |
|--------------|-------------|----------------|
| Unit tests (all) | <5s | 10s |
| Integration tests | <30s | 60s |
| Whisper tests (cached) | <2min | 5min |
| Whisper tests (first run) | <10min | 15min |

## Writing New Tests

### Unit Test Template

```python
# tests/unit/test_my_component_mock.py
"""
Unit tests for MyComponent with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, patch

from Quill.my_module.my_component import MyComponent

pytestmark = pytest.mark.unit


class TestMyComponentMocked:
    """Unit tests for MyComponent using mocks."""

    def test_something(self, mock_config):
        """Test description."""
        # Arrange
        component = MyComponent(mock_config)

        # Act
        result = component.do_something()

        # Assert
        assert result == expected_value
```

### Integration Test Template

```python
# tests/integration/test_my_integration.py
"""
Integration tests for component interactions.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestMyIntegration:
    """Integration tests using real components."""

    def test_something(self):
        """Test description."""
        # Test with real (non-mocked) components
        pass
```

### Whisper Test Template

```python
# tests/whisper/test_my_whisper_feature.py
"""
Tests with real Whisper model.
"""

import pytest

pytestmark = [pytest.mark.whisper, pytest.mark.slow]


class TestMyWhisperFeature:
    """Tests using real Whisper model."""

    def test_something(self, whisper_model_small, test_audio_sample):
        """Test description."""
        # Use shared model fixture
        segments, info = whisper_model_small.transcribe(test_audio_sample)
        # ... assertions
```

## Continuous Integration

For CI/CD pipelines, use:

```yaml
# .github/workflows/test.yml
- name: Run Unit Tests
  run: pytest  # Default: unit tests only, fast

- name: Run Integration Tests
  run: pytest -m integration

- name: Run Whisper Tests (Optional)
  run: pytest -m whisper
  # Only on specific branches or manual trigger
```

## Troubleshooting

### Tests can't find Quill module

```bash
# Install in editable mode
pip install -e .
```

### Whisper tests downloading every time

Models should be cached in `models/` directory. If they download repeatedly:
- Check that `models/` directory exists and is writable
- Check disk space (models are ~500MB)

### GPU tests failing

GPU tests require:
- NVIDIA GPU with CUDA support
- CUDA toolkit installed
- `torch` with CUDA support

If you don't have a GPU, these tests will skip automatically.

### Tests are slow

- Make sure you're running unit tests only (default): `pytest`
- Integration and whisper tests are slow by design
- Use `-n auto` for parallel execution (requires `pytest-xdist`)

## Coverage Goals

| Component | Unit Coverage Target | Integration Coverage |
|-----------|---------------------|---------------------|
| Config | 95% | 100% |
| Logging | 90% | 100% |
| Audio | 85% | 60% |
| Transcription | 80% | 40% |
| Injection | 70% | 0% (Windows-only) |
| Hotkeys | 70% | 0% (Windows-only) |
| UI | 60% | 0% (Windows-only) |
| App | 75% | 50% |
| **Overall** | **80%** | **40%** |

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
