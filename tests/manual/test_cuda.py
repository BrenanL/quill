#!/usr/bin/env python3
"""
CUDA Test: Verify GPU acceleration works with faster-whisper.

Run standalone:
    python tests/manual/test_cuda.py

What this tests:
    1. NVIDIA DLLs can be found and loaded (Windows)
    2. ctranslate2 supports CUDA compute types
    3. faster-whisper can load a model on GPU
    4. GPU transcription works

Note: faster-whisper uses ctranslate2's CUDA backend, NOT PyTorch's.
      PyTorch CUDA is not required for GPU transcription.
"""

import os
import sys
import time
from pathlib import Path

# =============================================================================
# CUDA DLL Setup (must happen before importing ctranslate2/faster_whisper)
# =============================================================================

def setup_cuda_dlls() -> list[str]:
    """Add NVIDIA DLL directories to path on Windows. Returns paths added."""
    added_paths = []

    if sys.platform != "win32":
        print("[INFO] Not Windows, skipping DLL setup")
        return added_paths

    # Method 1: Direct import and find package path
    try:
        import nvidia.cudnn
        import nvidia.cublas

        # Get package paths - try __path__ for namespace packages, then __file__
        def get_package_bin(pkg):
            if hasattr(pkg, '__path__') and pkg.__path__:
                return Path(list(pkg.__path__)[0]) / "bin"
            elif hasattr(pkg, '__file__') and pkg.__file__:
                return Path(pkg.__file__).parent / "bin"
            return None

        cudnn_path = get_package_bin(nvidia.cudnn)
        cublas_path = get_package_bin(nvidia.cublas)

        if cudnn_path and cudnn_path.exists():
            os.add_dll_directory(str(cudnn_path))
            # Also add to PATH for DLLs loaded via LoadLibrary without SEARCH_USER_DIRS
            os.environ['PATH'] = str(cudnn_path) + os.pathsep + os.environ.get('PATH', '')
            added_paths.append(str(cudnn_path))
            print(f"[INFO] Added DLL directory: {cudnn_path}")

        if cublas_path and cublas_path.exists():
            os.add_dll_directory(str(cublas_path))
            os.environ['PATH'] = str(cublas_path) + os.pathsep + os.environ.get('PATH', '')
            added_paths.append(str(cublas_path))
            print(f"[INFO] Added DLL directory: {cublas_path}")

    except ImportError:
        print("[WARN] nvidia.cudnn/cublas packages not found")
        print("[HINT] Run: uv pip install nvidia-cudnn-cu12 nvidia-cublas-cu12")

    # Method 2: Fallback to site-packages search if nothing found yet
    if not added_paths:
        import site
        for site_dir in site.getsitepackages():
            nvidia_dir = Path(site_dir) / "nvidia"
            if nvidia_dir.exists():
                for subdir in ["cudnn", "cublas"]:
                    dll_path = nvidia_dir / subdir / "bin"
                    if dll_path.exists():
                        os.add_dll_directory(str(dll_path))
                        os.environ['PATH'] = str(dll_path) + os.pathsep + os.environ.get('PATH', '')
                        added_paths.append(str(dll_path))
                        print(f"[INFO] Added DLL directory (fallback): {dll_path}")

    if not added_paths:
        print("[WARN] No NVIDIA DLL directories found")
        print("[HINT] Run: uv pip install nvidia-cudnn-cu12 nvidia-cublas-cu12")

    return added_paths


# Setup DLLs before any CUDA imports
_dll_paths = setup_cuda_dlls()

# =============================================================================
# Now safe to import CUDA-dependent packages
# =============================================================================

import numpy as np

