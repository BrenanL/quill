#!/usr/bin/env python3
"""
Full Pipeline Test: Test the complete hotkey → record → transcribe → inject flow.

This test simulates what the full app does, but step by step with clear
diagnostic output so we can see exactly where it fails.

Run standalone:
    python tests/manual/test_full_pipeline.py

What this tests:
    1. Hotkey registration works
    2. Audio capture works
    3. Transcription works
    4. Text injection works
    5. Full pipeline works together
"""

import sys
import time
import threading
import numpy as np

def print_header(text: str) -> None:
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_step(num: int, text: str) -> None:
    print(f"\n[Step {num}] {text}")

def print_result(success: bool, message: str) -> None:
    status = "[OK]  " if success else "[FAIL]"
    print(f"  {status} {message}")


def test_dependencies():
    """Test that all required dependencies are available."""
    print_header("DEPENDENCY CHECK")

    deps = {
        "keyboard": "Hotkey detection and text injection",
        "sounddevice": "Audio recording",
        "numpy": "Audio processing",
        "faster_whisper": "Speech transcription",
    }

    optional_deps = {
        "win10toast": "Windows notifications (optional)",
        "pyperclip": "Clipboard fallback (optional)",
    }

    all_ok = True

    print("\nRequired:")
    for module, desc in deps.items():
        try:
            __import__(module)
            print_result(True, f"{module} - {desc}")
        except ImportError as e:
            print_result(False, f"{module} - {desc} ({e})")
            all_ok = False

    print("\nOptional:")
    for module, desc in optional_deps.items():
        try:
            __import__(module)
            print_result(True, f"{module} - {desc}")
        except ImportError:
            print(f"  [SKIP] {module} - {desc} (not installed)")

    return all_ok


def test_hotkey_registration():
    """Test that hotkeys can be registered."""
    print_header("HOTKEY REGISTRATION TEST")

    import keyboard

    hotkey = "ctrl+shift+d"
    callback_fired = threading.Event()

    def on_hotkey():
        print("  >>> Hotkey callback fired! <<<")
        callback_fired.set()

    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
        print_result(True, f"Registered hotkey: {hotkey}")

        print(f"\n  Press {hotkey.upper()} within 10 seconds to test...")

        if callback_fired.wait(timeout=10):
            print_result(True, "Hotkey callback works!")
            keyboard.remove_hotkey(hotkey)
            return True
        else:
            print_result(False, "Hotkey not detected (timeout)")
            print("  Possible causes:")
            print("    - Need to run as Administrator")
            print("    - Another app using the same hotkey")
            print("    - keyboard library issue")
            keyboard.remove_hotkey(hotkey)
            return False

    except Exception as e:
        print_result(False, f"Failed to register hotkey: {e}")
        return False


def test_audio_capture():
    """Test audio capture."""
    print_header("AUDIO CAPTURE TEST")

    import sounddevice as sd

    duration = 3
    sample_rate = 16000

    print(f"  Recording {duration} seconds of audio...")
    print("  (Speak or make noise to verify it's capturing)")

    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        audio = audio.flatten()

        peak = np.max(np.abs(audio))
        rms = np.sqrt(np.mean(audio**2))

        print(f"  Samples: {len(audio)}")
        print(f"  Peak: {peak:.4f}")
        print(f"  RMS: {rms:.4f}")

        if peak > 0.01:
            print_result(True, "Audio captured successfully")
            return audio
        else:
            print_result(False, "Audio level very low (mic muted?)")
            return audio  # Return anyway for next test

    except Exception as e:
        print_result(False, f"Audio capture failed: {e}")
        return None


def test_transcription(audio: np.ndarray):
    """Test transcription."""
    print_header("TRANSCRIPTION TEST")

    if audio is None:
        print_result(False, "No audio to transcribe")
        return None

    from faster_whisper import WhisperModel

    print("  Loading Whisper model (tiny, CPU)...")

    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")
        print_result(True, "Model loaded")

        print("  Transcribing...")
        start = time.time()
        segments, info = model.transcribe(audio, language="en")
        text = " ".join([seg.text for seg in segments]).strip()
        elapsed = time.time() - start

        print(f"  Time: {elapsed:.2f}s")
        print(f"  Result: '{text[:100]}'" if text else "  Result: (empty)")

        if text:
            print_result(True, "Transcription successful")
        else:
            print("[INFO] No text transcribed (maybe silence)")

        del model
        return text

    except Exception as e:
        print_result(False, f"Transcription failed: {e}")
        return None


