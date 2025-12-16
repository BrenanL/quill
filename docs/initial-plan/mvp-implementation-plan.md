# Quill MVP: Implementation Plan

## Document Overview

This document contains the complete specification and implementation plan for Quill MVP (v0.1). It is divided into two parts:

1. **MVP Specification** - What we're building
2. **Implementation Plan** - How we'll build it

---

# Part 1: MVP Specification

## 1.1 Product Overview

**Quill MVP** is a Windows-native dictation tool that uses local Whisper AI for high-quality speech-to-text transcription. It runs as a persistent background service with system tray integration and hotkey activation.

**Target User:** Developer (single user) on Windows with GPU
**Primary Use Case:** Dictating code comments, documentation, and text while maintaining privacy
**Core Value:** Local, private, high-quality transcription with instant availability

---

## 1.2 Scope

### ✅ In Scope for MVP

**Core Functionality:**
1. System tray icon with state indicators (idle/recording/processing/success/error)
2. Global hotkey activation (toggle mode only)
3. Audio capture from default microphone
4. Local Whisper transcription (Faster-Whisper backend)
5. Text injection into active Windows application
6. Configurable model selection (tiny/base/small/medium/large)
7. Model auto-download on first use
8. Smart model lifecycle (load on use, unload after idle timeout)
9. Native Windows toast notifications for recording state
10. YAML-based configuration with validation
11. Comprehensive logging for debugging
12. Basic error handling and recovery

**Platform Support:**
- Windows 10/11 x64 only
- GPU support (CUDA) with CPU fallback
- Python 3.11+ runtime environment

**User Interface:**
- System tray icon (pystray)
- Right-click context menu for basic controls
- Native toast notifications for feedback
- No settings GUI (YAML config file only)

### ❌ Out of Scope for MVP

**Deferred to Future Versions:**
1. Linux support (Wayland issues)
2. macOS support
3. Settings UI window (tkinter or web)
4. First-run wizard/onboarding
5. Push-to-talk mode (toggle only for MVP)
6. Voice commands ("new line", "delete word")
7. Streaming/real-time transcription (batch only)
8. API backend (OpenAI API, custom endpoints)
9. Custom overlay recording indicator
10. Processing pipeline plugins (just basic noise reduction)
11. Multi-language support (English only)
12. Auto-update mechanism
13. Telemetry/analytics
14. Installer (manual installation for dev)
15. PyInstaller packaging (run from source in dev)

---

## 1.3 Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Quill MVP                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌───────────────┐    ┌─────────────┐ │
│  │ Tray Icon    │───→│ Hotkey        │───→│ Audio       │ │
│  │ (pystray)    │    │ Listener      │ ┌─→│ Capture     │ │
│  │              │    │ (keyboard)    │ │  │ (sounddev.) │ │
│  └──────────────┘    └───────┬───────┘ │  └──────┬──────┘ │
│         │                    │         │         │        │
│         │                    │ prepare()        ↓        │
│         │                    ↓         │  ┌──────────────┐│
│         │         ┌─────────────────┐  │  │ Audio Queue  ││
│         │         │ Transcription   │  │  │ (ring buffer)││
│         │         │ Service         │←─┘  └──────┬───────┘│
│         │         │ (always-running)│            │        │
│         │         └────────┬────────┘            │        │
│         │                  │                     │        │
│         │                  │ transcribe()        │        │
│         │                  │←────────────────────┘        │
│         │                  ↓                              │
│         │         ┌──────────────────┐                    │
│         │         │ Model Manager    │                    │
│         │         │ (load/unload)    │                    │
│         │         └──────────────────┘                    │
│         │                                                 │
│         │                  ↓ text result                  │
│         │       ┌────────────────────┐                    │
│         └──────→│ Text Injector      │                    │
│                 │ (win32api)         │                    │
│                 └────────────────────┘                    │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Configuration Manager (YAML + Pydantic validation)   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Logging System (structured logs to file)             │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Threading Model

```
Main Thread (UI):
├─ Tray icon event loop (pystray)
├─ Hotkey handler callbacks
└─ Text injection (must be on main thread for Windows)

Audio Capture Thread:
├─ sounddevice callback (real-time)
├─ Minimal processing (append to queue)
└─ MUST NOT BLOCK (or audio drops)

Transcription Service Thread (always-running):
├─ Health check endpoint
├─ prepare() - triggers background model loading
├─ transcribe() - runs Whisper inference (blocking, 0.5-5s)
└─ Manages model lifecycle

Model Loader Thread (spawned on-demand):
├─ Loads model in background when prepare() called
├─ Updates service state (idle → loading → ready)
└─ Allows user to speak while model warms up

Idle Monitor Thread:
├─ Track time since last transcription
├─ Unload model after timeout (default 5 min)
└─ Log resource usage
```

### Data Flow

