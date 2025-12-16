# tests/manual/__init__.py
"""
Manual/interactive tests for verifying Quill functionality.

These tests are designed to be run standalone (not as part of the regular pytest suite)
to verify that components work with real hardware and models.

Run individual tests:
    python tests/manual/test_layer1_whisper.py
    python tests/manual/test_layer2_service.py
    python tests/manual/test_layer3_microphone.py

Or run with pytest (explicitly):
    pytest tests/manual/ -v -m manual --no-cov
"""
