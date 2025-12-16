# Quill Developer Troubleshooting Guide

This guide covers common development issues and how to resolve them.

---

## Process Management

### Problem: Can't Stop Quill with Ctrl+C

**Why:** Quill runs as a background service with hotkey listeners and a system tray icon. These components block normal Ctrl+C (SIGINT) termination.

**Solutions:**

#### Method 1: Emergency Stop Hotkey
Press **Ctrl+Shift+Esc** (configurable in `config.yaml`)

**Note:** Currently broken (infinite loop bug), use Method 2 or 3 instead.

#### Method 2: PowerShell Commands (Windows)

**Find Quill processes:**
```powershell
# Find by path pattern
Get-Process python | Where-Object {$_.Path -like '*quill*'}

# Find by venv path
Get-Process python | Where-Object {$_.Path -like '*venvpwsh*' -or $_.Path -like '*\.venv*'}

# Show detailed info (includes PID, path, start time)
Get-Process python | Select-Object Id, ProcessName, Path, StartTime
```

**Kill Quill processes:**
```powershell
# Kill by path filter (recommended)
Get-Process python | Where-Object {$_.Path -like '*quill*'} | Stop-Process -Force

# Kill by venv path
Get-Process python | Where-Object {$_.Path -like '*venvpwsh*'} | Stop-Process -Force

# Kill specific process by ID
Stop-Process -Id <PID> -Force

# Nuclear option - kill ALL Python processes (be careful!)
Get-Process python | Stop-Process -Force
```

#### Method 3: Linux/WSL Commands

**Find Quill processes:**
```bash
# Find by command line pattern
ps aux | grep -i quill

# Find by working directory
ps aux | grep -E 'python.*quill|quill.*python'

# Show tree view (useful for finding child processes)
pstree -p | grep -i python
```

**Kill Quill processes:**
```bash
# Kill by PID (replace <PID> with actual process ID from ps)
kill -9 <PID>

# Kill by name pattern
pkill -9 -f "python.*quill"

# Kill all Python processes (be careful!)
pkill -9 python
```

#### Method 4: Task Manager (Windows)
1. Open Task Manager (Ctrl+Shift+Esc)
2. Find "Python" processes
3. Check "Command line" column to identify Quill
4. Right-click → End Task

#### Method 5: System Tray Icon
Right-click Quill's tray icon → Exit (may not work if app is frozen)

---

## CUDA/GPU Issues

### Problem: "CUDA not available, falling back to CPU"

**Symptoms:**
```
WARNING:root:CUDA not available, falling back to CPU
```

**Possible Causes:**

1. **PyTorch not installed in current venv**
   ```bash
   # Check if torch is installed
   python -c "import torch"

   # If missing, install with CUDA support
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

2. **Wrong PyTorch version (CPU-only)**
   ```bash
   # Check CUDA availability
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

   # Should print: CUDA available: True
   # If False, reinstall with CUDA support (see above)
   ```

3. **NVIDIA drivers not installed**
   ```bash
   # Windows: Check Device Manager for GPU
   # Linux: Check nvidia-smi
   nvidia-smi
   ```

4. **Multiple venvs with different installations**
   - `.venv` (WSL/Linux) vs `.venvpwsh` (PowerShell)
   - Make sure PyTorch is installed in BOTH if using both

### Problem: "Failed to load model: float16 compute type not supported"

**Why:** CPU fallback still tries to use `float16`, which CPUs don't support efficiently.

**Symptoms:**
```
ERROR | Failed to load model small: Requested float16 compute type, but the target device or backend do not support efficient float16 computation.
```

**Current Workaround:** Use GPU (install PyTorch with CUDA)

**Permanent Fix:** Bug in `model_manager.py` - needs to auto-adjust `compute_type` to `int8` when `device="cpu"`. See issues.md for details.

---

## Virtual Environment Management

### Problem: Two venvs (.venv and .venvpwsh) out of sync

**Why:** WSL uses `.venv`, PowerShell uses `.venvpwsh`, they need separate installations.

**Solution:** Install dependencies in both

**Using uv (recommended):**
```bash
# WSL/Linux
cd /mnt/d/github/quill
source .venv/bin/activate
uv pip install -e ".[dev]"

