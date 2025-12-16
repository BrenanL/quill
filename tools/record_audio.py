#!/usr/bin/env python3
"""
Simple audio recording script for testing Whisper transcription.

Records audio from the default microphone and saves to a WAV file.

Usage:
    python tools/record_audio.py output.wav
    python tools/record_audio.py path/to/output.wav
    python tools/record_audio.py output.wav --duration 10
    python tools/record_audio.py output.wav --sample-rate 44100
"""

import sys
import argparse
from pathlib import Path
import numpy as np


def record_audio(duration=5, sample_rate=16000):
    """
    Record audio from default microphone.

    Args:
        duration: Recording duration in seconds
        sample_rate: Sample rate in Hz (default 16000 for Whisper)

    Returns:
        numpy array of audio samples, or None on error
    """
    try:
        import sounddevice as sd
    except ImportError:
        print("Error: sounddevice not installed")
        print("Install: pip install sounddevice")
        return None

    print(f"\nRecording {duration} seconds at {sample_rate}Hz...")
    print("Recording in 3... 2... 1... GO!\n")

    try:
        # Record audio
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()  # Wait until recording is finished

        print("✓ Recording complete!\n")
        return audio.flatten()

    except Exception as e:
        print(f"Error during recording: {e}")
        return None


def save_audio(audio, filepath, sample_rate=16000):
    """
    Save audio to WAV file.

    Args:
        audio: numpy array of audio samples
        filepath: Output file path
        sample_rate: Sample rate in Hz

    Returns:
        True on success, False on error
    """
    try:
        import scipy.io.wavfile as wavfile
    except ImportError:
        print("Error: scipy not installed")
        print("Install: pip install scipy")
        return False

    try:
        # Create parent directory if it doesn't exist
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save audio
        wavfile.write(str(filepath), sample_rate, audio)

        print(f"✓ Audio saved to: {filepath}")
        print(f"  Duration: {len(audio) / sample_rate:.2f} seconds")
        print(f"  Sample rate: {sample_rate} Hz")
        print(f"  File size: {filepath.stat().st_size / 1024:.1f} KB")

        return True

    except Exception as e:
        print(f"Error saving audio: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Record audio from microphone and save to WAV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record 5 seconds to output.wav (16kHz, default for Whisper)
  python tools/record_audio.py output.wav

  # Record 10 seconds
  python tools/record_audio.py output.wav --duration 10

  # Record at 44.1kHz sample rate
  python tools/record_audio.py output.wav --sample-rate 44100

  # Save to subdirectory
  python tools/record_audio.py test_recordings/test_01.wav
        """
    )

    parser.add_argument(
        'output',
        help='Output WAV file path (e.g., output.wav or path/to/file.wav)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=5.0,
        help='Recording duration in seconds (default: 5)'
    )
    parser.add_argument(
        '--sample-rate', '-sr',
        type=int,
        default=16000,
        help='Sample rate in Hz (default: 16000, recommended for Whisper)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.duration <= 0:
        print("Error: Duration must be positive")
        sys.exit(1)

    if args.sample_rate < 8000 or args.sample_rate > 48000:
        print("Warning: Sample rate should typically be between 8000 and 48000 Hz")

    # Check output path
    output_path = Path(args.output)
    if output_path.suffix.lower() != '.wav':
        print("Warning: Output file should have .wav extension")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborted")
            sys.exit(0)

    # Check if file exists
    if output_path.exists():
        print(f"Warning: File already exists: {output_path}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborted")
            sys.exit(0)

    # Record audio
    print("=" * 60)
    print("Audio Recording")
    print("=" * 60)

    audio = record_audio(duration=args.duration, sample_rate=args.sample_rate)

    if audio is None:
        print("\nRecording failed")
        sys.exit(1)

    # Save audio
    success = save_audio(audio, output_path, sample_rate=args.sample_rate)

    if success:
        print("\n✓ Success!")
        print(f"\nTo transcribe with Whisper:")
        print(f"  python -c \"")
        print(f"from faster_whisper import WhisperModel")
        print(f"import soundfile as sf")
        print(f"audio, sr = sf.read('{output_path}')")
        print(f"model = WhisperModel('small', device='cpu', compute_type='int8')")
        print(f"segments, info = model.transcribe(audio, language='en')")
        print(f"for seg in segments: print(seg.text)")
        print(f"\"")
    else:
        print("\nSaving failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
