# Manual Tests for Quill

These tests verify that Quill components work with real hardware and models.
They are **not part of the regular pytest suite** and must be run explicitly.

## Prerequisites

1. **Windows environment** (PowerShell recommended, not WSL)
2. **Python virtual environment activated**
3. **Dependencies installed**: `pip install -e ".[dev]"`
4. **Microphone connected** (for Layer 3 tests)

## Quick Start

```powershell
# In PowerShell on Windows
cd D:\github\quill
.\.venvpwsh\Scripts\Activate.ps1  # or source .venv/bin/activate on Linux

# Run tests in order:
python tests/manual/test_layer1_whisper.py
python tests/manual/test_layer2_service.py
python tests/manual/test_layer3_microphone.py
```

## Test Layers

### Layer 1: Whisper Direct (`test_layer1_whisper.py`)

Tests the `faster-whisper` library directly without any Quill code.

**What it tests:**
- Can import faster-whisper
- Can load the tiny model (downloads on first run)
- Can transcribe synthetic audio
- Output has correct structure

**If this fails:** There's a problem with your Python environment or faster-whisper installation.

```bash
python tests/manual/test_layer1_whisper.py
```

### Layer 2: TranscriptionService (`test_layer2_service.py`)

Tests Quill's `TranscriptionService` wrapper around Whisper.

**What it tests:**
- Configuration loading works
- Service can be created
- Service.prepare() triggers model loading
- Service.transcribe() works
- Health check works

**If this fails:** There's a bug in Quill's service layer.

```bash
python tests/manual/test_layer2_service.py
```

### Layer 3: Microphone + Transcription (`test_layer3_microphone.py`)

**INTERACTIVE** - Tests real microphone recording and transcription.

**What it tests:**
- Audio devices are detected
- Microphone can record audio
- Recorded speech can be transcribed
- Full pipeline works end-to-end

**If this fails:** Check your microphone settings.

```bash
python tests/manual/test_layer3_microphone.py
```

## Running with pytest

You can also run these tests with pytest (useful for CI or more detailed output):

```bash
# Run all manual tests
pytest tests/manual/ -v -m manual --no-cov -s

# Run specific layer
pytest tests/manual/test_layer1_whisper.py -v -m manual --no-cov

# Note: -s is important for Layer 3 (interactive input)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'Quill'"

Make sure you installed Quill in development mode:
```bash
pip install -e ".[dev]"
```

### "CUDA not available, falling back to CPU"

This is fine for testing. The tests use CPU + int8 compute type which works everywhere.

### "No audio input devices found"

- Check your microphone is connected
- On Windows, check Sound Settings > Input
- Try a different USB port

### Layer 3 tests are slow

The first run downloads the Whisper model (~75MB for tiny). Subsequent runs are faster.

### Tests pass but transcription is empty

- Speak louder or closer to the microphone
- Check microphone isn't muted
- Try adjusting system microphone volume

## Config Notes

Layer 2 and 3 tests will automatically update `config.yaml` to use CPU-compatible settings:

```yaml
transcription:
  model_size: tiny
  device: cpu
  compute_type: int8
```

This ensures tests work on any machine. For production, you may want to use `small` model and `cuda` device.
