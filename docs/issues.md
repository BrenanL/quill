# Quill: Known Issues & Future Considerations

## Platform-Specific Issues

### Linux Wayland Text Injection Not Supported

**Issue:** Text injection does not work on Wayland display server due to security restrictions.

**Context:**
- Wayland prevents applications from simulating keyboard input to other applications
- Standard libraries (xdotool, keyboard, pynput) all fail on Wayland
- Wayland is now default on Ubuntu 22.04+, Fedora 35+, and most modern Linux distributions

**Recommended Workaround:**
- Support clipboard-based fallback (copy text to clipboard, user pastes manually)
- Clearly document that X11 session is required for automatic text injection
- Add runtime detection and warning if Wayland is detected

**Status:** Deferred for future implementation
**Priority:** Medium (affects Linux users on modern distros)

**Possible Future Solutions:**
1. Implement as Wayland input method protocol (complex, compositor-specific)
2. Use AT-SPI accessibility APIs (complex, not universally supported)
3. Clipboard mode with optional auto-paste via special permissions
4. Focus on X11 support only, users who need this can switch sessions

---

## Runtime/Control Issues

### Emergency Stop Hotkey Infinite Loop

**Issue:** Emergency stop hotkey (Ctrl+Shift+Esc) triggers repeatedly in an infinite loop instead of cleanly stopping the application.

**Symptoms:**
- Console floods with: `WARNING | Quill.app:_on_emergency_stop:201 | Emergency stop triggered`
- Notifications spam repeatedly
- Ctrl+C does not work to stop the process
- Application becomes unresponsive

**Root Cause:**
- Hotkey listener likely not properly suppressing the key event
- Event handler may be re-triggering itself
- No debouncing or single-fire protection

**Workaround:** See docs/dev-troubleshooting.md for process management commands

**Required Fix:**
- Add debouncing to emergency stop handler (ignore repeated calls within 1 second)
- Implement proper shutdown sequence that exits the event loop
- Add Ctrl+C (SIGINT) handler for graceful shutdown

**Status:** Critical bug - must fix before v1
**Priority:** HIGH

---

## Deployment/Production Issues

### Update Mechanism

**Issue:** No defined strategy for distributing updates to users.

**Context:**
- PyInstaller bundles need full replacement (100-500MB download each time)
- No auto-update system planned
- Users won't know when updates are available

**Recommended Approach for Future:**
- Implement simple update checker (query GitHub releases API)
- Notify user in tray menu when update available
- Provide link to download page
- Consider delta updates or package manager integration later

**Status:** Deferred - manual updates for development phase
**Priority:** Low (single user for now)

---

### Error Recovery Strategy

**Issue:** No comprehensive error handling and recovery system defined.

**Context:**
- Production failures will occur: model corruption, GPU OOM, audio device disconnection, etc.
- Need graceful degradation rather than crashes
- Users need actionable error messages

**Required Components:**
- Model load failure → try fallback model or prompt user
- Audio device lost → pause gracefully, resume when available
- GPU OOM → unload model, clear queues, retry with smaller model
- Transcription timeout → kill thread, reload model
- Config file corruption → load defaults, warn user

**Status:** Critical for v1 - must implement basic error handling
**Priority:** High

---

### Telemetry/Analytics

**Issue:** No visibility into how the tool is being used or what issues users encounter.

**Context:**
- Can't measure performance in production
- Don't know which features are used
- Can't identify common error patterns

**Recommended Approach for Future:**
- Opt-in anonymous telemetry
- Track: platform, GPU availability, model choice, average transcription time, error types
- Privacy-preserving (no audio, no transcription content, no PII)

**Status:** Deferred - not needed for single-user development
**Priority:** Low (high when going multi-user)

---

### Logging Strategy

**Issue:** Need clear logging policy for debugging and monitoring.

**Requirements:**
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation to prevent disk fill
- Configurable log level in config
- Privacy: never log audio content or transcription text (unless explicitly enabled for debugging)
- Include performance metrics (transcription time, model load time, memory usage)

**Status:** Required for v1
**Priority:** High

---

## User Experience Issues

### First-Run Onboarding

**Issue:** Users will be lost without guidance on first run.

**Recommended Future Implementation:**
- First-run wizard that:
  - Explains how the tool works
  - Tests microphone access
  - Downloads initial model with progress bar
  - Tests recording and transcription
  - Confirms successful setup
- Sets up auto-start if desired
- Creates default config with sensible defaults

**Current Workaround:**
- Provide clear README with setup instructions
- Include example config.yaml with comments
- Document model download process