```
1. User presses hotkey (start recording)
   ↓
2. SIMULTANEOUSLY (parallel operations):
   ┌─────────────────────────┬─────────────────────────┐
   │ A. Prepare Transcription│ B. Start Recording      │
   │                         │                         │
   │ - Ping service:         │ - Tray icon → red       │
   │   prepare()             │ - Notification:         │
   │                         │   "🔴 Recording..."     │
   │ - If DOWN: error,       │ - Audio capture starts  │
   │   cancel recording      │   buffering to queue    │
   │                         │                         │
   │ - If UP:                │                         │
   │   Service checks model  │                         │
   │   status:               │                         │
   │   • Already loaded      │                         │
   │     → returns "ready"   │                         │
   │   • Not loaded          │                         │
   │     → spawns loader     │                         │
   │       thread            │                         │
   │     → returns "loading" │                         │
   └─────────────────────────┴─────────────────────────┘
   ↓
3. User speaks for 5-10+ seconds
   - During this time: model loads in background (if needed)
   - User doesn't notice the wait
   - Audio continuously buffered
   ↓
4. User presses hotkey again (stop recording)
   ↓
5. Recording stops, audio queue is finalized
   ↓
6. Tray icon updates to "processing" (yellow)
   ↓
7. Toast notification: "⚙️ Processing..."
   ↓
8. Call transcription service: transcribe(audio_data)
   - If model still loading: brief wait (much shorter now)
   - Service runs Whisper inference
   - Returns text result
   ↓
9. Main thread receives text
   ↓
10. Inject text at cursor position (win32api)
   ↓
11. Tray icon flashes "success" (green), then back to idle (gray)
   ↓
12. Toast notification: "✅ Text inserted"
   ↓
13. Update last-used timestamp (for idle timeout tracking)
```

---

## 1.4 Configuration Specification

### config.yaml Structure

```yaml
# Quill Configuration File
# Edit values below to customize behavior

# Application Settings
app:
  # Auto-start service when Windows logs in
  auto_start: false

  # Log level: debug, info, warning, error
  log_level: "info"

  # Log file location (relative to app directory)
  log_file: "logs/Quill.log"

  # Maximum log file size before rotation (MB)
  log_max_size_mb: 10

# Transcription Settings
transcription:
  # Backend: "faster-whisper" (only option in MVP)
  backend: "faster-whisper"

  # Model size: tiny, base, small, medium, large
  # Default: small (best balance of speed and quality)
  model_size: "small"

  # Device: cuda (GPU) or cpu
  # Auto-detected if not specified
  device: "cuda"

  # Compute type: float16, int8, int8_float16
  # int8 is faster, uses less memory, minimal quality loss
  compute_type: "float16"

  # Language: en (English only in MVP)
  language: "en"

  # Model lifecycle management
  lifecycle:
    # Load model when first needed (not at startup)
    lazy_load: true

    # Unload model after this many minutes of inactivity
    # Set to 0 to keep loaded always
    # Set to -1 to unload immediately after each use
    unload_after_minutes: 5

    # Show progress during model download/loading
    show_progress: true

# Audio Settings
audio:
  # Sample rate (Hz) - Whisper expects 16kHz
  sample_rate: 16000

  # Channels: 1 (mono)
  channels: 1

  # Chunk duration in seconds for processing
  chunk_duration_seconds: 5

  # Voice Activity Detection (VAD) threshold
  # 0.0 = no VAD, 1.0 = very aggressive
  vad_threshold: 0.0  # Disabled for MVP

  # Noise reduction
  # Simple noise gate: drop audio below this amplitude
  noise_gate_threshold: 0.01

# Hotkey Settings
hotkeys:
  # Toggle recording on/off
  # Format: "modifier+modifier+key"
  # Valid modifiers: ctrl, alt, shift, win
  # Examples: "ctrl+shift+d", "ctrl+alt+r"
  toggle_recording: "ctrl+shift+d"

  # Emergency stop (force stop if stuck)
  emergency_stop: "ctrl+shift+esc"

# Text Injection Settings
text_injection:
  # Method: "win32" (Windows API), "clipboard" (fallback)
  method: "win32"

  # Typing speed simulation (characters per second)
  # 0 = instant (might not work in some apps)
  # 50-100 = natural typing speed
  typing_speed_cps: 0  # Instant for MVP

  # Delay between key events (milliseconds)
  key_delay_ms: 10

# UI Settings
ui:
  # Tray icon theme: "auto", "light", "dark"
  tray_icon_theme: "auto"

  # Show notifications for state changes
  show_notifications: true

  # Notification duration (seconds)
  notification_duration_seconds: 3

  # Flash success icon duration (milliseconds)
  success_flash_duration_ms: 1000

# Advanced Settings
advanced:
  # Maximum recording duration (seconds)
  # Prevents infinite recording if user forgets
  max_recording_duration_seconds: 300  # 5 minutes

  # Queue sizes (number of chunks)
  audio_queue_size: 50

  # Retry attempts for model loading
  model_load_retries: 3

  # Timeout for transcription (seconds)
  transcription_timeout_seconds: 60
```

### Configuration Validation

All config values validated using Pydantic:
- Type checking (int, float, str, bool)
- Range validation (e.g., log_max_size_mb > 0)
- Enum validation (e.g., model_size in [tiny, base, small, medium, large])
- Hotkey format validation (regex pattern)
- Safe YAML loading (no code execution)

---

## 1.5 User Interface Specification

### System Tray Icon States

| State | Icon | Color | Description |
|-------|------|-------|-------------|
| Idle | 🎤 Microphone | Gray | Ready to record, model may or may not be loaded |
| Recording | 🔴 Microphone | Red | Actively capturing audio |
| Processing | ⚙️ Gear | Yellow | Transcribing audio |
| Success | ✅ Check | Green | Text inserted (brief flash, then back to idle) |
| Error | ⚠️ Warning | Orange | Error occurred (stays until acknowledged) |
| Loading | ⏳ Hourglass | Blue | Loading model or downloading |

### Tray Context Menu

