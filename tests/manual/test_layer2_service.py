#!/usr/bin/env python3
"""
Layer 2 Test: Verify Quill's TranscriptionService works.

This tests the Quill service layer that wraps Whisper.

Prerequisites:
    - Layer 1 tests pass (Whisper works directly)
    - config.yaml exists with CPU-compatible settings

Run standalone:
    python tests/manual/test_layer2_service.py

Run with pytest:
    pytest tests/manual/test_layer2_service.py -v -m manual --no-cov

What this tests:
    1. Config can be loaded
    2. TranscriptionService can be created
    3. Service can prepare (trigger model loading)
    4. Service can transcribe audio
    5. Service state management works
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


def ensure_cpu_config() -> None:
    """
    Ensure config.yaml has CPU-compatible settings.

    This modifies config.yaml if needed to use CPU + int8.
    """
    config_path = Path("config.yaml")

    if not config_path.exists():
        # Copy from example
        example_path = Path("config.example.yaml")
        if example_path.exists():
            config_path.write_text(example_path.read_text())
            print("Created config.yaml from config.example.yaml")
        else:
            raise FileNotFoundError("No config.yaml or config.example.yaml found")

    # Read and check/update config
    import yaml

    config = yaml.safe_load(config_path.read_text())

    modified = False

    # Ensure CPU-compatible settings
    if config.get("transcription", {}).get("device") != "cpu":
        config.setdefault("transcription", {})["device"] = "cpu"
        modified = True

    if config.get("transcription", {}).get("compute_type") != "int8":
        config.setdefault("transcription", {})["compute_type"] = "int8"
        modified = True

    # Use tiny model for faster testing
    if config.get("transcription", {}).get("model_size") != "tiny":
        config.setdefault("transcription", {})["model_size"] = "tiny"
        modified = True

    if modified:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("Updated config.yaml for CPU testing (device=cpu, compute_type=int8, model_size=tiny)")


class TestLayer2TranscriptionService:
    """
    Tests for Quill's TranscriptionService.

    These tests verify that the service layer works correctly.
    """

    def test_config_loads(self):
        """Test that configuration can be loaded."""
        print_header("Test 1: Load configuration")

        try:
            from Quill.config.manager import ConfigManager

            config = ConfigManager.load_with_defaults("config.yaml")

            print_result(True, "Configuration loaded successfully")
            print(f"  Model: {config.transcription.model_size}")
            print(f"  Device: {config.transcription.device}")
            print(f"  Compute type: {config.transcription.compute_type}")

            assert config is not None
            assert config.transcription.model_size in ["tiny", "base", "small", "medium", "large"]

        except Exception as e:
            print_result(False, f"Failed to load config: {e}")
            pytest.fail(str(e))

    def test_service_creation(self):
        """Test that TranscriptionService can be created."""
        print_header("Test 2: Create TranscriptionService")

        try:
            from Quill.config.manager import ConfigManager
            from Quill.transcription.service import TranscriptionService

            config = ConfigManager.load_with_defaults("config.yaml")
            service = TranscriptionService(config)

            print_result(True, "TranscriptionService created")
            print(f"  State: {service.state}")
            print(f"  Model loaded: {service.model_manager.is_loaded()}")

            assert service.state == "idle"
            assert not service.model_manager.is_loaded()

        except Exception as e:
            print_result(False, f"Failed to create service: {e}")
            pytest.fail(str(e))

    def test_service_prepare(self):
        """Test that service.prepare() triggers model loading."""
        print_header("Test 3: Service prepare (trigger model load)")

        try:
            from Quill.config.manager import ConfigManager
            from Quill.transcription.service import TranscriptionService

            config = ConfigManager.load_with_defaults("config.yaml")
            service = TranscriptionService(config)

            # Call prepare
            print("Calling service.prepare()...")
            status = service.prepare()

            print(f"  Prepare returned: {status}")
            assert status["status"] in ["loading", "ready"]

            # Wait for model to load
            print("Waiting for model to load...")
            max_wait = 60  # seconds
            waited = 0
            while service.state == "loading" and waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                if waited % 5 == 0:
                    print(f"  Still loading... ({waited}s)")

            print(f"  Final state: {service.state}")
            print(f"  Model loaded: {service.model_manager.is_loaded()}")

            if service.state == "ready":
                print_result(True, "Model loaded successfully")
            elif service.state == "error":
                print_result(False, "Model loading failed")
                pytest.fail("Service ended in error state")
            else:
                print_result(False, f"Unexpected state: {service.state}")
                pytest.fail(f"Unexpected state: {service.state}")

            # Cleanup
            service.shutdown()

        except Exception as e:
            print_result(False, f"Error during prepare: {e}")
            pytest.fail(str(e))

    def test_service_transcribe(self):
        """Test that service can transcribe audio."""
        print_header("Test 4: Service transcribe")

        try:
            from Quill.config.manager import ConfigManager
            from Quill.transcription.service import TranscriptionService

            config = ConfigManager.load_with_defaults("config.yaml")
            service = TranscriptionService(config)

            # Prepare and wait for model to be ready
            # Note: prepare() starts a background thread, so we need to wait
            # for state to become "ready" (not just wait while "loading")
            service.prepare()
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

            # Create test audio (random noise)
            audio = np.random.randn(16000 * 3).astype(np.float32) * 0.1
            print(f"Test audio: {len(audio)} samples ({len(audio)/16000:.1f}s)")

            # Transcribe
            print("Transcribing...")
            start = time.time()
            text = service.transcribe(audio)
            elapsed = time.time() - start

            print_result(True, f"Transcription completed in {elapsed:.2f}s")
            print(f"  Result: '{text[:100]}'" if text else "  Result: (empty)")

            # Random noise may or may not produce text, but should not crash
            assert isinstance(text, str)

            # Cleanup
            service.shutdown()

        except Exception as e:
            print_result(False, f"Transcription error: {e}")
            pytest.fail(str(e))

    def test_service_health_check(self):
        """Test service health check."""
        print_header("Test 5: Service health check")

        try:
            from Quill.config.manager import ConfigManager
            from Quill.transcription.service import TranscriptionService

            config = ConfigManager.load_with_defaults("config.yaml")
            service = TranscriptionService(config)

            # Health check before loading
            health = service.health_check()
            print(f"Health (before load): {health}")

            assert health["status"] == "ok"
            assert health["state"] == "idle"
            assert health["model_loaded"] is False

            # Prepare and wait for model to be ready
            service.prepare()
            max_wait = 60
            waited = 0
            while service.state not in ("ready", "error") and waited < max_wait:
                time.sleep(0.5)
                waited += 0.5

            # Health check after loading
            health = service.health_check()
            print(f"Health (after load): {health}")

            assert health["status"] == "ok"
            assert health["state"] == "ready"
            assert health["model_loaded"] is True

            print_result(True, "Health check works correctly")

            # Cleanup
            service.shutdown()

        except AssertionError as e:
            print_result(False, f"Health check assertion failed: {e}")
            pytest.fail(str(e))
        except Exception as e:
            print_result(False, f"Health check error: {e}")
            pytest.fail(str(e))


def run_all_tests() -> bool:
    """Run all tests and return success status."""
    print_header("LAYER 2: TRANSCRIPTION SERVICE TESTS")
    print("Testing Quill's TranscriptionService wrapper")
    print("This verifies the service layer works before testing the full app.")

    # Ensure config is set up for CPU testing
    try:
        ensure_cpu_config()
    except Exception as e:
        print(f"[ERROR] Could not set up config: {e}")
        return False

    test_instance = TestLayer2TranscriptionService()
    tests = [
        ("Load configuration", test_instance.test_config_loads),
        ("Create service", test_instance.test_service_creation),
        ("Service prepare", test_instance.test_service_prepare),
        ("Service transcribe", test_instance.test_service_transcribe),
        ("Service health check", test_instance.test_service_health_check),
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
            print(f"         Error: {error[:80]}...")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] Layer 2 tests passed! TranscriptionService is working.")
        print("You can proceed to Layer 3 tests (microphone + full integration).")
        return True
    else:
        print("\n[FAILURE] Some tests failed. Fix these before proceeding.")
        return False


if __name__ == "__main__":
    # When run as standalone script
    success = run_all_tests()
    sys.exit(0 if success else 1)