**Status:** Deferred - wizard not in MVP, config file only
**Priority:** High (for public release)

---

### Model Loading UX

**Issue:** 3-5 second model loading delay on first use with no feedback is poor UX.

**Implemented Solution:**
- Show clear message/notification: "Loading [model name] model..."
- Display progress bar during model download
- Pre-load model when hotkey is pressed (before recording starts)
- User sees feedback immediately, perceives shorter wait

**Status:** Required for v1
**Priority:** High

---

### Model Management

**Issue:** No UI for discovering, downloading, or managing Whisper models.

**Current Approach:**
- User selects model in config.yaml
- On first run with that model, system downloads it automatically
- Models stored in `models/` directory
- No UI for deletion or size management

**Future Enhancement:**
- Simple settings UI showing:
  - Available models (tiny/base/small/medium/large)
  - Download status and disk space used
  - One-click download/delete
  - Performance guidance (speed vs quality)

**Status:** Deferred - config-based for MVP
**Priority:** Medium

---

## Technical Debt

### PyInstaller Bundle Size

**Issue:** Distribution bundle will be 150-500MB (large for a "lightweight" tool).

**Context:**
- Python runtime: 15MB
- Dependencies (numpy, torch, etc.): 100-150MB
- Whisper model: 39MB-1.5GB (if bundled)

**Mitigation:**
- Don't bundle models in executable
- Lazy-load heavy dependencies
- Consider alternative packaging (conda, pip, platform packages)

**Status:** Acknowledged, acceptable for v1
**Priority:** Low

---

### Threading Model Complexity

**Issue:** Audio capture + transcription requires careful thread coordination.

**Risks:**
- GIL contention causing audio dropouts
- Queue overflow if transcription too slow
- Race conditions on model access

**Required Architecture:**
- Separate threads for: audio capture, processing, transcription, UI
- Bounded queues with back-pressure handling
- Thread-safe model access
- Proper cleanup on shutdown

**Status:** Must be designed correctly in v1
**Priority:** Critical

---

### GPU Dependency

**Issue:** Real-time feel requires GPU; CPU inference is 3-5x slower.

**Context:**
- Small model on GPU: ~0.8s for 5s audio (good)
- Small model on CPU: ~2.5s for 5s audio (acceptable)
- Medium model on CPU: ~5s for 5s audio (poor)

**Mitigation:**
- Auto-detect GPU availability
- Recommend appropriate model for hardware
- Warn user if no GPU detected and large model selected

**Status:** Acknowledged, document clearly
**Priority:** Medium

---

## Future Features (Backlog)

### Voice Commands
- "new line", "delete word", "undo", etc.
- Complex NLP required
- Language-specific
- High false-positive risk
**Priority:** Low - defer to v2+

### Streaming Transcription
- Real-time partial results
- More complex architecture
- Better UX but harder to implement
**Priority:** Medium - consider for v2

### Multi-Language Support
- Currently English-only assumed
- Whisper supports 99 languages
- Need UI for language selection
**Priority:** Low - English first

### Custom Vocabulary/Corrections
- User-defined word replacements
- Common error corrections
- Domain-specific terminology
**Priority:** Medium - useful for technical users

### API Backend Support
- OpenAI Whisper API
- Custom hosted models
- Requires API key management, network handling
**Priority:** Medium - defer until local works well

### macOS Support
- Different audio APIs
- Different text injection (Accessibility permissions required)
- Different tray implementation
**Priority:** Low - Windows/Linux first

---

## Security Considerations

### API Key Storage

**Issue:** API keys must not be stored in plaintext.

**Solution:** Use OS keyring
- Windows: Credential Manager
- Linux: Secret Service (gnome-keyring, kwallet)
- Python library: `keyring`

**Status:** Required if API backend implemented
**Priority:** High (when needed)

---

### YAML Loading

**Issue:** Unsafe YAML loading can execute arbitrary code.

**Solution:** Always use `yaml.safe_load()` not `yaml.load()`

**Status:** Required for v1
**Priority:** Critical

---

### Model Integrity

**Issue:** Downloaded models could be corrupted or malicious.

**Solution:**
- Verify SHA256 hash of downloaded models
- Use official HuggingFace model hub URLs only
- Warn if hash mismatch

**Status:** Required for v1
**Priority:** High

---

## Notes

This document tracks known limitations, deferred features, and technical debt. Items marked "Required for v1" must be addressed before initial release. Deferred items are documented for future consideration but not blocking.

**Last Updated:** 2025-01-13
