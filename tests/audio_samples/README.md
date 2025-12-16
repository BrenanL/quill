# Test Audio Samples

This directory contains real audio files for testing Whisper transcription accuracy.

## Creating Test Audio

### Option 1: Record Your Own Voice

Record yourself saying a known phrase, then test transcription accuracy.

**Example phrases:**
- "The quick brown fox jumps over the lazy dog."
- "Testing Whisper transcription accuracy with real human speech."
- "This is a test recording for the Quill dictation application."

**Using Python to record:**

```python
import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np

# Settings
duration = 5  # seconds
sample_rate = 16000

print("Recording in 3... 2... 1...")
print("Speak now!")

# Record
audio = sd.rec(int(duration * sample_rate),
               samplerate=sample_rate,
               channels=1,
               dtype=np.float32)
sd.wait()  # Wait until recording is finished

print("Recording complete!")

# Save as WAV
wavfile.write('tests/audio_samples/test_speech_01.wav',
              sample_rate,
              audio)
```

### Option 2: Download Test Audio

Download free test audio from:
- LibriSpeech: https://www.openslr.org/12/
- Common Voice: https://commonvoice.mozilla.org/
- OpenSLR: https://www.openslr.org/

### Option 3: Use Text-to-Speech

Generate test audio with known text:

```python
# Example using pyttsx3 (if installed)
import pyttsx3

engine = pyttsx3.init()
engine.save_to_file(
    "The quick brown fox jumps over the lazy dog.",
    "tests/audio_samples/tts_test_01.wav"
)
engine.runAndWait()
```

## Testing Accuracy

Once you have audio files:

```python
# tests/whisper/test_accuracy.py
import pytest
from faster_whisper import WhisperModel
import soundfile as sf

pytestmark = [pytest.mark.whisper, pytest.mark.slow]

def test_transcription_accuracy():
    """Test transcription accuracy with real speech."""
    # Load audio
    audio, sr = sf.read('tests/audio_samples/test_speech_01.wav')

    # Expected transcription
    expected = "the quick brown fox jumps over the lazy dog"

    # Load model and transcribe
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, language="en")

    # Get transcription
    result = " ".join([seg.text.strip() for seg in segments]).lower()

    # Check similarity (you might want to use a better metric)
    assert expected in result or result in expected

    print(f"Expected: {expected}")
    print(f"Got:      {result}")
```

## Current Test Audio

The existing test fixtures generate **synthetic audio** (pure tones), not real speech:

- `tone_audio` - 440Hz sine wave (A note)
- `silence_audio` - Zeros (silence)
- `test_audio_sample` - 440Hz tone (3 seconds)
- `test_speech_audio` - Synthetic formants (NOT real speech)

**These synthetic samples test that Whisper:**
- Doesn't crash on various inputs
- Returns proper data structures
- Handles edge cases

**They do NOT test transcription accuracy** because they contain no actual speech.

## Gitignore

Audio files should be gitignored (they're large):

```gitignore
# In .gitignore
tests/audio_samples/*.wav
tests/audio_samples/*.mp3
tests/audio_samples/*.flac
!tests/audio_samples/README.md
```
