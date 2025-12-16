# Streaming Dictation Status Report
**Date:** 2025-12-16

## Current State

### What Works
- **Batch mode**: Hotkey → record → hotkey → transcribe all → inject
  - Accuracy is excellent
  - Implemented in `src/Quill/dictation.py` with `STREAMING_ENABLED = False`

- **Full pipeline test**: `tests/manual/test_full_pipeline.py` passes
- **All components functional**: hotkeys, audio capture, Whisper, text injection

### What Doesn't Work Well
- **Streaming mode** (`STREAMING_ENABLED = True`): Produces garbage/hallucinated text
- **Root cause**: Whisper needs minimum context (~5-10 seconds) for accuracy
- **Our simple RMS pause detector** creates tiny segments (0.5-2s) that Whisper hallucinates on

## Better Streaming Approach: VAD + Minimum Chunk Size

### The Problem with Simple RMS Detection
- Just checks amplitude threshold
- Detects every tiny pause as a segment break
- Results in segments too short for accurate transcription
- Whisper hallucinates "Thank you for watching" type filler

### Proposed Solution: Silero VAD + Minimum Duration

**Algorithm:**
```
1. Use Silero VAD to detect speech activity in real-time
2. Accumulate audio until BOTH conditions met:
   - VAD detects end of speech (natural pause)
   - At least MIN_CHUNK_SECONDS accumulated (e.g., 5-10s)
3. Transcribe the accumulated segment
4. Inject text immediately
5. Continue recording
6. If MAX_CHUNK_SECONDS reached (e.g., 30s), force transcribe
```

**Why Silero VAD over simple RMS:**
- Trained ML model, not just amplitude threshold
- Distinguishes speech from noise/breathing/background
- Well-tested by Silero team and used by faster-whisper internally
- Handles edge cases better (quiet speech, loud background)

### Recommended Configuration
```python
# Minimum chunk size for good accuracy
MIN_CHUNK_SECONDS = 5      # Don't transcribe less than this
IDEAL_CHUNK_SECONDS = 10   # Target chunk size when pause detected
MAX_CHUNK_SECONDS = 30     # Force chunk even without pause

# Model recommendations for streaming
MODEL_SIZE = "base"        # Better than "tiny" for shorter segments
# Or "small" if latency allows
```

### Why Not "tiny" Model for Streaming?
- "tiny" is optimized for speed, not accuracy on short clips
- "base" or "small" handles shorter segments better
- Trade-off: slightly longer transcription time vs much better accuracy

## Implementation Steps

### Step 1: Add Silero VAD dependency
```bash
pip install silero-vad
# Or: add to pyproject.toml
```

### Step 2: Create VAD-based pause detector
Replace simple RMS detector with Silero VAD:

```python
# src/Quill/audio/vad_detector.py
import torch
from silero_vad import load_silero_vad, get_speech_timestamps

class VADDetector:
    def __init__(self, min_chunk_s=5, max_chunk_s=30):
        self.model = load_silero_vad()
        self.min_chunk_samples = 16000 * min_chunk_s
        self.max_chunk_samples = 16000 * max_chunk_s
        self.buffer = []
        self.total_samples = 0

    def process_chunk(self, audio_chunk):
        self.buffer.append(audio_chunk)
        self.total_samples += len(audio_chunk)

        # Check if we have enough audio
        if self.total_samples < self.min_chunk_samples:
            return None

        # Check VAD for speech end
        audio = np.concatenate(self.buffer)
        speech_timestamps = get_speech_timestamps(
            torch.from_numpy(audio),
            self.model
        )

        # If speech ended and we have minimum duration
        if self._speech_ended(speech_timestamps, audio):
            segment = audio
            self.buffer = []
            self.total_samples = 0
            return segment

        # Force chunk if max duration reached
        if self.total_samples >= self.max_chunk_samples:
            segment = np.concatenate(self.buffer)
            self.buffer = []
            self.total_samples = 0
            return segment

        return None
```

