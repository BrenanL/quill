Perfect — here’s a **complete description, architecture, and specification document** for your dictation tool project. It’s written to be ready for a coding agent or small engineering team to implement and iterate on.

---

# 🎙️ Quill: Local + Modular Speech-to-Text Dictation Tool

## 1. Overview

**Quill** is a local, cross-platform dictation utility designed to replace native OS dictation (e.g. Windows + H). It provides high-quality transcription using **OpenAI’s Whisper** (via **Faster-Whisper** for local inference) with configurable modes, models, and streaming/transcription strategies.
The tool is modular, lightweight, and extensible — built to evolve from a personal productivity app into a cloud-synced multi-device assistant.

---

## 2. Objectives

* Deliver **high-quality local transcription** using Whisper or compatible APIs.
* Enable **custom hotkey activation** and **tray-based control UI**.
* Support **push-to-talk** and **toggle** dictation modes.
* Stream text into **any text field** on the OS (system-level input injection).
* Provide a **configurable, modular architecture** for experimentation and future extensions.
* Offer **real-time or near-real-time** transcription modes (batch or streaming).
* Ensure **cross-platform support**: Windows and Linux (native, no WSL).

---

## 3. Architecture Overview

### 3.1 Core Components

| Component                 | Description                                                                                                                                            |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Frontend / UI Layer**   | System tray icon, recording indicator popup, basic settings window.                                                                                    |
| **Audio Capture Service** | Listens to microphone input and streams or batches audio segments. Configurable for sampling rate, chunking, silence detection, etc.                   |
| **Processing Pipeline**   | Handles optional preprocessing modules (e.g. noise filtering, silence trimming, VAD, voice isolation). Modular interface for swapping implementations. |
| **Transcription Engine**  | Interfaces with Faster-Whisper or OpenAI Whisper API. Converts audio to text. Configurable model size and backend.                                     |
| **Text Injection Layer**  | Inserts transcribed text into the active OS text field. Platform-specific modules (Windows: pywin32 / keyboard; Linux: xdotool).                       |
| **Configuration System**  | YAML/JSON config with runtime reload and UI-based editing. Controls model selection, hotkeys, streaming mode, etc.                                     |
| **Logging / Telemetry**   | Local logs for debugging, optional anonymized performance metrics.                                                                                     |

---

## 4. High-Level Flow

### User Flow (Toggle Mode)

1. **User presses configured hotkey** (e.g. `Ctrl+Shift+D`).
2. **Tray icon changes state** → “Recording” indicator appears.
3. **Audio Capture Service** starts collecting audio chunks.
4. **Processing Pipeline** filters and segments audio (configurable chunk size).
5. **Transcription Engine** processes chunks and returns text incrementally.
6. **Text Injection Layer** inserts text where the user’s cursor is focused.
7. **User presses hotkey again** → dictation stops, UI resets.

### User Flow (Push-to-Talk Mode)

1. **User holds hotkey**, audio capture + transcription runs.
2. On **key release**, text is injected and service pauses.

---

## 5. Modular System Design

### 5.1 Audio Capture Module

* **Implementation:** PyAudio, SoundDevice, or PortAudio.
* **Features:**

  * Configurable chunk length (e.g. 5 sec)
  * Automatic silence detection / VAD
  * Configurable sampling rate (16kHz default)
  * Output: WAV or PCM buffer stream

### 5.2 Processing Pipeline

* **Goal:** Prepares audio before transcription.
* **Plugin system:** Load processors defined in config (`processors: [“noise_reduction”, “silence_trim”]`).
* **Possible processors:**

  * Noise filtering
  * Dead-air trimming
  * Voice isolation (future)
  * Chunk buffering (combine short clips)
  * Adaptive streaming (based on CPU load)

### 5.3 Transcription Engine

* **Default:** Faster-Whisper backend (local inference)
* **Alternative:** OpenAI Whisper API or custom API endpoint
* **Configurable options:**

  * Model size (`tiny`, `base`, `small`, `medium`, `large`)
  * **Default model:** `small` (best balance of speed and quality)
  * Precision (FP16/INT8)
  * Device (`cpu` or `cuda`)
  * API endpoint (for remote inference or self-hosted models)
  * Streaming interval (e.g. 5s)
  * **Lazy loading:** Model loaded on first use, kept in memory afterward
* **Outputs:** plain text or structured timestamps for advanced use.

### 5.4 Text Injection Layer

* **Windows:** `pywin32`, `keyboard`, or `pynput`
* **Linux:** `xdotool` or `uinput`
* Must handle multi-language input, emoji, and system clipboard fallback.

### 5.5 Configuration System

* **File:** `config.yaml`
* **Editable through UI**
* **Example keys:**

  ```yaml
  model_backend: "faster-whisper"
  model_size: "small"
  device: "cuda"
  api_endpoint: null  # or "https://api.openai.com/v1" or custom URL
  api_key: null  # optional, for API-based backends
  hotkey: "ctrl+shift+d"
  mode: "toggle"  # or "push-to-talk"
  chunk_length: 5
  silence_threshold: 0.01
  stream_text: true
  log_level: "info"
  lazy_load: true  # load model only on first use
  ```
* **Runtime reload:** watch file or trigger via tray menu.

### 5.6 Tray and UI Layer