```
Quill
├─ ● Recording (Status: Idle/Recording/Processing)
├─ ──────────────────────
├─ 🎤 Start Recording       [if idle]
│  OR
├─ ⏸️ Stop Recording        [if recording]
├─ ──────────────────────
├─ Model: small ▶          [Submenu]
│  ├─ ( ) tiny
│  ├─ (•) small
│  ├─ ( ) medium
│  └─ ( ) large
├─ ──────────────────────
├─ Service ▶               [Submenu]
│  ├─ ● Healthy            [Status indicator]
│  ├─ 🔄 Restart Service
│  ├─ ⏹️ Stop Service
│  └─ ▶️ Start Service     [if stopped]
├─ ──────────────────────
├─ 📝 Open Config
├─ 📂 Open Logs
├─ 📊 View Stats           [Future]
├─ ──────────────────────
├─ ℹ️ About
└─ ❌ Exit
```

### Toast Notifications

| Event | Notification | Duration |
|-------|--------------|----------|
| Recording started | "🔴 Recording..." | Persistent |
| Recording stopped | "⚙️ Processing..." | Persistent |
| Model loading | "⏳ Loading [model] model..." | Persistent |
| Model downloading | "⬇️ Downloading [model] (45%)..." | Persistent + progress |
| Transcription complete | "✅ Text inserted" | 3 seconds |
| Error | "⚠️ Error: [brief message]" | 5 seconds |
| Model unloaded | "💤 Model unloaded (idle)" | 2 seconds |

---

## 1.6 File Structure

```
Quill/
├── src/
│   └── Quill/
│       ├── __init__.py
│       ├── __main__.py              # Entry point: python -m Quill
│       ├── app.py                   # Main application class
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py            # Pydantic models for validation
│       │   └── manager.py           # Config loading/saving
│       │
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── capture.py           # Audio capture (sounddevice)
│       │   ├── preprocessing.py     # Noise gate, resampling
│       │   └── vad.py               # Voice Activity Detection (future)
│       │
│       ├── transcription/
│       │   ├── __init__.py
│       │   ├── engine.py            # Abstract transcription interface
│       │   ├── faster_whisper.py    # Faster-Whisper implementation
│       │   └── model_manager.py     # Download, load, unload models
│       │
│       ├── injection/
│       │   ├── __init__.py
│       │   ├── injector.py          # Abstract text injection interface
│       │   └── windows.py           # Windows-specific (win32api)
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── tray.py              # System tray (pystray)
│       │   ├── notifications.py     # Toast notifications (Windows)
│       │   └── icons.py             # Icon management
│       │
│       ├── hotkeys/
│       │   ├── __init__.py
│       │   └── listener.py          # Hotkey detection (keyboard library)
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py           # Logging setup
│           ├── threading.py         # Thread utilities, queues
│           └── errors.py            # Custom exceptions
│
├── models/                          # Downloaded Whisper models
│   └── .gitkeep
│
├── logs/                            # Application logs
│   └── .gitkeep
│
├── config.yaml                      # User configuration
├── config.example.yaml              # Example configuration
│
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_audio.py
│   ├── test_transcription.py
│   └── test_injection.py
│
├── docs/
│   ├── initial-plan/
│   │   ├── overview.md
│   │   ├── g-helper-ui-analysis.md
│   │   ├── ui-runtime-considerations.md
│   │   ├── architectural-analysis.md
│   │   └── mvp-implementation-plan.md  # This document
│   └── issues.md
│
├── .venv/                           # Virtual environment
├── .gitignore
├── pyproject.toml                   # Project dependencies (uv/poetry)
├── README.md
└── LICENSE
```

---

## 1.7 Dependencies

### Core Dependencies