# PowerShell
cd D:\github\quill
.venvpwsh\Scripts\Activate.ps1
uv pip install -e ".[dev]"
```

**Using pip:**
```bash
# WSL/Linux
cd /mnt/d/github/quill
source .venv/bin/activate
pip install -e ".[dev]"

# PowerShell
cd D:\github\quill
.venvpwsh\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Problem: Which venv am I using?

**Check active venv:**
```bash
# Look at shell prompt (should show venv name)
# Or check Python path
which python  # Linux/WSL
(Get-Command python).Path  # PowerShell
```

**Expected paths:**
- WSL: `/mnt/d/github/quill/.venv/bin/python`
- PowerShell: `D:\github\quill\.venvpwsh\Scripts\python.exe`

### Problem: pytest uses system Python instead of venv

**Symptoms:**
- `which python` shows venv path
- `which pytest` shows `/home/user/.local/bin/pytest` or system path
- Tests fail with `ModuleNotFoundError: No module named 'Quill'`

**Why:** Venv not properly activated, PATH doesn't include venv's `bin` directory.

**Solution (WSL):**
```bash
# Use absolute path to activate (not relative)
source /mnt/d/github/quill/.venv/bin/activate

# Verify pytest is from venv
which pytest  # Should show /mnt/d/github/quill/.venv/bin/pytest

# Run tests
pytest tests/unit/test_config.py -v
```

**Workaround:** Always use `python -m pytest` instead of `pytest` directly:
```bash
python -m pytest tests/unit/test_config.py -v
```

---

## Configuration Issues

### Problem: Config validation errors on startup

**Symptoms:**
```
ERROR | ConfigError: Invalid configuration: ...
```

**Common Causes:**
1. **Invalid YAML syntax**
   - Use a YAML validator or IDE with YAML support
   - Check for proper indentation (spaces, not tabs)
   - Check for unquoted special characters

2. **Invalid values**
   - Model size must be: tiny, base, small, medium, large
   - Device must be: cuda, cpu
   - Hotkeys must have format: modifier+key (e.g., "ctrl+shift+d")

3. **Missing config.yaml**
   - Copy `config.example.yaml` to `config.yaml`
   - Edit with your preferences

**Debug config loading:**
```python
# Test config manually
python -c "
from Quill.config.manager import ConfigManager
config = ConfigManager.load_with_defaults('config.yaml')
print(config)
"
```

---

## Audio Issues

### Problem: "No audio input device found"

**Symptoms:**
```
ERROR | AudioCaptureError: No audio input device found
```

**Solutions:**
1. Check microphone is connected and enabled
2. Test microphone in Windows Sound Settings
3. List available devices:
   ```python
   python -c "
   import sounddevice as sd
   print(sd.query_devices())
   "
   ```

### Problem: Audio capture fails or sounds distorted

**Possible Causes:**
1. **Wrong sample rate** - Quill expects 16kHz (configured in config.yaml)
2. **Buffer overflow** - Recording too long or system too slow
3. **Microphone permissions** - Windows may block access

**Debug audio capture:**
```python
# Test recording manually
python -c "
import sounddevice as sd
import numpy as np

duration = 3  # seconds
sr = 16000
print(f'Recording for {duration}s...')
audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='float32')
sd.wait()
print(f'Recorded {len(audio)} samples')
print(f'Peak amplitude: {np.max(np.abs(audio)):.3f}')
"
```

---

## Model Loading Issues

### Problem: Model download fails

**Symptoms:**
```
ERROR | ModelError: Failed to download model small: ...
```

**Solutions:**
1. **Check internet connection**
2. **Check disk space** - Models require:
   - tiny: ~75MB
   - base: ~145MB
   - small: ~465MB
   - medium: ~1.5GB
   - large: ~2.9GB
3. **Clear partial downloads:**
   ```bash
   rm -rf models/whisper-*
   # Or on Windows:
   Remove-Item -Recurse -Force models\whisper-*
   ```
4. **Manual download** - faster-whisper auto-downloads on first use

### Problem: Model loading takes too long

**Expected times (on SSD with good internet):**
- First time: 30s-5min (downloading)
- Subsequent: 1-5s (loading from disk)

**If slower:**
1. Check disk speed (HDD vs SSD)
2. Check available RAM/VRAM
3. Try smaller model first (tiny/base)