### Step 3: Update dictation.py
- Import VADDetector instead of PauseDetector
- Update config defaults for minimum chunk size
- Consider using "base" model instead of "tiny"

### Step 4: Add config options
```yaml
# config.yaml additions
streaming:
  enabled: true
  min_chunk_seconds: 5
  max_chunk_seconds: 30
  model_size: "base"  # Better for streaming
  vad_threshold: 0.5  # Silero VAD sensitivity
```

## Future Improvements

### Short-term
- [x] Implement Silero VAD streaming
- [x] Test with "base" and "small" models
- [x] Find optimal min_chunk_seconds for UX vs accuracy
- [x] Add GPU support for faster transcription

### Medium-term
- [ ] Overlapping chunks with context (better accuracy at boundaries)
- [ ] Confidence-based retry (re-transcribe if low confidence)
- [ ] Speaker diarization (who's speaking)
- [ ] Punctuation/formatting improvements

### Long-term
- [ ] Real-time streaming ASR (not Whisper - OpenAI Realtime API, Deepgram, etc.)
- [ ] Local real-time models (whisper.cpp streaming, Vosk)
- [ ] Wake word detection
- [ ] Voice commands

## Files Modified This Session

| File | Status | Description |
|------|--------|-------------|
| `src/Quill/dictation.py` | Created | Simple dictation service with batch/streaming modes |
| `tests/manual/test_full_pipeline.py` | Created | Full pipeline diagnostic test |
| `tests/manual/test_layer1_whisper.py` | Created | Whisper direct tests |
| `tests/manual/test_layer2_service.py` | Created | TranscriptionService tests |
| `tests/manual/test_layer3_microphone.py` | Created | Microphone + transcription tests |
| `pytest.ini` | Modified | Added `manual` marker |

## How to Continue

1. **Test batch mode thoroughly** - ensure it's production-ready
2. **Implement VAD-based streaming** - follow steps above
3. **Tune parameters** - find sweet spot for min_chunk_seconds
4. **Consider model upgrade** - "base" or "small" for streaming

## Commands Reference

```bash
# Run dictation service (batch mode - works well)
python -m Quill.dictation

# Run full pipeline test
python tests/manual/test_full_pipeline.py

# Run layer tests
python tests/manual/test_layer1_whisper.py
python tests/manual/test_layer2_service.py
python tests/manual/test_layer3_microphone.py

# Run regular pytest suite (excludes manual tests)
pytest
```

---

## Update: Implementation Complete

**Date:** 2025-12-16 (later same day)

The proposed Silero VAD solution was implemented and is working. Additional features were added:

### What Was Implemented
1. **Silero VAD integration** - `src/Quill/audio/vad_detector.py` processes audio in 512-sample chunks as required by Silero
2. **Minimum chunk duration** - 5 seconds minimum before transcribing (configurable)
3. **GPU auto-detection** - automatically uses CUDA if available, falls back to CPU with appropriate compute type
4. **Text normalization** - proper spacing between chunks (adds space after `.!?,;:` and between words)
5. **Auto-stop on silence** - recording stops after 20s of no speech (configurable)
6. **Config file support** - settings loaded from `config.yaml` with sensible defaults

### Additional Files Created
| File | Description |
|------|-------------|
| `src/Quill/audio/vad_detector.py` | Silero VAD detector with 512-sample chunk processing |
| `start-quill.ps1` | PowerShell startup script |
| `config.example.yaml` | Added `dictation:` section |
| `README.md` | Added "Dictation Service" section |

### Current Configuration Defaults
```yaml
dictation:
  streaming_enabled: true
  min_chunk_seconds: 5.0
  max_chunk_seconds: 30.0
  vad_threshold: 0.5
  min_silence_ms: 700
  auto_stop_silence_seconds: 20
```

### Known Working
- Streaming mode with VAD produces accurate transcription
- Text joins properly between chunks
- Auto-stop prevents forgotten recordings
- Works on both CPU (int8) and GPU (float16)