```toml
[project]
name = "Quill"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Audio processing
    "sounddevice>=0.4.6",
    "numpy>=1.24.0",
    "scipy>=1.11.0",  # For audio preprocessing

    # Transcription
    "faster-whisper>=1.0.0",
    "torch>=2.0.0",  # Required by faster-whisper

    # UI
    "pystray>=0.19.5",
    "Pillow>=10.0.0",  # For tray icons

    # Hotkeys
    "keyboard>=0.13.5",

    # Text injection (Windows)
    "pywin32>=306",

    # Configuration
    "pydantic>=2.5.0",
    "ruamel.yaml>=0.18.0",

    # Logging
    "loguru>=0.7.0",

    # Utilities
    "requests>=2.31.0",  # For model downloads
    "tqdm>=4.66.0",  # Progress bars
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

---

## 1.8 Success Criteria

### MVP is considered successful if:

1. ✅ **Core functionality works**
   - User can press hotkey, speak, press hotkey again
   - Text appears in active application
   - Accuracy is acceptable (>90% WER for clear speech)

2. ✅ **Performance is acceptable**
   - Model loads in <5 seconds with progress feedback
   - Transcription completes in <3 seconds for typical 5s audio clip (GPU)
   - No audio dropouts during recording
   - UI remains responsive

3. ✅ **Reliability is acceptable**
   - Runs for hours without crashes
   - Handles common errors gracefully (no GPU, no mic, etc.)
   - Model lifecycle works (loads/unloads correctly)

4. ✅ **Configuration is flexible**
   - Can easily change models, hotkeys, settings via YAML
   - Config validation prevents invalid settings
   - Logs are useful for debugging

5. ✅ **UX is not frustrating**
   - Clear feedback on what's happening (notifications)
   - Obvious how to start/stop recording
   - Errors are actionable ("No microphone detected - please connect one")

---

# Part 2: Detailed Implementation Plan

## 2.1 Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Basic project structure and core utilities

**Tasks:**
1. Set up project structure and virtual environment
2. Configure dependency management (uv or poetry)
3. Create config schema and validation (Pydantic)
4. Implement logging system (loguru)
5. Create basic error types and exceptions
6. Write initial tests for config and logging

**Deliverables:**
- Working project structure
- Config loading/validation
- Structured logging to file
- Basic test suite

**Success Criteria:**
- Can load config.yaml and validate all fields
- Logs are written to file with rotation
- Tests pass

---

### Phase 2: Audio Capture (Week 1-2)
**Goal:** Reliable audio recording from microphone

**Tasks:**
1. Implement audio capture using sounddevice
2. Create ring buffer for audio chunks
3. Add basic preprocessing (resampling to 16kHz)
4. Implement noise gate
5. Add recording start/stop logic
6. Handle audio device errors gracefully
7. Write audio capture tests

**Deliverables:**
- AudioCapture class
- Ring buffer implementation
- Audio preprocessing pipeline
- Error handling for device issues

**Success Criteria:**
- Can record audio from default microphone
- Audio is correctly resampled to 16kHz mono
- Recording can be started/stopped cleanly
- Handles microphone disconnect gracefully

**Key Code Modules:**
- `src/Quill/audio/capture.py`
- `src/Quill/audio/preprocessing.py`
- `src/Quill/utils/threading.py`

---

### Phase 3: Transcription Engine (Week 2)
**Goal:** Working Whisper transcription with service-based model management

**Tasks:**
1. Implement TranscriptionService (always-running service)
2. Implement model download with progress
3. Implement model loading (background, non-blocking)
4. Create Faster-Whisper integration
5. Add prepare() method (triggers model loading)
6. Add transcribe() method (blocking inference)
7. Add model lifecycle management (load/unload timer)
8. Add model integrity verification (SHA256)
9. Handle GPU/CPU fallback
10. Write transcription tests

**Deliverables:**
- TranscriptionService class (health check, prepare, transcribe)
- ModelManager class (download, verify, load, unload)
- FasterWhisperEngine class
- Background model loading (non-blocking prepare())
- Lifecycle management (idle timeout)
- Progress feedback for downloads

**Success Criteria:**
- prepare() returns immediately, triggers background loading
- Can download models from HuggingFace
- Models load successfully on GPU and CPU
- Transcription produces accurate text
- Model unloads after idle timeout
- Handles OOM errors gracefully
- Service stays alive throughout application lifetime

**Key Code Modules:**
- `src/Quill/transcription/service.py` (NEW - TranscriptionService)
- `src/Quill/transcription/model_manager.py`
- `src/Quill/transcription/faster_whisper.py`
- `src/Quill/transcription/engine.py`

**Critical Implementation Details:**

```python
# Transcription Service pseudocode
class TranscriptionService:
    """
    Always-running service that manages model lifecycle.
    Runs in separate thread, always alive.
    """

    def __init__(self, config):
        self.config = config
        self.model_manager = ModelManager(config)
        self.state = "idle"  # idle, loading, ready, error
        self.lock = threading.Lock()
        self.last_used = None

    def health_check(self):
        """Check if service is alive"""
        return {
            "status": "ok",
            "state": self.state,
            "model_loaded": self.model_manager.current_model is not None
        }

    def prepare(self):
        """
        Signal that transcription will be needed soon.
        Triggers model loading if not loaded.
        Returns immediately (non-blocking).
        """
        with self.lock:
            if self.state == "ready":
                # Model already loaded
                logger.debug("Model already ready")
                return {"status": "ready"}

            if self.state == "loading":
                # Already loading
                logger.debug("Model already loading")
                return {"status": "loading"}

            if self.state == "idle":
                # Start loading model in background
                logger.info("Starting background model load")
                threading.Thread(
                    target=self._load_model_background,
                    daemon=True
                ).start()
                return {"status": "loading"}

            return {"status": "error"}

    def _load_model_background(self):
        """Background model loading (runs in separate thread)"""
        try:
            self.state = "loading"
            logger.info("Loading model...")

            # Load model (this takes 3-5 seconds)
            self.model_manager.load_model(
                self.config.transcription.model_size,
                self.config.transcription.device
            )

            with self.lock:
                self.state = "ready"
            logger.info("Model loaded and ready")

        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            with self.lock:
                self.state = "error"

    def transcribe(self, audio_data):
        """
        Blocking transcription.
        Will wait if model still loading.
        """
        # Wait for model to be ready (if still loading)
        max_wait = 10  # seconds
        waited = 0
        while self.state == "loading" and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1

        if self.state != "ready":
            raise TranscriptionError(f"Model not ready (state: {self.state})")

        # Run transcription
        result = self.model_manager.transcribe(audio_data)
        self.last_used = time.time()

        return result

    def check_idle_timeout(self):
        """Called periodically by idle monitor thread"""
        if self.state == "ready" and self.last_used:
            idle_time = time.time() - self.last_used
            timeout = self.config.transcription.lifecycle.unload_after_minutes * 60

            if idle_time > timeout:
                logger.info(f"Model idle for {idle_time:.0f}s, unloading")
                self.model_manager.unload_model()
                with self.lock:
                    self.state = "idle"