def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_result(success: bool, message: str) -> None:
    """Print a test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {message}")


def test_ctranslate2_cuda() -> bool:
    """Test that ctranslate2 supports CUDA compute types."""
    print_header("Test 1: ctranslate2 CUDA Support")

    try:
        import ctranslate2

        supported = ctranslate2.get_supported_compute_types('cuda')
        print(f"  Supported CUDA compute types: {supported}")

        if 'float16' in supported:
            print_result(True, "ctranslate2 supports CUDA float16")
            return True
        else:
            print_result(False, "float16 not in supported types")
            return False

    except Exception as e:
        print_result(False, f"Error: {e}")
        if "cudnn" in str(e).lower():
            print("[HINT] cuDNN DLLs not found - check DLL setup above")
        return False


def test_load_model_cuda(model_size: str = "tiny", compute_type: str = "float16"):
    """Test loading a model on CUDA. Returns model if successful, None otherwise."""
    print_header(f"Test 2: Load {model_size} model (CUDA, {compute_type})")

    try:
        from faster_whisper import WhisperModel

        print(f"  Loading model (may download on first run)...")
        start = time.time()

        model = WhisperModel(
            model_size,
            device="cuda",
            compute_type=compute_type,
            download_root="models",
        )

        elapsed = time.time() - start
        print_result(True, f"Model loaded in {elapsed:.1f}s")

        return model

    except Exception as e:
        print_result(False, f"Error: {e}")
        if "cudnn" in str(e).lower():
            print("[HINT] cuDNN DLLs not found. Ensure nvidia-cudnn-cu12 is installed")
            print("[HINT] and DLL paths are added before importing faster_whisper")
        return None


def test_transcribe_cuda(model) -> bool:
    """Test transcription on CUDA."""
    print_header("Test 3: Transcribe on CUDA")

    if model is None:
        print_result(False, "No model provided (previous test failed?)")
        return False

    try:
        # 3 seconds of 440Hz tone
        t = np.linspace(0, 3, 16000 * 3, dtype=np.float32)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        print("  Transcribing 3s of audio...")
        start = time.time()

        segments, info = model.transcribe(audio, language="en")
        segments_list = list(segments)

        elapsed = time.time() - start
        text = " ".join([seg.text for seg in segments_list]).strip()

        print_result(True, f"Transcription completed in {elapsed:.2f}s")
        print(f"  Segments: {len(segments_list)}")
        print(f"  Text: '{text[:100]}'" if text else "  Text: (empty)")

        return True

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False


def test_microphone_cuda(model_size: str = "small", duration: float = 5.0) -> bool:
    """Test live microphone recording with CUDA transcription."""
    print_header(f"Test: Live Microphone ({model_size} model, {duration}s)")

    try:
        import sounddevice as sd
        from faster_whisper import WhisperModel

        print(f"  Loading {model_size} model on CUDA...")
        model = WhisperModel(
            model_size,
            device="cuda",
            compute_type="float16",
            download_root="models",
        )
        print(f"  Model loaded.")

        # Wait for user to be ready
        input(f"\n  Press ENTER when ready to record {duration} seconds of speech...")
        print(f"\n  >>> RECORDING - SPEAK NOW <<<\n")
        audio = sd.rec(
            int(duration * 16000),
            samplerate=16000,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()  # Wait for recording to finish
        audio = audio.flatten()

        print(f"  Recording complete. Transcribing...")
        start = time.time()

        segments, info = model.transcribe(audio, language="en")
        segments_list = list(segments)

        elapsed = time.time() - start
        text = " ".join([seg.text for seg in segments_list]).strip()

        print_result(True, f"Transcription completed in {elapsed:.2f}s")
        print(f"\n  Transcribed text:")
        print(f"  \"{text}\"")

        del model
        return True

    except Exception as e:
        print_result(False, f"Error: {e}")
        return False


def test_model_sizes():
    """Test different model sizes on CUDA."""
    print_header("Test: Model Size Comparison")

    from faster_whisper import WhisperModel

    # 3 seconds of audio
    t = np.linspace(0, 3, 16000 * 3, dtype=np.float32)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    results = []

    for model_size in ["tiny", "base", "small"]:
        try:
            print(f"\n  Testing {model_size}...")

            load_start = time.time()
            model = WhisperModel(
                model_size,
                device="cuda",
                compute_type="float16",
                download_root="models",
            )
            load_time = time.time() - load_start

            trans_start = time.time()
            segments, _ = model.transcribe(audio, language="en")
            list(segments)  # Consume iterator
            trans_time = time.time() - trans_start

            results.append({
                "model": model_size,
                "load_time": load_time,
                "trans_time": trans_time,
            })

            print(f"    Load: {load_time:.1f}s, Transcribe: {trans_time:.2f}s")

            del model

        except Exception as e:
            print(f"    [FAIL] {model_size}: {e}")

    if results:
        print_result(True, f"Tested {len(results)} model sizes")
        return True
    else:
        print_result(False, "No models loaded successfully")
        return False


def run_all_tests() -> bool:
    """Run all CUDA tests."""
    print_header("CUDA TESTS FOR QUILL")
    print("Testing GPU acceleration with faster-whisper")
    print(f"DLL paths added: {len(_dll_paths)}")
    print("\nNote: faster-whisper uses ctranslate2 CUDA, not PyTorch CUDA")

    results = []

    # Test 1: ctranslate2 CUDA support
    results.append(("ctranslate2 CUDA", test_ctranslate2_cuda()))
    if not results[-1][1]:
        print("\n[ABORT] ctranslate2 CUDA not working, cannot continue")
        return False

    # Test 2: Load model
    model = test_load_model_cuda("tiny", "float16")
    results.append(("Load model CUDA", model is not None))

    if model is None:
        print("\n[ABORT] Cannot load model on CUDA, cannot continue")
        return False

    # Test 3: Transcribe
    results.append(("Transcribe CUDA", test_transcribe_cuda(model)))

    # Cleanup
    del model

    # Test 4: Model sizes (optional, slower)
    print("\n[INFO] Skipping model size comparison (run with --full for this)")

    # Summary
    print_header("SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] CUDA tests passed! GPU acceleration is working.")
        print("\nTo use CUDA in Quill, update config.yaml:")
        print("  transcription:")
        print("    device: cuda")
        print("    compute_type: float16")
        print("    model_size: small  # or medium for better accuracy")
        return True
    else:
        print("\n[FAILURE] Some CUDA tests failed.")
        return False


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python tests/manual/test_cuda.py [OPTIONS]")
        print("")
        print("Options:")
        print("  --mic          Run live microphone test with CUDA (small model, 5s)")
        print("  --mic-medium   Run live microphone test with medium model (better accuracy)")
        print("  --full         Run all tests including model size comparison")
        print("  -h, --help     Show this help message")
        sys.exit(0)

    if "--mic" in sys.argv:
        # Just run microphone test
        test_microphone_cuda(model_size="small", duration=5.0)
        sys.exit(0)

    if "--mic-medium" in sys.argv:
        # Microphone test with medium model for better accuracy
        test_microphone_cuda(model_size="medium", duration=5.0)
        sys.exit(0)

    if "--full" in sys.argv:
        # Run including model size comparison
        success = run_all_tests()
        if success:
            test_model_sizes()
        sys.exit(0 if success else 1)
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
