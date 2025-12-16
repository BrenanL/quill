#!/usr/bin/env python3
"""
Layer 1 Test: Verify Whisper model loading and transcription works.

This is the most fundamental test - if this fails, nothing else will work.

Run standalone:
    python tests/manual/test_layer1_whisper.py

Run with pytest:
    pytest tests/manual/test_layer1_whisper.py -v -m manual --no-cov

What this tests:
    1. faster-whisper can be imported
    2. Model can be downloaded/loaded (tiny model for speed)
    3. Model can transcribe audio (synthetic audio)
    4. Output has expected structure
"""

import sys
import time
from pathlib import Path

import pytest
import numpy as np

# Mark all tests in this module as manual (excluded from regular pytest runs)
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


class TestLayer1WhisperDirect:
    """
    Direct tests of faster-whisper functionality.

    These tests verify that the Whisper library works correctly
    without any Quill code involved.
    """

    def test_import_faster_whisper(self):
        """Test that faster-whisper can be imported."""
        print_header("Test 1: Import faster-whisper")

        try:
            from faster_whisper import WhisperModel
            print_result(True, "faster-whisper imported successfully")
            assert True
        except ImportError as e:
            print_result(False, f"Failed to import: {e}")
            print("\nFix: pip install faster-whisper")
            pytest.fail(f"Cannot import faster-whisper: {e}")

    def test_load_tiny_model_cpu(self):
        """Test loading the tiny model on CPU with int8."""
        print_header("Test 2: Load tiny model (CPU, int8)")

        from faster_whisper import WhisperModel

        start = time.time()
        print("Loading model (this may download on first run)...")

        try:
            model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8",
                download_root="models",
            )
            elapsed = time.time() - start
            print_result(True, f"Model loaded in {elapsed:.1f}s")

            # Cleanup
            del model
            assert True

        except Exception as e:
            print_result(False, f"Failed to load model: {e}")
            pytest.fail(str(e))

    def test_transcribe_silence(self):
        """Test transcription with silence (should not crash)."""
        print_header("Test 3: Transcribe silence")

        from faster_whisper import WhisperModel

        model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")

        # 3 seconds of silence
        audio = np.zeros(16000 * 3, dtype=np.float32)

        try:
            segments, info = model.transcribe(audio, language="en")
            segments_list = list(segments)

            print_result(True, f"Transcription completed, {len(segments_list)} segments")
            print(f"  Language detected: {info.language}")

            assert info.language == "en"

        except Exception as e:
            print_result(False, f"Transcription failed: {e}")
            pytest.fail(str(e))
        finally:
            del model

    def test_transcribe_tone(self):
        """Test transcription with a tone (440Hz)."""
        print_header("Test 4: Transcribe 440Hz tone")

        from faster_whisper import WhisperModel

        model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")

        # 3 seconds of 440Hz tone
        t = np.linspace(0, 3, 16000 * 3, dtype=np.float32)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        try:
            start = time.time()
            segments, info = model.transcribe(audio, language="en")
            segments_list = list(segments)
            elapsed = time.time() - start

            text = " ".join([seg.text for seg in segments_list])

            print_result(True, f"Transcription completed in {elapsed:.2f}s")
            print(f"  Segments: {len(segments_list)}")
            print(f"  Text: '{text[:100]}'" if text else "  Text: (empty)")

            # Tone may or may not produce text, but should not crash
            assert True

        except Exception as e:
            print_result(False, f"Transcription failed: {e}")
            pytest.fail(str(e))
        finally:
            del model

    def test_transcribe_output_structure(self):
        """Test that transcription output has correct structure."""
        print_header("Test 5: Verify output structure")

        from faster_whisper import WhisperModel

        model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")

        # Random noise (more likely to produce segments than silence)
        audio = np.random.randn(16000 * 3).astype(np.float32) * 0.1

        try:
            segments, info = model.transcribe(audio, language="en")

            # Check info structure
            assert hasattr(info, 'language'), "info should have 'language' attribute"
            print_result(True, f"info.language = '{info.language}'")

            # Check segments structure
            segments_list = list(segments)
            for i, seg in enumerate(segments_list):
                assert hasattr(seg, 'text'), f"segment {i} should have 'text'"
                assert hasattr(seg, 'start'), f"segment {i} should have 'start'"
                assert hasattr(seg, 'end'), f"segment {i} should have 'end'"

            print_result(True, f"All {len(segments_list)} segments have correct structure")

        except AssertionError as e:
            print_result(False, str(e))
            pytest.fail(str(e))
        except Exception as e:
            print_result(False, f"Unexpected error: {e}")
            pytest.fail(str(e))
        finally:
            del model


def run_all_tests() -> bool:
    """Run all tests and return success status."""
    print_header("LAYER 1: WHISPER DIRECT TESTS")
    print("Testing faster-whisper library directly (no Quill code)")
    print("This verifies the foundation works before testing higher layers.")

    test_instance = TestLayer1WhisperDirect()
    tests = [
        ("Import faster-whisper", test_instance.test_import_faster_whisper),
        ("Load tiny model", test_instance.test_load_tiny_model_cpu),
        ("Transcribe silence", test_instance.test_transcribe_silence),
        ("Transcribe tone", test_instance.test_transcribe_tone),
        ("Output structure", test_instance.test_transcribe_output_structure),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))

    # Summary
    print_header("SUMMARY")
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, error in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")
        if error:
            print(f"         Error: {error[:50]}...")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] Layer 1 tests passed! Whisper is working correctly.")
        print("You can proceed to Layer 2 tests.")
        return True
    else:
        print("\n[FAILURE] Some tests failed. Fix these before proceeding.")
        return False


if __name__ == "__main__":
    # When run as standalone script
    success = run_all_tests()
    sys.exit(0 if success else 1)
