# Quill

Local speech-to-text dictation tool using OpenAI's Whisper AI.

## Features

- 🎤 **Local transcription** - No cloud, complete privacy
- ⌨️ **Global hotkeys** - Work in any application
- 🚀 **Smart model loading** - Background loading, auto-unload on idle
- 🎯 **Direct text injection** - Text appears at your cursor
- ⚙️ **Configurable** - Multiple models, custom settings

## Quick Start

### Requirements

- Python 3.10+
- Windows 10/11 (Linux/macOS support planned)
- Optional: NVIDIA GPU with CUDA for faster transcription

### Installation

**For WSL2/Linux (Development):**
```bash
# Clone repository
git clone <repository-url>
cd quill

# Create virtual environment (requires uv: https://docs.astral.sh/uv/)
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Copy example config
cp config.example.yaml config.yaml
```

**For Windows PowerShell (Running):**
```powershell
# Navigate to repository
cd quill

# Create virtual environment (requires uv: https://docs.astral.sh/uv/)
uv venv .venvpwsh
.venvpwsh\Scripts\Activate.ps1

# Install dependencies
uv pip install -e ".[dev]"

# Copy example config
copy config.example.yaml config.yaml
```

**Note:** Quill must run in native Windows (PowerShell/CMD), not WSL2, for hotkeys and text injection to work.

### Usage

**In PowerShell:**
```powershell
.venvpwsh\Scripts\Activate.ps1
python -m Quill
```

**In WSL2/Linux (won't work - for development only):**
```bash
source .venv/bin/activate
python -m Quill  # This will fail - Windows features not available
```

Press your hotkey (default: Ctrl+Shift+D) to start/stop recording. Speak your text. Text will be inserted at cursor position.

### Configuration

Edit `config.yaml` to customize:

- **Model size**: tiny, base, small (default), medium, large
- **Hotkeys**: Change recording hotkey
- **Audio**: Sample rate, noise gate, etc.
- **Model lifecycle**: When to load/unload models

## How It Works

1. **Press hotkey** - Start recording
2. **Speak** - Audio is captured from microphone
3. **Press hotkey again** - Stop recording
4. **Wait** - Whisper transcribes audio (1-3 seconds)
5. **Text appears** - Transcription inserted at cursor

## Dictation Service (Simple Mode)

A lightweight dictation service is available for quick use:

```powershell
.venvpwsh\Scripts\Activate.ps1
python -m Quill.dictation
```

Or use the startup script:
```powershell
.\start-quill.ps1
```

**Features:**
- Streaming mode: text appears as you speak (after natural pauses)
- Auto-stop: recording stops after 20s of silence
- GPU auto-detection: uses CUDA if available
- Configurable via `config.yaml` (see `dictation:` section)

**Streaming vs Batch:**
- `streaming_enabled: true` - transcribes chunks as you speak
- `streaming_enabled: false` - transcribes all audio when you stop

## Architecture

- **AudioCapture**: Records audio from microphone
- **TranscriptionService**: Manages Whisper model lifecycle
- **ModelManager**: Downloads and loads models
- **WindowsTextInjector**: Inserts text at cursor
- **HotkeyListener**: Detects global hotkeys

## Development

```bash
# Run tests
pytest

# Format code
black src/
ruff check src/ --fix

# Type check
mypy src/
```

## Stable Install (Tag & Deploy)

To use Quill daily while developing, set up a separate stable installation from a tagged release.

### Creating a Release

```powershell
# In your development repo
cd D:\github\quill

# Tag a working version
git tag v0.1.0 -m "First stable release"
git push origin v0.1.0  # optional, for backup
```

### Installing from a Tag

```powershell
# Clone to a separate directory
## Installing locally:
git clone D:\github\quill $HOME\quill-stable --branch v0.1.0

## Installing remotely:
git clone https://github.com/BrenanL/quill.git $HOME\quill-stable --branch v0.1.0

cd $HOME\quill-stable

# Set up venv and install (requires uv: https://docs.astral.sh/uv/)
uv venv .venvpwsh
.venvpwsh\Scripts\Activate.ps1
uv pip install -e . # using standard command breaks for some reason, be sure to use `-e`

# Configure
copy config.example.yaml config.yaml

# Run
.\start-quill.ps1
```

### Updating to a New Release

```powershell
cd $HOME\quill-stable
git fetch --tags
git checkout v0.1.1
.venvpwsh\Scripts\Activate.ps1
uv pip install .
```

## Troubleshooting

**"python -m Quill" opens dialog instead of running**
- You're trying to use WSL2 venv in Windows or vice versa
- Use `.venvpwsh` in PowerShell, `.venv` in WSL2
- Make sure you're in a PowerShell terminal, not File Explorer
- Recreate venv in native Windows if needed

**No microphone detected**
- Check microphone is connected and enabled
- Check Windows privacy settings allow microphone access

**CUDA not available**
- Install CUDA Toolkit 11.8+
- Or set `device: "cpu"` in config.yaml (slower but works)

**Hotkey not working**
- Check if another application uses the same hotkey
- Try a different hotkey combination
- Must run in native Windows (not WSL2)

**Slow transcription**
- Use smaller model (tiny, base) for faster transcription
- Enable GPU/CUDA for 5-10x speed improvement

## License

MIT

## Credits

- OpenAI Whisper
- faster-whisper by Guillaume Klein