---

## Hotkey Issues

### Problem: Hotkeys not working

**Possible Causes:**
1. **Conflicting hotkey** - Another app using same combination
2. **Permission issues** - Windows may require elevation
3. **Keyboard library issues** - Try running as administrator

**Test hotkeys:**
```python
# Test keyboard library
python -c "
import keyboard
print('Press ctrl+shift+d...')
keyboard.wait('ctrl+shift+d')
print('Hotkey detected!')
"
```

### Problem: Hotkey triggers in wrong application

**Why:** Global hotkeys work system-wide, not just in Quill

**Solution:** Choose a unique hotkey combination that doesn't conflict with other apps

---

## Text Injection Issues

### Problem: Text not appearing in target application

**Possible Causes:**
1. **Target app doesn't accept keyboard input** - Some apps block programmatic input
2. **Focus lost** - Click in target app before pressing hotkey
3. **Permissions** - Some apps (elevated) require Quill to run as admin
4. **Clipboard fallback** - Set `text_injection.method: "clipboard"` in config

**Test injection:**
1. Open Notepad
2. Click in text area
3. Trigger Quill recording
4. Speak
5. Check if text appears

---

## Logging and Debugging

### Enable debug logging

Edit `config.yaml`:
```yaml
app:
  log_level: debug  # Change from "info"
```

### View logs

```bash
# Tail logs in real-time
tail -f logs/Quill.log  # Linux/WSL

# PowerShell
Get-Content -Path logs\Quill.log -Wait -Tail 50
```

### Common log messages

**Normal operation:**
```
INFO | Quill started successfully
INFO | Starting recording...
INFO | Model loaded successfully
INFO | Transcription complete
```

**Warnings (usually okay):**
```
WARNING | CUDA not available, falling back to CPU
WARNING | win10toast not available, notifications disabled
```

**Errors (need attention):**
```
ERROR | Model load failed
ERROR | AudioCaptureError
ERROR | TranscriptionError
```

---

## Testing

### Run test suite

```bash
# Activate venv
source .venv/bin/activate  # Linux/WSL
.venvpwsh\Scripts\Activate.ps1  # PowerShell

# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_config.py

# Run with coverage
pytest --cov=src/Quill --cov-report=html
```

### Quick integration test

```bash
# Test full pipeline (requires microphone)
python -m Quill

# In another terminal, check logs
tail -f logs/Quill.log
```

---

## Performance Profiling

### Check transcription speed

```python
# Time a transcription
import time
import numpy as np
from Quill.transcription.service import TranscriptionService
from Quill.config.manager import ConfigManager

config = ConfigManager.load_with_defaults('config.yaml')
service = TranscriptionService(config)

# Prepare model
service.prepare()
time.sleep(5)  # Wait for model to load

# Generate 5s of test audio
audio = np.random.randn(16000 * 5).astype('float32')

# Time transcription
start = time.time()
text = service.transcribe(audio)
elapsed = time.time() - start

print(f"Transcribed in {elapsed:.2f}s")
print(f"Text: {text}")
```

### Expected performance

| Model | Device | 5s Audio | Target |
|-------|--------|----------|--------|
| tiny  | GPU    | ~0.3s    | <1s    |
| small | GPU    | ~1s      | <3s    |
| small | CPU    | ~3s      | <5s    |

---

## Common Development Workflows

### Start Quill for testing

```bash
# Activate venv
source .venv/bin/activate

# Run in foreground (see logs)
python -m Quill

# Stop: See "Process Management" section above
```

### Make code changes

```bash
# 1. Stop Quill (if running)
# 2. Edit code
# 3. Format and check
black src/
ruff check src/ --fix
mypy src/

# 4. Run tests
pytest

# 5. Restart Quill
python -m Quill
```

### Sync dependencies after pyproject.toml changes

```bash
# Using uv (fast)
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

---

## Getting Help

If you encounter an issue not covered here:

1. **Check logs:** `logs/Quill.log` often has detailed error info
2. **Check issues.md:** Known issues and planned fixes
3. **Enable debug logging:** Set `log_level: debug` in config
4. **Search code:** `grep -r "error message" src/`
5. **File an issue:** Document steps to reproduce

---

**Last Updated:** 2025-11-14