def test_text_injection(text: str = None):
    """Test text injection."""
    print_header("TEXT INJECTION TEST")

    if not text:
        text = "Hello from Quill test!"

    import keyboard

    print(f"  Will inject: '{text}'")
    print("\n  INSTRUCTIONS:")
    print("    1. Click on a text field (Notepad, browser, etc.)")
    print("    2. Press ENTER here when ready")
    print("    3. Watch text appear in the target window")

    input("\n  Press ENTER when ready...")

    print("\n  Injecting in 2 seconds...")
    time.sleep(2)

    try:
        keyboard.write(text, delay=0.01)
        print_result(True, f"Injected {len(text)} characters")
        return True

    except Exception as e:
        print_result(False, f"Injection failed: {e}")
        return False


def test_full_pipeline_interactive():
    """Test the complete pipeline with user interaction."""
    print_header("FULL PIPELINE TEST (INTERACTIVE)")

    print("\nThis test simulates the full Quill flow:")
    print("  1. Press hotkey to start recording")
    print("  2. Speak")
    print("  3. Press hotkey to stop")
    print("  4. Text gets transcribed and injected")

    print("\n" + "-" * 40)
    print("SETUP: Open a text editor (Notepad) and click in it")
    print("       Keep this console visible too")
    print("-" * 40)

    input("\nPress ENTER when ready to begin...")

    import keyboard
    import sounddevice as sd
    from faster_whisper import WhisperModel

    # State
    is_recording = False
    audio_chunks = []
    sample_rate = 16000
    stream = None

    # Load model first
    print("\nLoading Whisper model...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="models")
    print("[OK] Model ready")

    def audio_callback(indata, frames, time_info, status):
        if is_recording:
            audio_chunks.append(indata.copy())

    def on_hotkey():
        nonlocal is_recording, stream, audio_chunks

        if not is_recording:
            # Start recording
            print("\n>>> RECORDING STARTED - Speak now! <<<")
            audio_chunks = []
            is_recording = True

            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                callback=audio_callback,
                blocksize=int(sample_rate * 0.1),
                dtype='float32'
            )
            stream.start()

        else:
            # Stop recording
            print(">>> RECORDING STOPPED <<<")
            is_recording = False

            if stream:
                stream.stop()
                stream.close()

            if not audio_chunks:
                print("[ERROR] No audio captured")
                return

            # Concatenate audio
            audio = np.concatenate(audio_chunks).flatten()
            print(f"  Captured {len(audio)/sample_rate:.1f}s of audio")

            # Transcribe
            print("  Transcribing...")
            segments, info = model.transcribe(audio, language="en")
            text = " ".join([seg.text for seg in segments]).strip()

            print(f"  Result: '{text}'")

            if text:
                # Inject
                print("  Injecting text...")
                time.sleep(0.5)  # Small delay for focus
                keyboard.write(text, delay=0.01)
                print("[OK] Text injected!")
                test_complete.set()  # Signal test is done
            else:
                print("[INFO] No text to inject")
                test_complete.set()  # Still complete, just no text

    # Event to signal completion
    test_complete = threading.Event()

    # Register hotkey
    hotkey = "ctrl+shift+d"
    keyboard.add_hotkey(hotkey, on_hotkey)
    print(f"\nHotkey registered: {hotkey.upper()}")
    print("\nINSTRUCTIONS:")
    print(f"  1. Click in Notepad (or your text editor)")
    print(f"  2. Press {hotkey.upper()} to START recording")
    print(f"  3. Speak clearly")
    print(f"  4. Press {hotkey.upper()} to STOP and inject")

    try:
        # Wait for test to complete (or timeout after 2 minutes)
        if test_complete.wait(timeout=120):
            print("\n[OK] Pipeline test completed successfully!")
        else:
            print("\n[TIMEOUT] No recording completed within 2 minutes")
    except KeyboardInterrupt:
        print("\n\nTest ended by user")
    finally:
        keyboard.remove_hotkey(hotkey)
        del model


def main():
    print_header("QUILL FULL PIPELINE DIAGNOSTIC")
    print("This tool tests each component of the Quill pipeline")
    print("to identify exactly where issues occur.")

    # Step 1: Dependencies
    if not test_dependencies():
        print("\n[FATAL] Missing required dependencies. Install them first.")
        return False

    # Step 2: Hotkey
    print_step(1, "Testing hotkey registration...")
    if not test_hotkey_registration():
        print("\n[WARNING] Hotkey test failed, but continuing...")

    # Step 3: Audio
    print_step(2, "Testing audio capture...")
    audio = test_audio_capture()

    # Step 4: Transcription
    print_step(3, "Testing transcription...")
    text = test_transcription(audio)

    # Step 5: Text injection
    print_step(4, "Testing text injection...")
    test_text_injection(text if text else "Hello from Quill!")

    # Step 6: Full pipeline
    print_step(5, "Testing full interactive pipeline...")
    response = input("\nRun full interactive pipeline test? (y/n): ").strip().lower()
    if response == 'y':
        test_full_pipeline_interactive()

    print_header("DIAGNOSTIC COMPLETE")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