# Model Manager pseudocode (simplified, supports TranscriptionService)
class ModelManager:
    def __init__(self, config):
        self.models_dir = Path("models")
        self.current_model = None
        self.config = config

    def load_model(self, model_size, device="cuda"):
        """Load model (blocking operation)"""
        if self.current_model:
            self.unload_model()

        model_path = self.models_dir / model_size
        self.current_model = WhisperModel(model_path, device=device)
        logger.info(f"Loaded {model_size} model on {device}")

    def unload_model(self):
        """Unload model and free memory"""
        if self.current_model:
            del self.current_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.current_model = None
            logger.info("Model unloaded")

    def transcribe(self, audio_data):
        """Run inference (blocking)"""
        if not self.current_model:
            raise TranscriptionError("No model loaded")

        segments, info = self.current_model.transcribe(audio_data)
        text = " ".join([seg.text for seg in segments])
        return text
```

---

### Phase 4: Text Injection (Week 2-3)
**Goal:** Inject transcribed text into active Windows application

**Tasks:**
1. Implement Windows text injection via win32api
2. Handle special characters (Unicode, emoji)
3. Add clipboard fallback mode
4. Implement typing speed simulation (if needed)
5. Handle focus/permission errors
6. Write injection tests (mock win32api)

**Deliverables:**
- WindowsTextInjector class
- Clipboard fallback
- Error handling for injection failures

**Success Criteria:**
- Can inject text into notepad, VS Code, browser
- Unicode characters work correctly
- Falls back to clipboard if injection fails
- No crashes from permission errors

**Key Code Modules:**
- `src/Quill/injection/windows.py`
- `src/Quill/injection/injector.py`

**Critical Implementation Details:**

```python
# Text Injector pseudocode
class WindowsTextInjector:
    def inject(self, text):
        try:
            # Method 1: Direct keyboard simulation
            if self._can_use_keyboard():
                return self._inject_via_keyboard(text)
        except Exception as e:
            logger.warning(f"Keyboard injection failed: {e}")

        try:
            # Method 2: Clipboard + Ctrl+V
            return self._inject_via_clipboard(text)
        except Exception as e:
            logger.error(f"Clipboard injection failed: {e}")
            raise InjectionError("All injection methods failed")

    def _inject_via_keyboard(self, text):
        # Use win32api to simulate keystrokes
        for char in text:
            vk_code = win32api.VkKeyScanEx(char, 0)
            win32api.keybd_event(vk_code, 0, 0, 0)
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(self.key_delay / 1000)

    def _inject_via_clipboard(self, text):
        # Save current clipboard
        old_clipboard = pyperclip.paste()

        # Copy text to clipboard
        pyperclip.copy(text)

        # Simulate Ctrl+V
        self._simulate_ctrl_v()

        # Restore old clipboard (optional)
        pyperclip.copy(old_clipboard)
```

---

### Phase 5: System Tray UI (Week 3)
**Goal:** Functional tray icon with state management

**Tasks:**
1. Create tray icon with pystray
2. Implement icon state changes (idle/recording/processing/success/error)
3. Build context menu with actions
4. Add Windows toast notifications
5. Handle tray icon clicks
6. Implement "Open Config" and "Open Logs" actions
7. Write UI tests (headless where possible)

**Deliverables:**
- TrayIcon class with state management
- Context menu with all actions
- Toast notification wrapper
- Icon assets (5 states)

**Success Criteria:**
- Tray icon appears in system tray
- Icon updates reflect current state
- Context menu works (all actions functional)
- Notifications appear correctly
- No UI crashes or hangs

**Key Code Modules:**
- `src/Quill/ui/tray.py`
- `src/Quill/ui/notifications.py`
- `src/Quill/ui/icons.py`

**Critical Implementation Details:**

```python
# Tray Icon pseudocode
class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.state = "idle"

    def create(self):
        menu = pystray.Menu(
            pystray.MenuItem("Start Recording", self.start_recording,
                           visible=lambda item: self.state == "idle"),
            pystray.MenuItem("Stop Recording", self.stop_recording,
                           visible=lambda item: self.state == "recording"),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Model", pystray.Menu(
                pystray.MenuItem("tiny", self.set_model_tiny),
                pystray.MenuItem("small", self.set_model_small, checked=True),
                # ...
            )),
            # ... more menu items
        )

        self.icon = pystray.Icon(
            "Quill",
            icon=self.get_icon_for_state("idle"),
            title="Quill",
            menu=menu
        )

    def update_state(self, new_state):
        self.state = new_state
        self.icon.icon = self.get_icon_for_state(new_state)
        self.icon.title = f"Quill - {new_state.title()}"

    def get_icon_for_state(self, state):
        # Load appropriate icon image
        icon_map = {
            "idle": "microphone_gray.png",
            "recording": "microphone_red.png",
            "processing": "gear_yellow.png",
            "success": "check_green.png",
            "error": "warning_orange.png"
        }
        return Image.open(f"assets/icons/{icon_map[state]}")
