# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@docs/work-tracker.md

## Project Overview

**Quill** is a local, Windows-native dictation tool that uses OpenAI's Whisper (via Faster-Whisper) for high-quality speech-to-text transcription. The tool runs as a persistent background service with system tray integration and global hotkey activation.

**Key Features:**
- Local transcription (privacy-focused, no cloud)
- Tray-first UI design (inspired by g-helper)
- Global hotkey activation (toggle mode)
- Smart model lifecycle (lazy load, auto-unload on idle)
- Text injection into any Windows application
- Configurable model selection (tiny/base/small/medium/large)

## Development Environment

### Setup

```bash
# Repository location
cd /mnt/d/github/quill

# Virtual environment (REQUIRED - per user's global instructions)
source .venv/bin/activate  # Linux/WSL
# OR
.venv\Scripts\activate  # Windows

# Install dependencies (when pyproject.toml exists)
pip install uv
uv pip install -e ".[dev]"
# OR
pip install -e ".[dev]"

# Create directories
mkdir -p models logs src/Quill

# Run application
python -m Quill

# Run tests
pytest

# Format code
black src/
ruff check src/ --fix

# Type checking
mypy src/
```

### Directory Structure (Planned)

```
Quill/
├── src/Quill/          # Main package
│   ├── __main__.py           # Entry point
│   ├── app.py                # Main application orchestrator
│   ├── config/               # Configuration (Pydantic schemas, YAML loading)
│   ├── audio/                # Audio capture (sounddevice), preprocessing
│   ├── transcription/        # Whisper integration, model manager
│   │   ├── service.py        # TranscriptionService (prepare, transcribe)
│   │   ├── model_manager.py  # Model download, load, unload
│   │   └── faster_whisper.py # Faster-Whisper engine
│   ├── injection/            # Text injection (win32api)
│   ├── ui/                   # System tray (pystray), notifications
│   ├── hotkeys/              # Global hotkey listener (keyboard library)
│   └── utils/                # Logging, threading, errors
├── models/                   # Downloaded Whisper models (gitignored)
├── logs/                     # Application logs (gitignored)
├── config.yaml               # User configuration (gitignored)
├── config.example.yaml       # Example configuration
├── tests/                    # Test suite
└── docs/                     # Documentation and planning
```

## Architecture

### High-Level Components

1. **Tray UI Layer** (`ui/`) - System tray icon with state management (idle/recording/processing/success/error)
2. **Hotkey Service** (`hotkeys/`) - Global hotkey detection using `keyboard` library
3. **Audio Capture** (`audio/`) - Microphone recording via `sounddevice`, ring buffer, preprocessing
4. **Transcription Engine** (`transcription/`) - Faster-Whisper integration, model lifecycle management
5. **Text Injector** (`injection/`) - Windows text injection via `win32api`, clipboard fallback
6. **Configuration** (`config/`) - YAML config with Pydantic validation

### Threading Model

- **Main Thread (UI):** Tray icon event loop, hotkey callbacks, text injection (must be on main thread for Windows)
- **Audio Capture Thread:** Real-time `sounddevice` callback, minimal processing, queue population
- **Transcription Service Thread:** Always-running service that manages model lifecycle, provides prepare() and transcribe() methods
- **Model Loader Thread:** Spawned on-demand when prepare() called, loads model in background while user speaks
- **Idle Monitor Thread:** Track inactivity, unload model after timeout (default 5 min)

### Data Flow

```
User presses hotkey (start)
  → SIMULTANEOUSLY:
     A. Ping transcription service: prepare()
        - If DOWN: error, cancel recording
        - If UP: service starts loading model in background
     B. Start recording (tray icon → red, toast notification)
        - Audio capture thread buffers to queue
  → User speaks (5-10+ seconds)
     - Model loads in background (user doesn't notice)
  → User presses hotkey again (stop)
  → Stop recording, tray icon → yellow "processing"
  → Call transcription service: transcribe()
     - Model should be ready (or nearly ready)
     - Run inference, return text
  → Inject text at cursor (main thread)
  → Tray icon → green flash, then back to idle
```

## Key Design Decisions

### Model Lifecycle (Critical)
- **Service-based:** TranscriptionService runs always, manages model state
- **Lazy loading with prepare():** Model loads when prepare() called (on hotkey press), not at startup
- **Background loading:** Model loads in background while user speaks (5-10s), user doesn't notice wait
- **Persistent memory:** Model stays loaded for instant subsequent recordings
- **Idle timeout:** Auto-unload after 5 minutes of inactivity (configurable)
- **Progress feedback:** Show notifications during model download/loading

