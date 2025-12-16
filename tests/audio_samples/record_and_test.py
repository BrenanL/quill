#!/usr/bin/env python3
"""
Quick script to record audio and test Whisper transcription accuracy.

Usage:
    python tests/audio_samples/record_and_test.py
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone."""
    try:
        import sounddevice as sd
    except ImportError:
        print("Error: sounddevice not installed")
        print("Install: pip install sounddevice")
        return None

    print(f"\nRecording {duration} seconds of audio...")
    print("Speak clearly: Say a test phrase like:")
    print('  "The quick brown fox jumps over the lazy dog"')
    print("\nRecording in 3... 2... 1... GO!\n")

    # Record
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()

    print("✓ Recording complete!\n")
    return audio.flatten()


def transcribe_audio(audio, model_size="small"):
    """Transcribe audio using Whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("Error: faster-whisper not installed")
        print("Install: pip install faster-whisper")
        return None

    print(f"Loading Whisper '{model_size}' model...")
    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        download_root="models"
    )

    print("Transcribing...\n")
    segments, info = model.transcribe(audio, language="en")

    # Collect all text
    text_segments = []
    for segment in segments:
        text_segments.append(segment.text.strip())
        print(f"  [{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")

    full_text = " ".join(text_segments)
    return full_text


def save_audio(audio, filename, sample_rate=16000):
    """Save audio to WAV file."""
    try:
        import scipy.io.wavfile as wavfile
    except ImportError:
        print("Warning: scipy not installed, cannot save audio")
        return False

    filepath = Path(__file__).parent / filename
    wavfile.write(str(filepath), sample_rate, audio)
    print(f"\n✓ Audio saved to: {filepath}")
    return True


def main():
    """Main test function."""
    print("=" * 60)
    print("Whisper Transcription Accuracy Test")
    print("=" * 60)

    # Get user input
    print("\nWhat would you like to test?")
    print("1. Record and transcribe (5 seconds)")
    print("2. Record and transcribe (10 seconds)")
    print("3. Load existing audio file")

    choice = input("\nChoice (1-3): ").strip()

    if choice == "1":
        duration = 5
        audio = record_audio(duration=duration)
    elif choice == "2":
        duration = 10
        audio = record_audio(duration=duration)
    elif choice == "3":
        filename = input("Audio file path: ").strip()
        try:
            import soundfile as sf
            audio, sr = sf.read(filename)
            if sr != 16000:
                print(f"Resampling from {sr}Hz to 16000Hz...")
                from scipy import signal
                audio = signal.resample(audio, int(len(audio) * 16000 / sr))
        except Exception as e:
            print(f"Error loading audio: {e}")
            return
    else:
        print("Invalid choice")
        return

    if audio is None:
        return

    # Save the recording
    save = input("\nSave recording? (y/n): ").strip().lower()
    if save == 'y':
        filename = input("Filename (e.g., test_01.wav): ").strip()
        if not filename.endswith('.wav'):
            filename += '.wav'
        save_audio(audio, filename)

    # Transcribe
    model_size = input("\nModel size (tiny/base/small/medium/large) [small]: ").strip() or "small"

    transcription = transcribe_audio(audio, model_size=model_size)

    if transcription:
        print("\n" + "=" * 60)
        print("FINAL TRANSCRIPTION:")
        print("=" * 60)
        print(transcription)
        print("=" * 60)

        # Ask for expected text
        print("\nWhat did you actually say?")
        expected = input("Expected text: ").strip()

        if expected:
            # Simple accuracy check
            transcription_lower = transcription.lower()
            expected_lower = expected.lower()

            if transcription_lower == expected_lower:
                print("\n✓ PERFECT MATCH!")
            elif expected_lower in transcription_lower:
                print("\n✓ Expected text found in transcription")
            elif transcription_lower in expected_lower:
                print("\n✓ Transcription found in expected (may be truncated)")
            else:
                print("\n✗ Mismatch")
                print(f"  Expected: {expected}")
                print(f"  Got:      {transcription}")

                # Calculate simple word overlap
                expected_words = set(expected_lower.split())
                transcribed_words = set(transcription_lower.split())
                overlap = expected_words & transcribed_words
                accuracy = len(overlap) / max(len(expected_words), 1) * 100

                print(f"\n  Word overlap: {len(overlap)}/{len(expected_words)} ({accuracy:.1f}%)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
