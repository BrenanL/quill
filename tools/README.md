# Quill Development Tools

Utility scripts for development, testing, and debugging.

---

## Scripts

### 1. `check_whisper_processes.py`

Check for running Whisper/pytest processes and optionally terminate them.

**Usage:**

```bash
# Interactive check (prompts before killing)
python tools/check_whisper_processes.py

# Auto-kill with SIGTERM
python tools/check_whisper_processes.py --kill

# Force kill with SIGKILL
python tools/check_whisper_processes.py --force
```

**What it detects:**
- pytest processes running whisper tests
- Python processes with whisper/faster-whisper imported
- Python processes using GPU memory (via nvidia-smi)
- Running Quill application

**Output includes:**
- PID (process ID)
- Command line
- CPU usage (%)
- RAM usage (MB)
- VRAM usage (MB, if applicable)
- Process status

**Example output:**
```
Found 2 Whisper-related process(es):

[1] PID: 12345 | CPU: 85.3% | RAM: 2048 MB | VRAM: 1536 MB | Status: R
    Command: python -m pytest tests/whisper/test_whisper_inference.py

[2] PID: 12346 | CPU: 12.1% | RAM: 512 MB | Status: S
    Command: python -m Quill

Total: 2560 MB RAM, 1536 MB VRAM

Kill these processes? (y/n):
```

**Use cases:**
- Clean up hung pytest sessions
- Free VRAM after testing
- Verify all Whisper processes terminated
- Debug process leaks

**Features:**
- Automatically excludes itself from detection
- Offers to clear GPU cache after killing processes
- Handles permission errors gracefully
- Supports both interactive and automated modes

---

### 2. `check_memory_usage.py`

Check if Whisper models are loaded in memory (VRAM or RAM).

**Usage:**

```bash
# Check current memory usage
python tools/check_memory_usage.py

# Clear CUDA cache and garbage collect
python tools/check_memory_usage.py --clear-cache
```

**What it checks:**
- CUDA GPU memory (allocated and reserved)
- System RAM usage
- Active GPU processes
- PyTorch cache status

**Example output:**
```
CUDA Memory:
  Allocated: 0.23 GB
  Reserved:  0.50 GB

System Memory:
  Total:     15.85 GB
  Used:      8.42 GB (53.1%)
  Available: 7.43 GB

GPU Processes: None
```

**Use cases:**
- Verify Whisper model is unloaded after tests
- Check if GPU memory leak exists
- Debug VRAM issues
- Force cleanup of cached allocations

---

### 3. `record_audio.py`

Record audio from your microphone and save to a WAV file.

**Usage:**

```bash
# Basic usage (5 seconds, 16kHz)
python tools/record_audio.py output.wav

# Record for 10 seconds
python tools/record_audio.py output.wav --duration 10

# Custom sample rate (44.1kHz)
python tools/record_audio.py output.wav --sample-rate 44100

# Save to subdirectory
python tools/record_audio.py recordings/test_01.wav
```

**Parameters:**
- `output` - Output WAV file path (required)
- `--duration, -d` - Recording duration in seconds (default: 5)
- `--sample-rate, -sr` - Sample rate in Hz (default: 16000)

**Recommended settings for Whisper:**
- Sample rate: **16000 Hz** (Whisper's native rate)
- Duration: **5-10 seconds** (good for testing)
- Format: **WAV** (lossless, compatible)

**Example workflow:**

```bash
# 1. Record test audio
python tools/record_audio.py test.wav --duration 10

# 2. Transcribe with Whisper
python -c "
from faster_whisper import WhisperModel
import soundfile as sf

# Load audio
audio, sr = sf.read('test.wav')

# Load model and transcribe
model = WhisperModel('small', device='cpu', compute_type='int8')
segments, info = model.transcribe(audio, language='en')

# Print results
for seg in segments:
    print(f'[{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}')
"
```

---

## Common Workflows

### Test Whisper Accuracy

```bash
# 1. Record yourself saying a known phrase
python tools/record_audio.py test_phrase.wav
# Say: "The quick brown fox jumps over the lazy dog"

# 2. Transcribe and check accuracy
# (Use the transcription script from test examples)
```

### Debug Memory Issues

```bash
# 1. Check initial memory
python tools/check_memory_usage.py

# 2. Run tests
pytest -m whisper

# 3. Check if processes are still running
python tools/check_whisper_processes.py

# 4. Check if model is still loaded in memory
python tools/check_memory_usage.py

# 5. Force cleanup if needed
python tools/check_whisper_processes.py --kill
python tools/check_memory_usage.py --clear-cache
```

### Create Test Dataset

```bash
# Create multiple test recordings
python tools/record_audio.py test_recordings/sample_01.wav
python tools/record_audio.py test_recordings/sample_02.wav
python tools/record_audio.py test_recordings/sample_03.wav

# Then use in tests
# (See tests/audio_samples/README.md for testing with real audio)
```

---

## Requirements

These scripts require packages from the main project:

```bash
# Activate virtual environment
source .venv/bin/activate

# Requirements already installed with project:
- sounddevice  # For recording
- numpy        # For audio arrays
- scipy        # For WAV file I/O
- torch        # For CUDA memory checks

# Optional (for enhanced features):
pip install psutil  # For system memory info
```

---

## Tips

### Recording Tips
- Use a quiet environment
- Speak clearly and at normal volume
- Position microphone 6-12 inches from mouth
- Test with `--duration 3` first to check levels
- Default 16kHz is optimal for Whisper (don't change unless needed)

### Memory Management
- Session-scoped pytest fixtures automatically cleanup
- Use `--clear-cache` if VRAM stays high after tests
- WSL2 may show higher VRAM usage due to driver overhead
- Check `nvidia-smi` directly for accurate GPU usage

### Troubleshooting

**"sounddevice not installed"**
```bash
pip install sounddevice
```

**"No audio device found"**
```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

**"CUDA not available"**
- Models will run on CPU (slower but works)
- Check PyTorch installation: `python -c "import torch; print(torch.cuda.is_available())"`

---

## See Also

- `tests/audio_samples/` - Test audio fixtures and examples
- `tests/whisper/` - Whisper model tests
- `docs/test-system-spec.md` - Testing system specification