```

---

### Phase 6: Hotkey Integration (Week 3)
**Goal:** Global hotkey detection and handling

**Tasks:**
1. Implement hotkey listener using keyboard library
2. Parse hotkey config strings
3. Handle toggle recording logic
4. Add emergency stop hotkey
5. Handle hotkey conflicts gracefully
6. Write hotkey tests

**Deliverables:**
- HotkeyListener class
- Hotkey parsing and validation
- Toggle recording state management

**Success Criteria:**
- Hotkey works globally (in any application)
- Toggle logic works correctly (start → stop → start)
- Emergency stop immediately halts recording
- Conflicts are detected and logged
- No missed hotkey presses

**Key Code Modules:**
- `src/Quill/hotkeys/listener.py`

**Critical Implementation Details:**

```python
# Hotkey Listener pseudocode
class HotkeyListener:
    def __init__(self, config, app):
        self.config = config
        self.app = app
        self.is_recording = False

    def start(self):
        # Register hotkeys
        toggle_hotkey = self.config.hotkeys.toggle_recording
        keyboard.add_hotkey(toggle_hotkey, self.on_toggle_recording)

        emergency_hotkey = self.config.hotkeys.emergency_stop
        keyboard.add_hotkey(emergency_hotkey, self.on_emergency_stop)

        logger.info(f"Hotkeys registered: {toggle_hotkey}, {emergency_hotkey}")

    def on_toggle_recording(self):
        if not self.is_recording:
            # Starting recording
            logger.info("Hotkey: Start recording")

            # 1. Ping transcription service to prepare
            service_status = self.app.transcription_service.prepare()

            if service_status["status"] == "error":
                # Service is broken, don't start recording
                self.app.show_notification("⚠️ Transcription service error")
                logger.error("Cannot start recording: service error")
                return

            # 2. Start recording (service is preparing in background)
            self.app.start_recording()
            self.is_recording = True

            if service_status["status"] == "loading":
                # Optional: Log that model is loading
                logger.info("Model loading in background...")

        else:
            # Stopping recording
            logger.info("Hotkey: Stop recording")
            self.app.stop_recording()
            self.is_recording = False

    def on_emergency_stop(self):
        logger.warning("Emergency stop triggered")
        self.app.emergency_stop()
        self.is_recording = False
```

---

### Phase 7: Main Application Integration (Week 4)
**Goal:** Connect all components into working application

**Tasks:**
1. Create main App class that orchestrates all components
2. Implement state machine for recording flow
3. Connect audio → transcription → injection pipeline
4. Add threading coordination
5. Implement idle monitor for model unloading
6. Add startup/shutdown logic
7. Handle all error scenarios
8. Write integration tests

**Deliverables:**
- Complete App class
- State machine implementation
- Full pipeline integration
- Graceful startup/shutdown

**Success Criteria:**
- Complete recording → transcription → injection flow works
- State transitions are clean
- No deadlocks or race conditions
- Errors are handled gracefully
- Can run for extended periods without issues

**Key Code Modules:**
- `src/Quill/app.py`
- `src/Quill/__main__.py`

**Critical Implementation Details:**

```python
# Main App pseudocode
class QuillApp:
    def __init__(self, config_path="config.yaml"):
        self.config = ConfigManager.load(config_path)
        self.state = "idle"

        # Initialize components
        self.transcription_service = TranscriptionService(self.config)
        self.audio_capture = AudioCapture(self.config)
        self.text_injector = WindowsTextInjector(self.config)
        self.tray_icon = TrayIcon(self)
        self.hotkey_listener = HotkeyListener(self.config, self)

        # Threading
        self.audio_queue = queue.Queue(maxsize=50)
        self.transcription_thread = None
        self.idle_monitor_thread = None

        # Setup logging
        setup_logging(self.config)

    def start(self):
        logger.info("Starting Quill")

        # Start idle monitor
        self.idle_monitor_thread = threading.Thread(
            target=self._idle_monitor_loop, daemon=True
        )
        self.idle_monitor_thread.start()

        # Start hotkey listener
        self.hotkey_listener.start()

        # Start tray icon (blocking)
        self.tray_icon.create()
        self.tray_icon.run()

    def start_recording(self):
        if self.state != "idle":
            logger.warning("Cannot start recording: not idle")
            return

        logger.info("Starting recording")
        self.state = "recording"
        self.tray_icon.update_state("recording")
        self.show_notification("🔴 Recording...")

        # Start audio capture
        self.audio_capture.start(self.audio_queue)

    def stop_recording(self):
        if self.state != "recording":
            logger.warning("Cannot stop recording: not recording")
            return

        logger.info("Stopping recording")
        self.state = "processing"
        self.tray_icon.update_state("processing")

        # Stop audio capture
        audio_data = self.audio_capture.stop()

        # Start transcription in background
        self.transcription_thread = threading.Thread(
            target=self._transcribe_and_inject,
            args=(audio_data,),
            daemon=True
        )
        self.transcription_thread.start()

    def _transcribe_and_inject(self, audio_data):
        try:
            # Show processing notification
            self.show_notification("⚙️ Processing...")

            # Call transcription service
            # (model should already be loading/loaded from prepare() call)
            text = self.transcription_service.transcribe(audio_data)
            logger.info(f"Transcribed: {text[:50]}...")

            # Inject text (must be on main thread for Windows)
            # Use GLib.idle_add or similar to post to main thread
            self._inject_text_on_main_thread(text)

            # Update state
            self.state = "idle"
            self.tray_icon.update_state("success")
            self.show_notification("✅ Text inserted")

            # Flash success, then back to idle
            threading.Timer(1.0, lambda: self.tray_icon.update_state("idle")).start()

        except Exception as e:
            logger.error(f"Transcription/injection failed: {e}", exc_info=True)
            self.state = "error"
            self.tray_icon.update_state("error")
            self.show_notification(f"⚠️ Error: {str(e)[:50]}")

    def _idle_monitor_loop(self):
        while True:
            time.sleep(60)  # Check every minute
            self.transcription_service.check_idle_timeout()

    def emergency_stop(self):
        logger.warning("Emergency stop")
        self.audio_capture.stop()
        self.state = "idle"
        self.tray_icon.update_state("idle")

    def shutdown(self):
        logger.info("Shutting down Quill")
        self.audio_capture.cleanup()
        self.transcription_service.model_manager.unload_model()
        self.hotkey_listener.stop()
        self.tray_icon.stop()
