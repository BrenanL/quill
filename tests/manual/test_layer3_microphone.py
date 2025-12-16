#!/usr/bin/env python3
"""
Layer 3 Test: Verify microphone recording + transcription works.

This is an INTERACTIVE test that requires:
    - A working microphone
    - You to speak when prompted

Prerequisites:
    - Layer 1 tests pass (Whisper works directly)
    - Layer 2 tests pass (TranscriptionService works)
    - Microphone is connected and working

Run standalone (recommended):
    python tests/manual/test_layer3_microphone.py

Run with pytest (will skip if no TTY):
    pytest tests/manual/test_layer3_microphone.py -v -m manual --no-cov -s

What this tests:
    1. Audio device can be detected
    2. Microphone can record audio
    3. Recorded audio can be transcribed
    4. Full pipeline: record -> transcribe -> output
"""

import sys
import time
from pathlib import Path

import pytest
import numpy as np

# Mark all tests in this module as manual
pytestmark = [pytest.mark.manual, pytest.mark.slow]


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_result(success: bool, message: str) -> None:
    """Print a test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {message}")


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty()


class TestLayer3Microphone:
    """
    Interactive tests with real microphone.

    These tests require user interaction (speaking into microphone).
    """

    def test_audio_device_available(self):
        """Test that an audio input device is available."""
        print_header("Test 1: Check audio devices")

        try:
            import sounddevice as sd

            devices = sd.query_devices()
            print(f"Found {len(devices)} audio devices")

            # Find input devices
            input_devices = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    input_devices.append((i, dev))
                    print(f"  [{i}] {dev['name']} (inputs: {dev['max_input_channels']})")

            if input_devices:
                print_result(True, f"Found {len(input_devices)} input device(s)")

                # Show default
                default_input = sd.query_devices(kind='input')
                print(f"\nDefault input: {default_input['name']}")
            else:
                print_result(False, "No input devices found")
                pytest.fail("No audio input devices available")

        except Exception as e:
            print_result(False, f"Error querying devices: {e}")
            pytest.fail(str(e))

    def test_record_audio_basic(self):
        """Test basic audio recording (3 seconds of whatever)."""
        print_header("Test 2: Basic audio recording")

        try:
            import sounddevice as sd

            duration = 3
            sample_rate = 16000

            print(f"Recording {duration} seconds...")
            print("(You can speak or stay silent - just testing recording works)")

            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()

            audio = audio.flatten()

            print(f"  Recorded {len(audio)} samples")
            print(f"  Duration: {len(audio)/sample_rate:.2f}s")
            print(f"  Peak amplitude: {np.max(np.abs(audio)):.4f}")
            print(f"  RMS level: {np.sqrt(np.mean(audio**2)):.4f}")

            # Check we got audio
            if np.max(np.abs(audio)) > 0:
                print_result(True, "Audio recorded successfully")
            else:
                print_result(False, "Audio is all zeros (microphone may be muted)")
                pytest.fail("No audio recorded")

        except Exception as e:
            print_result(False, f"Recording error: {e}")
            pytest.fail(str(e))

    def test_record_and_transcribe_interactive(self):
        """
        Interactive test: Record speech and transcribe it.

        This test prompts the user to speak and then transcribes.
        """
        print_header("Test 3: Record and transcribe (INTERACTIVE)")

        if not is_interactive():
            print("Skipping: Not running in interactive terminal")
            pytest.skip("Requires interactive terminal")

        try:
            import sounddevice as sd
            from faster_whisper import WhisperModel

            # Load model first (so user doesn't wait after speaking)
            print("Loading Whisper model (tiny, CPU)...")
            model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")
            print("Model loaded!\n")

            # Prompt user
            print("-" * 40)
            print("INSTRUCTIONS:")
            print("  1. Press ENTER when ready to record")
            print("  2. Speak clearly for 5 seconds")
            print("  3. Recording will stop automatically")
            print("-" * 40)

            input("\nPress ENTER to start recording...")

            # Record
            duration = 5
            sample_rate = 16000

            print(f"\n>>> RECORDING NOW - Speak for {duration} seconds! <<<\n")

            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()

            print(">>> Recording complete <<<\n")

            audio = audio.flatten()
            peak = np.max(np.abs(audio))
            rms = np.sqrt(np.mean(audio**2))

            print(f"Audio stats:")
            print(f"  Peak: {peak:.4f}")
            print(f"  RMS:  {rms:.4f}")

            if peak < 0.01:
                print("\n[WARNING] Audio level very low - mic may be muted or too quiet")

            # Transcribe
            print("\nTranscribing...")
            start = time.time()
            segments, info = model.transcribe(audio, language="en")
            text = " ".join([seg.text for seg in segments]).strip()
            elapsed = time.time() - start

            print(f"Transcription time: {elapsed:.2f}s")
            print(f"\n{'='*40}")
            print(f"TRANSCRIBED TEXT:")
            print(f"{'='*40}")
            print(text if text else "(no speech detected)")
            print(f"{'='*40}\n")

            if text:
                print_result(True, "Speech transcribed successfully")
            else:
                print("[INFO] No text transcribed. This could mean:")
                print("  - You didn't speak")
                print("  - Microphone volume too low")
                print("  - Speech was unclear")
                # Not a failure - empty result is valid

            del model

        except Exception as e:
            print_result(False, f"Error: {e}")
            pytest.fail(str(e))

    def test_full_pipeline_with_service(self):
        """
        Full pipeline test using Quill's TranscriptionService.

        This tests the actual code path that Quill uses.
        """
        print_header("Test 4: Full pipeline with TranscriptionService (INTERACTIVE)")

        if not is_interactive():
            print("Skipping: Not running in interactive terminal")
            pytest.skip("Requires interactive terminal")

        try:
            import sounddevice as sd
            from Quill.config.manager import ConfigManager
            from Quill.transcription.service import TranscriptionService

            # Load config and create service
            print("Loading config and creating service...")
            config = ConfigManager.load_with_defaults("config.yaml")

            # Override to use tiny/cpu for testing
            config.transcription.model_size = "tiny"
            config.transcription.device = "cpu"
            config.transcription.compute_type = "int8"

            service = TranscriptionService(config)

            # Prepare service (load model)
            print("Preparing service (loading model)...")
            service.prepare()

            # Wait for model to be ready
            # Note: prepare() starts a background thread, so we need to wait
            # for state to become "ready" (not just wait while "loading")
            max_wait = 60
            waited = 0
            while service.state not in ("ready", "error") and waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                if waited % 5 == 0:
                    print(f"  Waiting for model... state={service.state} ({waited}s)")

            if service.state != "ready":
                print_result(False, f"Service not ready: {service.state}")
                pytest.fail(f"Service not ready: {service.state}")

            print("Service ready!\n")

            # Prompt user
            print("-" * 40)
            print("INSTRUCTIONS:")
            print("  1. Press ENTER when ready to record")
            print("  2. Speak clearly for 5 seconds")
            print("  3. Recording will stop automatically")
            print("-" * 40)

            input("\nPress ENTER to start recording...")

            # Record
            duration = 5
            sample_rate = 16000

            print(f"\n>>> RECORDING NOW - Speak for {duration} seconds! <<<\n")

            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()

            print(">>> Recording complete <<<\n")

            audio = audio.flatten()

            # Transcribe using service
            print("Transcribing via TranscriptionService...")
            start = time.time()
            text = service.transcribe(audio)
            elapsed = time.time() - start

            print(f"Transcription time: {elapsed:.2f}s")
            print(f"\n{'='*40}")
            print(f"TRANSCRIBED TEXT:")
            print(f"{'='*40}")
            print(text if text else "(no speech detected)")
            print(f"{'='*40}\n")

            if text:
                print_result(True, "Full pipeline works!")
            else:
                print("[INFO] No text transcribed.")

            # Cleanup
            service.shutdown()

        except Exception as e:
            print_result(False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            pytest.fail(str(e))


def run_all_tests() -> bool:
    """Run all tests and return success status."""
    print_header("LAYER 3: MICROPHONE + TRANSCRIPTION TESTS")
    print("Testing real microphone recording with Whisper transcription")
    print("\nThis is an INTERACTIVE test - you will need to speak into your microphone!")

    if not is_interactive():
        print("\n[ERROR] This test requires an interactive terminal.")
        print("Run directly: python tests/manual/test_layer3_microphone.py")
        return False

    test_instance = TestLayer3Microphone()
    tests = [
        ("Audio devices available", test_instance.test_audio_device_available),
        ("Basic audio recording", test_instance.test_record_audio_basic),
        ("Record and transcribe (interactive)", test_instance.test_record_and_transcribe_interactive),
        ("Full pipeline with service (interactive)", test_instance.test_full_pipeline_with_service),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True, None))
        except pytest.skip.Exception as e:
            results.append((name, None, f"Skipped: {e}"))
        except Exception as e:
            results.append((name, False, str(e)))

    # Summary
    print_header("SUMMARY")
    passed = sum(1 for _, success, _ in results if success is True)
    failed = sum(1 for _, success, _ in results if success is False)
    skipped = sum(1 for _, success, _ in results if success is None)
    total = len(results)

    for name, success, error in results:
        if success is True:
            status = "[PASS]"
        elif success is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"  {status} {name}")
        if error and success is False:
            print(f"         Error: {error[:80]}...")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0:
        print("\n[SUCCESS] Layer 3 tests passed! Microphone + transcription working.")
        print("\nNext steps:")
        print("  - Try running the full app: python -m Quill")
        print("  - Press Ctrl+Shift+D to start/stop recording")
        return True
    else:
        print("\n[FAILURE] Some tests failed. Check microphone and configuration.")
        return False


if __name__ == "__main__":
    # When run as standalone script
    success = run_all_tests()
    sys.exit(0 if success else 1)
