# Quill UI & Runtime Considerations
## Based on G-Helper Analysis

## Executive Summary

Quill aims to be a **lightweight, tray-based dictation tool** similar to how g-helper provides lightweight system control. However, there are critical differences in technology stack and target platforms that require careful architectural decisions.

---

## Key Differences: Quill vs G-Helper

| Aspect | G-Helper | Quill |
|--------|----------|-------------|
| **Language** | C# | Python 3.11+ |
| **UI Framework** | WinForms (.NET 8.0) | PyQt6 / Tauri (proposed) |
| **Platform** | Windows only | Windows + Linux |
| **Binary Size** | Single .exe (~few MB) | Python + dependencies (~100MB+) |
| **Startup Time** | <1 second | 2-5 seconds (Python interpreter) |
| **Native Feel** | Native Windows controls | Qt widgets (non-native) |
| **GPU Access** | Direct via .NET | Via CUDA/PyTorch bindings |

---

## Critical Implications for Quill

### 1. **Runtime Location & Installation**

**G-Helper Approach:**
- Single portable executable
- Can run from any location
- No installation required
- System tray icon appears instantly

**Quill Challenges:**
- Python + dependencies = larger footprint
- Whisper models = 100MB-3GB of files
- Virtual environment required
- Longer startup time

**Recommended Approach:**
```
Install Location Options:

Option A: Traditional Installation
├── C:\Program Files\Quill\
│   ├── Quill.exe (PyInstaller bundle)
│   ├── models\
│   │   ├── tiny.bin
│   │   ├── small.bin
│   │   └── medium.bin
│   └── config\
│       └── config.yaml

Option B: Portable (Like G-Helper)
├── Quill\
│   ├── Quill.exe
│   ├── models\
│   └── config.yaml

Option C: User Directory (Recommended for cross-platform)
├── ~/.local/share/Quill/  (Linux)
├── %APPDATA%\Quill\        (Windows)
│   ├── models\
│   ├── logs\
│   └── config.yaml
├── ~/.local/bin/Quill (symlink/launcher)
```

**Recommendation**: **Option C** - User directory installation
- Cross-platform compatible
- No admin rights required
- Easy updates
- Respects OS conventions

### 2. **UI Framework Choice Re-evaluation**

**PyQt6 Pros:**
- Cross-platform (Windows, Linux, macOS)
- Mature, well-documented
- Good system tray support
- Native-ish look with styling

**PyQt6 Cons:**
- **Heavy**: 50-100MB runtime
- **Startup overhead**: 1-3 second initial load
- **Not truly native**: Qt widgets, not OS widgets
- **Licensing**: GPL or commercial license required

**Alternative: Tauri**

**Tauri Pros:**
- Lightweight: ~3-5MB binary
- Uses OS webview (native)
- Modern UI (HTML/CSS/JS)
- Good tray support

**Tauri Cons:**
- Requires Rust + JavaScript knowledge
- More complex build process
- Python backend = IPC overhead
- Not "just Python"

**Alternative: Python + Native Tray Libraries**

**Minimal Approach:**
```
Core: Python backend (no GUI framework)
Tray: pystray (pure Python, tiny)
UI: Only when needed:
  - Lightweight web server + browser for settings
  - OR minimal tkinter for simple dialogs
  - OR system dialogs (file picker, etc.)
```

**Benefits:**
- Ultra-lightweight (<10MB)
- Fast startup (< 1 second)
- No heavy GUI framework
- Tray-first like g-helper

---

## 3. **Adapting G-Helper's Lightweight Philosophy**

### What We Can Adopt Directly

#### ✅ **Tray-First Design**
```
Startup Sequence:
1. Launch app → Show tray icon ONLY
2. No visible windows
3. Icon shows current state (idle/recording/processing)
4. Right-click → Quick actions menu
5. Left-click → Toggle recording OR show status
```

#### ✅ **Smart Positioning**
- Settings window appears bottom-right (like g-helper)
- Recording indicator as small overlay (like ToastForm)
- Auto-hide when focus lost

#### ✅ **State-Based Icon**
```python
Tray Icon States:
- 🎤 Gray: Idle, ready
- 🔴 Red: Recording
- ⚙️ Yellow: Processing
- ✅ Green: Text injected
- ⚠️ Orange: Error/warning
```

#### ✅ **Minimal UI Surface**
- Tray icon + context menu = primary interface
- Settings window = secondary (hidden by default)
- Recording indicator = tertiary (temporary overlay)

### What We Must Adapt

#### ⚠️ **Startup Time**
**G-Helper:** Instant (compiled binary)
**Quill Solution:**
- Background service model (always running)
- OR aggressive lazy loading
- OR keep in memory after first use

**Recommended: Persistent Background Service**
```
User logs in → Quill starts minimized
    ↓
Loads minimal tray UI (~200ms)
    ↓
Lazy-loads Whisper model on first use (~2-5s)
    ↓
Keeps model in memory for instant subsequent use
```