```

---

### Phase 8: Testing & Debugging (Week 4-5)
**Goal:** Comprehensive testing and bug fixes

**Tasks:**
1. Write unit tests for all components
2. Write integration tests for full pipeline
3. Test error scenarios (no mic, no GPU, bad config, etc.)
4. Test long-running stability (hours)
5. Test model lifecycle (load/unload)
6. Test memory usage and leaks
7. Fix bugs discovered during testing
8. Document known issues

**Deliverables:**
- Comprehensive test suite
- Bug fixes
- Performance profiling results
- Updated documentation

**Success Criteria:**
- >80% code coverage
- All critical paths tested
- No crashes in 8-hour stress test
- Memory usage stable over time
- All known bugs documented or fixed

---

### Phase 9: Documentation & Polish (Week 5)
**Goal:** Production-ready documentation and UX polish

**Tasks:**
1. Write comprehensive README
2. Document installation instructions
3. Create example config with comments
4. Write troubleshooting guide
5. Polish notification messages
6. Improve error messages to be actionable
7. Add version info to tray menu
8. Final UX review and tweaks

**Deliverables:**
- Complete README.md
- Commented config.example.yaml
- Troubleshooting guide
- Polished error messages

**Success Criteria:**
- Can follow README and get running in <10 minutes
- All error messages are clear and actionable
- Example config covers all options
- Documentation is complete

---

## 2.2 Testing Strategy

### Unit Tests

**Coverage targets:**
- Config loading and validation: 100%
- Audio preprocessing: >90%
- Text injection logic: >80%
- Tray menu actions: >70%

**Mocking strategy:**
- Mock sounddevice for audio tests
- Mock win32api for injection tests
- Mock faster-whisper for transcription tests
- Mock pystray for UI tests

### Integration Tests

**Test scenarios:**
1. Full pipeline: hotkey → audio → transcription → injection
2. Model lifecycle: load → use → idle timeout → unload
3. Error recovery: no mic → disconnect mic → reconnect
4. Config changes: change model → reload → verify new model used
5. Long recording: 5 minute recording → transcription → injection

### Manual Testing Checklist

- [ ] Install from scratch on clean Windows machine
- [ ] Test with different microphones
- [ ] Test with GPU and without GPU
- [ ] Test all tray menu actions
- [ ] Test all hotkeys
- [ ] Test all model sizes
- [ ] Verify notifications appear correctly
- [ ] Test in various applications (notepad, VS Code, browser, etc.)
- [ ] Test edge cases (very short recording, very long recording, silence)
- [ ] Test error scenarios (bad config, corrupt model, etc.)

---

## 2.3 Development Environment Setup

### Prerequisites

```bash
# Required software
- Windows 10/11 x64
- Python 3.11+
- Git
- CUDA Toolkit 11.8+ (for GPU support)
- Visual Studio Build Tools (for pywin32)

# Optional
- NVIDIA GPU with 4GB+ VRAM
- Good microphone
```

### Setup Steps

```bash
# 1. Clone repository
cd /mnt/d/github/quill
git status  # Verify we're in the right place

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/WSL:
source .venv/bin/activate

# 4. Install dependencies using uv (fast) or pip
pip install uv
uv pip install -e ".[dev]"

# OR with pip:
pip install -e ".[dev]"

# 5. Create initial config
cp config.example.yaml config.yaml

# 6. Create necessary directories
mkdir -p models logs

# 7. Run tests to verify setup
pytest

# 8. Run application
python -m Quill
```

---

## 2.4 Development Workflow

### Daily Development

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 2. Pull latest changes
git pull

# 3. Run tests before making changes
pytest

# 4. Make changes, write tests

# 5. Run tests again
pytest

# 6. Format code
black src/
ruff check src/ --fix

# 7. Type check
mypy src/

# 8. Run app to manually test
python -m Quill

# 9. Commit
git add .
git commit -m "feat: add feature X"

# 10. Push
git push
```

### Git Workflow

```
Branches:
- main: Stable, working code
- develop: Integration branch
- feature/*: Feature branches
- bugfix/*: Bug fix branches

Commit message format:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- test: Tests
- refactor: Code restructuring
- chore: Maintenance

Example:
git checkout -b feature/tray-icon
# ... make changes ...
git commit -m "feat: implement tray icon with state management"
git push origin feature/tray-icon
# ... create PR to develop ...
```

---

## 2.5 Performance Targets

### Latency Targets

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Hotkey response | <50ms | 100ms |
| Recording start | <100ms | 200ms |
| Model loading (small, GPU) | <3s | 5s |
| Transcription (5s audio, small, GPU) | <1s | 3s |
| Text injection (50 chars) | <100ms | 500ms |
| Total latency (5s recording) | <5s | 10s |

### Memory Targets

| Component | Baseline | With Model Loaded |
|-----------|----------|-------------------|
| Python runtime | 30MB | 30MB |
| Dependencies | 50MB | 50MB |
| Audio buffers | 10MB | 10MB |
| Whisper model (small) | 0MB | 2GB |
| **Total** | **90MB** | **2.1GB** |

### Optimization Priorities