* **Tray Framework:** `pystray` (ultra-lightweight, cross-platform)
* **Settings UI:** `tkinter` (built-in, minimal dependencies)
* **Design Philosophy:** Tray-first approach inspired by [g-helper](https://github.com/seerge/g-helper)
  * Application starts with **tray icon only** (no visible windows)
  * Persistent background service for instant response
  * Model lazy-loaded on first recording
* **Tray options:**

  * Left-click: Toggle recording on/off
  * Right-click menu:
    * Start/Stop Recording
    * Select Model (tiny/base/small/medium/large)
    * Settings
    * Exit
* **Tray icon states:**
  * Gray microphone: Idle
  * Red microphone: Recording
  * Yellow gear: Processing
  * Green check: Success (brief flash)
* **Indicator UI:**

  * **Phase 1:** Native OS notifications ("🔴 Recording...", "✅ Text inserted")
  * **Phase 2:** Custom overlay window (like g-helper's ToastForm)
  * Position: Near system tray, auto-hide after completion

---

## 6. Platform-Specific Considerations

### Windows

* Hotkey handling via `keyboard` or Windows API
* Tray icon via `pystray` (handles Windows system tray automatically)
* Notifications: Windows Toast Notifications (built-in)
* Audio: WASAPI backend
* GPU acceleration: Requires NVIDIA GPU + CUDA if using Faster-Whisper

### Linux

* Hotkey: `pynput` or system keybinding
* Tray icon via `pystray` (auto-detects AppIndicator/StatusNotifier)
* Notifications: D-Bus notifications (notify-send)
* Audio: ALSA or PulseAudio
* GPU: NVIDIA CUDA or ROCm (AMD)

---

## 7. Performance & Model Selection Guide

| Model  | Params | Speed (x real-time)* | VRAM (FP16) | Quality   |
| ------ | ------ | -------------------- | ----------- | --------- |
| tiny   | 39M    | ~32×                 | <1GB        | Fair      |
| base   | 74M    | ~16×                 | ~1GB        | Good      |
| small  | 244M   | ~6×                  | ~2GB        | Very Good |
| medium | 769M   | ~2×                  | ~5GB        | Excellent |
| large  | 1550M  | ~1×                  | ~10GB       | Best      |

*Based on RTX 3060 GPU or equivalent.
CPU-only speed: roughly 3–5× slower.

> **Default model:** `small` (best balance for most users)
> **Lazy loading strategy:** Model loaded on first use, kept in memory for instant subsequent recordings

---

## 8. Extensibility & Future Plans

* ✅ Cloud sync for config + personal vocab
* ✅ Custom dictionary correction layer
* ✅ Real-time streaming transcription
* ✅ Auto-punctuation & formatting (via LLM post-processor)
* ✅ Integration with note apps or IDEs (via plugin interface)
* ✅ Voice command parsing (“new line”, “delete word”)

---

## 9. Toolchain and Environment

| Category               | Tools                                  |
| ---------------------- | -------------------------------------- |
| **Language**           | Python 3.11+                           |
| **Package Manager**    | `uv` or `poetry`                       |
| **Audio Libraries**    | `sounddevice`, `pyaudio`               |
| **Transcription**      | `faster-whisper`                       |
| **UI / Tray**          | `pystray` (tray), `tkinter` (settings) |
| **Notifications**      | Native OS (Windows Toast, Linux D-Bus) |
| **Hotkeys / Keyboard** | `keyboard`, `pynput`                   |
| **Config / Logging**   | `ruamel.yaml`, `loguru`                |
| **Packaging**          | `PyInstaller` for distribution         |
| **Testing**            | `pytest`                               |

---

## 9.5 Installation & Development

### Development Setup

* Run directly from repository location (`/mnt/d/github/quill/`)
* Use virtual environment in `.venv/`
* Models stored in `models/` subdirectory
* Config: `config.yaml` in repo root

```bash
# Development workflow
cd /mnt/d/github/quill
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m Quill
```

### Production Installation

**User directory structure:**
```
Windows: %APPDATA%\Quill\
Linux:   ~/.local/share/Quill/

├── models/           # Downloaded Whisper models
├── logs/            # Application logs
└── config.yaml      # User configuration
```

**Executable location:**
```
Windows: C:\Program Files\Quill\Quill.exe
Linux:   ~/.local/bin/Quill
```

**Auto-start:**
* Windows: Task Scheduler or registry Run key
* Linux: systemd user service or XDG autostart

### Packaging for Distribution

* Use `PyInstaller` to create single executable
* Bundle default config template
* First-run: Download selected model (or bundle `small` by default)
* Installer creates shortcuts and sets up auto-start

---

## 10. Deliverables for First Implementation Phase

1. ✅ Audio recording & chunking system
2. ✅ Faster-Whisper backend module
3. ✅ API endpoint backend option (OpenAI or custom)
4. ✅ Text injection module (active field typing)
5. ✅ Hotkey activation logic (push-to-talk or toggle)
6. ✅ Tray-first UI (pystray + state-based icon)
7. ✅ Native notification recording indicator
8. ✅ Configuration system (YAML + runtime reload)
9. ✅ Settings UI (tkinter-based, minimal)
10. ✅ Lazy-loading model system
11. ✅ Logging and error handling
12. ✅ Development + production deployment paths