#### ⚠️ **Cross-Platform Tray**
**Windows:** Standard tray works well
**Linux:** Fragmented tray support
```
Linux Tray Options:
1. AppIndicator (Ubuntu/GNOME)
2. StatusNotifier (KDE)
3. Legacy X11 systray (deprecated)

Solution: Use pystray library
- Auto-detects platform
- Falls back gracefully
- Consistent API
```

#### ⚠️ **Native Feel**
**G-Helper:** Uses Windows DWM APIs for native look
**Quill:** Cannot use OS native controls easily from Python

**Solution:**
- Use OS-appropriate styling
- Minimal custom UI (avoid heavy theming)
- Respect system theme (dark/light mode)
- Keep it simple and functional

---

## 4. **Recording Indicator Design**

G-Helper uses `ToastForm` for OSD notifications. We should implement similar:

### Option A: Frameless Qt Window (if using PyQt6)
```python
class RecordingIndicator(QWidget):
    - Frameless, always-on-top
    - Semi-transparent background
    - Shows "🔴 Recording..." or waveform animation
    - Auto-hides when recording stops
    - Positioned near system tray
```

### Option B: Native OS Notifications
```python
Windows: Toast notification (Windows 10+)
Linux: D-Bus notifications (notify-send)

Pros: Truly native, zero UI code
Cons: Less control over appearance/positioning
```

### Option C: Overlay Window (Lightweight)
```python
Platform-specific overlay:
- Windows: Win32 layered window
- Linux: X11/Wayland overlay

Ultra-minimal, just an icon + text
No framework required
```

**Recommendation:** **Option B for v1**, **Option A for v2**
- Start with native notifications (easy, cross-platform)
- Upgrade to custom overlay later for better UX

---

## 5. **Performance Optimization Strategy**

### Challenge: Python is slower than C#
**Mitigation:**
1. **Keep core hot path in compiled code**
   - Audio capture: Native libraries (sounddevice → PortAudio)
   - Transcription: Faster-Whisper → C++/CUDA backend
   - Text injection: OS APIs via ctypes/pywin32

2. **Lazy loading**
   ```python
   Startup:
   - Load tray icon (fast)
   - Load config (fast)
   - Initialize hotkey listener (fast)

   First recording:
   - Load Whisper model (slow, but only once)
   - Initialize audio backend (medium)

   Subsequent recordings:
   - Already loaded, instant
   ```

3. **Memory residence**
   - Keep model loaded in memory
   - Don't reload on each use
   - Trade memory (1-5GB) for speed

4. **Async architecture**
   ```python
   Main thread: UI/tray
   Audio thread: Capture loop
   Transcription thread: Whisper processing
   Injection thread: Text output

   → Non-blocking, responsive UI
   ```

---

## 6. **Recommended Architecture Based on G-Helper Insights**

### Minimal Framework Approach (Recommended)

```
Core:
├── main.py (entry point, tray initialization)
├── audio_capture.py (sounddevice)
├── transcription.py (faster-whisper)
├── text_injector.py (platform-specific)
├── hotkey_listener.py (keyboard/pynput)
└── config_manager.py (ruamel.yaml)

UI Layer:
├── tray_icon.py (pystray - ultra lightweight)
├── recording_indicator.py (platform notifications)
└── settings_ui.py (optional: tkinter OR web-based)

Models:
└── models/ (downloaded Whisper models)

Config:
└── config.yaml
```

### Why This Beats PyQt6 for This Use Case

| Aspect | PyQt6 | Minimal Approach |
|--------|-------|------------------|
| Tray support | ✅ Excellent | ✅ Excellent (pystray) |
| Binary size | ❌ 50-100MB | ✅ 5-10MB |
| Startup time | ⚠️ 1-3s | ✅ <0.5s |
| Cross-platform | ✅ Yes | ✅ Yes |
| Settings UI | ✅ Rich widgets | ⚠️ Basic (but sufficient) |
| Memory usage | ❌ 50-100MB | ✅ 10-20MB |
| Complexity | ⚠️ Medium | ✅ Low |

---

## 7. **Revised UI Component Specifications**

### 7.1 System Tray Icon (Primary Interface)

**Implementation:** `pystray` library

```python
Features:
- Shows current state (idle/recording/processing)
- Left-click: Toggle recording (like g-helper toggle)
- Right-click: Context menu
  ├── Start/Stop Recording
  ├── Select Model (tiny/small/medium/large)
  ├── Settings
  ├── View Logs
  └── Exit

Icon variations:
- Microphone (gray) = Idle
- Microphone (red) = Recording
- Gear (yellow) = Processing
- Check (green) = Success flash
```

### 7.2 Recording Indicator (Temporary Overlay)