1. **Critical:** Audio capture must not drop frames
2. **High:** Transcription latency under 3s (GPU)
3. **High:** Model loading feedback (progress bar)
4. **Medium:** Reduce baseline memory usage
5. **Low:** Optimize text injection speed

---

## 2.6 Risk Management

### High-Priority Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model loading timeout | Medium | High | Add timeout, fallback to tiny model |
| Audio device disconnected | High | High | Detect and gracefully stop recording |
| GPU OOM with large model | Medium | High | Catch exception, unload, suggest smaller model |
| Hotkey conflicts with other apps | Low | Medium | Detect conflicts, suggest alternative |
| Text injection fails | Low | High | Fallback to clipboard mode |

### Testing Risks

- Not testing on clean Windows machine → might have hidden dependencies
- Not testing without GPU → CPU fallback might be broken
- Not testing long-running stability → memory leaks go unnoticed

**Mitigation:** Set up test VM or dedicated test machine

---

## 2.7 Success Metrics

### MVP Launch Readiness Checklist

**Functionality:**
- [ ] Can record audio via hotkey
- [ ] Can transcribe with all 5 model sizes
- [ ] Can inject text into common applications
- [ ] Tray icon shows correct state
- [ ] Notifications appear correctly
- [ ] Model lifecycle works (load/unload)
- [ ] Config changes take effect

**Reliability:**
- [ ] No crashes in 4-hour continuous run
- [ ] Handles common errors gracefully
- [ ] Memory usage stable over time
- [ ] Can recover from GPU OOM

**Performance:**
- [ ] Transcription <3s for 5s audio (GPU, small model)
- [ ] Model loads in <5s with progress
- [ ] No audio dropouts

**Usability:**
- [ ] Can install and run following README only
- [ ] Error messages are clear
- [ ] Logs are useful for debugging
- [ ] Config is self-documenting

**Code Quality:**
- [ ] Test coverage >80%
- [ ] No critical bugs in issue tracker
- [ ] Code is formatted (black)
- [ ] Type hints are correct (mypy)

---

## 2.8 Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Foundation + Audio Capture | Config, logging, audio recording |
| 2 | Transcription Engine | Model download, loading, transcription |
| 2-3 | Text Injection | Windows text injection |
| 3 | Tray UI + Hotkeys | Tray icon, notifications, hotkeys |
| 4 | Integration | Complete pipeline working |
| 4-5 | Testing & Debugging | Bug fixes, stability |
| 5 | Documentation & Polish | README, final UX polish |

**Total:** ~5 weeks for MVP

**Buffer:** +1 week for unexpected issues

**Target completion:** 6 weeks from start

---

## 2.9 Next Steps

### Immediate Actions (This Week)

1. **Set up development environment**
   - Create project structure
   - Install dependencies
   - Verify GPU is accessible

2. **Implement Phase 1 (Foundation)**
   - Create config schema
   - Set up logging
   - Write initial tests

3. **Prototype Phase 2 (Audio)**
   - Get basic audio recording working
   - Verify sounddevice works correctly
   - Test resampling to 16kHz

### Week 1 Milestone

By end of Week 1, should have:
- Working config system
- Audio capture functional
- Logs writing correctly
- Tests passing

**Go/No-Go Decision Point:**
If audio capture has fundamental issues, may need to revisit approach.

---

## Appendix A: Code Skeleton

### Main Entry Point

```python
# src/Quill/__main__.py
"""
Quill - Local speech-to-text dictation tool
"""
import sys
from pathlib import Path
from Quill.app import QuillApp
from Quill.utils.logging import setup_logging

def main():
    # Find config
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("ERROR: config.yaml not found")
        print("Please create config.yaml from config.example.yaml")
        sys.exit(1)

    try:
        # Create and start app
        app = QuillApp(config_path)
        app.start()  # Blocking

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Appendix B: Error Handling Patterns

### Standard Error Handling

```python
from Quill.utils.errors import (
    QuillError,
    AudioCaptureError,
    TranscriptionError,
    InjectionError,
    ConfigError
)

def risky_operation():
    try:
        # Do something that might fail
        result = dangerous_call()
        return result

    except SpecificError as e:
        # Log and handle specific error
        logger.error(f"Specific error: {e}", exc_info=True)
        # Try recovery
        return fallback_operation()

    except Exception as e:
        # Log and re-raise as QuillError
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise QuillError(f"Operation failed: {e}") from e
```

---

## Appendix C: Configuration Validation Example

```python
from pydantic import BaseModel, Field, validator
from typing import Literal
from pathlib import Path

class TranscriptionConfig(BaseModel):
    backend: Literal["faster-whisper"] = "faster-whisper"
    model_size: Literal["tiny", "base", "small", "medium", "large"] = "small"
    device: Literal["cuda", "cpu"] = "cuda"
    compute_type: Literal["float16", "int8", "int8_float16"] = "float16"
    language: str = "en"

    @validator("device")
    def validate_device(cls, v):
        if v == "cuda":
            import torch
            if not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                return "cpu"
        return v

class Config(BaseModel):
    transcription: TranscriptionConfig
    # ... other sections

    class Config:
        extra = "forbid"  # Don't allow unknown fields
```

---

## End of Document

**Document Version:** 1.0
**Last Updated:** 2025-01-13
**Status:** Ready for Implementation

This implementation plan provides a complete roadmap from zero to working MVP in approximately 5-6 weeks. Each phase builds on the previous, with clear deliverables and success criteria.

Next step: Begin Phase 1 (Foundation) by setting up the project structure and configuration system.
