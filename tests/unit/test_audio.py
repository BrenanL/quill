"""Tests for audio capture and preprocessing."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from Quill.audio.preprocessing import (
    resample_audio,
    apply_noise_gate,
    convert_to_mono,
    normalize_audio,
)
from Quill.utils.threading import RingBuffer

pytestmark = pytest.mark.unit


class TestRingBuffer:
    """Test RingBuffer class."""

    def test_put_and_get(self):
        """Test basic put and get operations."""
        buffer = RingBuffer(maxsize=10)
        buffer.put("item1")
        buffer.put("item2")

        assert buffer.get() == "item1"
        assert buffer.get() == "item2"

    def test_get_all(self):
        """Test getting all items."""
        buffer = RingBuffer(maxsize=10)
        buffer.put("a")
        buffer.put("b")
        buffer.put("c")

        items = buffer.get_all()
        assert items == ["a", "b", "c"]
        assert buffer.empty()

    def test_clear(self):
        """Test clearing buffer."""
        buffer = RingBuffer(maxsize=10)
        buffer.put(1)
        buffer.put(2)
        buffer.clear()

        assert buffer.empty()


class TestPreprocessing:
    """Test audio preprocessing functions."""

    def test_apply_noise_gate(self):
        """Test noise gate application."""
        audio = np.array([0.5, 0.005, 0.8, 0.002, -0.6], dtype=np.float32)
        gated = apply_noise_gate(audio, threshold=0.01)

        assert gated[0] == 0.5  # Above threshold
        assert gated[1] == 0.0  # Below threshold
        assert gated[2] == 0.8  # Above threshold
        assert gated[3] == 0.0  # Below threshold
        assert gated[4] == -0.6  # Above threshold (absolute value)

    def test_convert_to_mono(self):
        """Test stereo to mono conversion."""
        # Mono input (should return unchanged)
        mono = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = convert_to_mono(mono)
        np.testing.assert_array_equal(result, mono)

        # Stereo input (should average channels)
        stereo = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        result = convert_to_mono(stereo)
        expected = np.array([1.5, 3.5, 5.5], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)

    def test_normalize_audio(self):
        """Test audio normalization."""
        audio = np.array([0.5, -0.3, 0.2], dtype=np.float32)
        normalized = normalize_audio(audio, target_level=0.9)

        # Peak should be at target level
        peak = np.max(np.abs(normalized))
        assert abs(peak - 0.9) < 0.01

    def test_resample_audio_same_rate(self):
        """Test resampling with same sample rate."""
        audio = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        resampled = resample_audio(audio, orig_sr=16000, target_sr=16000)

        np.testing.assert_array_equal(resampled, audio)
