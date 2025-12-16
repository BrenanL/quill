# tests/whisper/conftest.py
"""
Session-scoped fixtures for real Whisper model testing.
"""

import pytest
import numpy as np
from pathlib import Path

@pytest.fixture(scope="session")
def whisper_model_small():
    """
    Load Whisper small model ONCE for entire test session.

    All tests marked with @pytest.mark.whisper share this model instance.
    This prevents loading the model 10+ times and wasting memory/time.

    Yields:
        WhisperModel: Loaded small model on CPU with int8 compute
    """
    from faster_whisper import WhisperModel

    print("\n[Session Setup] Loading Whisper small model (this may take 1-2 minutes)...")

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",  # CPU-compatible
        download_root="models",
    )

    print("[Session Setup] Whisper model loaded successfully")

    yield model

    print("\n[Session Teardown] Cleaning up Whisper model")
    del model

@pytest.fixture(scope="session")
def whisper_model_tiny():
    """
    Load Whisper tiny model ONCE for entire test session.

    Tiny model is faster for tests that don't need accuracy.
    """
    from faster_whisper import WhisperModel

    print("\n[Session Setup] Loading Whisper tiny model...")

    model = WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8",
        download_root="models",
    )

    yield model

    del model

@pytest.fixture(scope="session")
def test_audio_sample():
    """
    Reusable test audio data for Whisper tests.

    Generates 3 seconds of 440Hz tone at 16kHz.
    """
    duration = 3
    sample_rate = 16000
    frequency = 440

    t = np.linspace(0, duration, duration * sample_rate, dtype=np.float32)
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio

@pytest.fixture(scope="session")
def test_speech_audio():
    """
    Reusable speech-like test audio.

    Simulates speech with varying frequencies and amplitude modulation.
    """
    duration = 3
    sample_rate = 16000

    t = np.linspace(0, duration, duration * sample_rate, dtype=np.float32)

    # Mix multiple frequencies to simulate speech formants
    speech = (
        0.3 * np.sin(2 * np.pi * 250 * t) +  # F1
        0.3 * np.sin(2 * np.pi * 2500 * t) +  # F2
        0.2 * np.sin(2 * np.pi * 3500 * t)    # F3
    )

    # Add amplitude modulation (syllables)
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
    speech = speech * modulation

    return speech.astype(np.float32)