### Tray-First Design (inspired by g-helper)
- Application starts with **tray icon only** (no visible windows)
- Persistent background service for instant hotkey response
- Native OS notifications for state feedback
- No settings GUI in MVP (YAML config only)

### Platform Support
- **MVP:** Windows 10/11 x64 only
- **Deferred:** Linux (Wayland hotkey issues), macOS
- **Dependencies:** CUDA for GPU, CPU fallback supported

## Configuration

Configuration lives in `config.yaml` (YAML format) with Pydantic validation.

**Key settings:**
- `transcription.model_size`: "tiny" | "base" | "small" | "medium" | "large" (default: "small")
- `transcription.device`: "cuda" | "cpu" (auto-detected)
- `transcription.lifecycle.lazy_load`: true (load on first use)
- `transcription.lifecycle.unload_after_minutes`: 5 (0 = keep always, -1 = unload immediately)
- `hotkeys.toggle_recording`: "ctrl+shift+d" (configurable)
- `audio.sample_rate`: 16000 (required by Whisper)

## Core Dependencies

- **Audio:** `sounddevice`, `numpy`, `scipy`
- **Transcription:** `faster-whisper`, `torch`
- **UI:** `pystray`, `Pillow`
- **Hotkeys:** `keyboard`
- **Text Injection:** `pywin32` (Windows-specific)
- **Config:** `pydantic`, `ruamel.yaml`
- **Logging:** `loguru`

## Testing Strategy

- **Unit tests:** Config validation, audio preprocessing, text injection logic
- **Integration tests:** Full pipeline (hotkey → audio → transcription → injection), model lifecycle
- **Manual testing:** Different microphones, GPU/CPU modes, various applications, edge cases

**Coverage targets:** >80% overall, 100% for config validation

## Implementation Status

**Current Phase:** Foundation (Phase 1)
- Project structure setup
- Configuration system
- Logging infrastructure

**Planned Phases (5-week MVP timeline):**
1. Foundation + Audio Capture (Week 1)
2. Transcription Engine (Week 2)
3. Text Injection (Week 2-3)
4. Tray UI + Hotkeys (Week 3)
5. Integration (Week 4)
6. Testing & Debugging (Week 4-5)
7. Documentation & Polish (Week 5)

## Performance Targets

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Hotkey response | <50ms | 100ms |
| Model loading (small, GPU) | <3s | 5s |
| Transcription (5s audio, small, GPU) | <1s | 3s |
| Text injection (50 chars) | <100ms | 500ms |

## Common Development Patterns

### Error Handling
All components use custom exceptions from `utils/errors.py`:
- `QuillError` (base)
- `AudioCaptureError`, `TranscriptionError`, `InjectionError`, `ConfigError`

Log errors with `logger.error(exc_info=True)` and implement graceful fallbacks (e.g., clipboard injection if keyboard fails).

### State Management
Main app uses state machine: `idle → recording → processing → success/error → idle`

Tray icon updates reflect current state with visual feedback.

### Thread Safety
- Audio queue: thread-safe `queue.Queue`
- Text injection: must post to main thread (Windows requirement)
- Model operations: synchronized via locks in ModelManager

## Known Issues & Constraints

- **Windows-only in MVP:** Linux support deferred due to Wayland global hotkey complications
- **No settings GUI:** MVP uses YAML config editing only
- **Toggle mode only:** Push-to-talk deferred to post-MVP
- **English only:** Multi-language support deferred
- **No streaming:** Batch transcription only (entire recording processed at once)

## Development Notes

- Follow user's global instructions: always use `.venv`, avoid `git commit` without explicit instruction
- use `uv` for python packages
- Code formatting: use `black` and `ruff`
- Type hints: use `mypy` for validation
- Commit style: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- Git branches: `main` (stable), `develop` (integration), `feature/*`, `bugfix/*`
- When asked to take note of an issue, append it to `docs/issues.md`
- Always check `docs/work-tracker.md` before beginning any work. Update work items as you complete them. 

## Documentation References

- Overview: `docs/initial-plan/overview.md`
- MVP Implementation Plan: `docs/initial-plan/mvp-implementation-plan.md`
- Issues Log: `docs/issues.md`