**Implementation:** Native OS notifications (Phase 1)

```python
Display:
- "🔴 Recording..." while active
- Brief "✅ Text inserted" on completion
- "⚠️ Error: [message]" on failure

Position:
- OS-determined (notification area)

Duration:
- Recording: Persistent while active
- Success: 2 seconds
- Error: 5 seconds
```

### 7.3 Settings Window (Secondary Interface)

**Implementation:** Tkinter (Phase 1) OR Web UI (Phase 2)

```python
Layout (Minimal):
┌─────────────────────────────────┐
│ Quill Settings            │
├─────────────────────────────────┤
│ Model: [small ▼]                │
│ Device: [cuda ▼]                │
│ Hotkey: [Ctrl+Shift+D] [Change] │
│ Mode: ( ) Push-to-talk          │
│       (•) Toggle                │
│                                 │
│ [Save]  [Cancel]                │
└─────────────────────────────────┘

Position:
- Bottom-right corner (like g-helper)
- Fixed size (no resize needed)
- Auto-hide on focus loss (300ms debounce)
```

---

## 8. **Cross-Platform Runtime Differences**

### Windows
```
Installation:
- %APPDATA%\Quill\
- Auto-start: Task Scheduler OR registry Run key

Tray:
- Standard Windows system tray
- WinAPI for text injection (pywin32)
- WASAPI for audio capture

Packaging:
- PyInstaller → single .exe
- Optional: NSIS installer
```

### Linux
```
Installation:
- ~/.local/share/Quill/
- Auto-start: systemd user service OR ~/.config/autostart/

Tray:
- AppIndicator (Ubuntu/GNOME)
- StatusNotifier (KDE)
- Fallback: pystray handles this

Text injection:
- xdotool (X11)
- ydotool (Wayland)
- uinput (universal but requires setup)

Packaging:
- PyInstaller → single binary
- OR: Python package + .desktop file
```

---

## 9. **Startup & Auto-Run Strategy**

### G-Helper Approach
- Single .exe in startup folder
- Instant launch
- No visible window

### Quill Approach

**Windows:**
```python
# Option 1: Task Scheduler (preferred)
- Most reliable
- Can set delay (e.g., start 30s after login)
- Respects user permissions

# Option 2: Registry Run key
- Instant startup
- Simpler but less control
```

**Linux:**
```bash
# systemd user service
~/.config/systemd/user/Quill.service

[Unit]
Description=Quill Dictation Service

[Service]
ExecStart=/home/user/.local/bin/Quill
Restart=on-failure

[Install]
WantedBy=default.target
```

**Both:**
- Start minimized (tray only)
- Load config immediately
- Defer model loading until first use

---

## 10. **Final Recommendations**

### Phase 1: MVP (Match G-Helper Philosophy)

1. **Ultra-minimal UI approach**
   - `pystray` for tray icon
   - Native OS notifications for recording indicator
   - Tkinter for settings (if needed) OR config file only

2. **Runtime model**
   - Background service (always running)
   - Lazy-load Whisper model on first use
   - Keep in memory afterward

3. **Installation**
   - User directory install (no admin)
   - Auto-start on login (optional)
   - Single executable via PyInstaller

4. **Platform priority**
   - Windows first (more straightforward tray)
   - Linux second (test on Ubuntu + KDE)

### Phase 2: Enhanced UX

1. **Custom recording overlay**
   - Frameless window near tray
   - Waveform visualization
   - Live transcription preview

2. **Web-based settings UI**
   - Local server (Flask/FastAPI)
   - Opens in default browser
   - Modern, responsive UI

3. **Advanced features**
   - Model auto-download
   - Cloud config sync
   - Voice commands ("new line", "delete word")

---

## 11. **Concrete Next Steps**

1. ✅ **Prototype tray icon** with `pystray`
   - Test on Windows + Linux
   - Verify icon states work
   - Test hotkey integration

2. ✅ **Implement minimal recording indicator**
   - Native notifications first
   - Verify cross-platform

3. ✅ **Build hotkey listener**
   - Test toggle vs push-to-talk
   - Ensure works when app in background

4. ✅ **Integrate Faster-Whisper**
   - Lazy loading test
   - Memory usage profiling
   - Speed benchmarks

5. ✅ **Package as single executable**
   - PyInstaller configuration
   - Test startup time
   - Measure binary size

---

## Conclusion

Quill can achieve g-helper's **lightweight, tray-first philosophy** despite being Python-based by:

1. **Avoiding heavy GUI frameworks** (PyQt6/Electron)
2. **Using minimal tray library** (pystray)
3. **Lazy-loading expensive resources** (Whisper models)
4. **Running as persistent background service** (like g-helper)
5. **Prioritizing startup speed** over UI richness

The key insight from g-helper: **"Lightweight" is about UX design and smart resource management**, not just the choice of language or framework.
