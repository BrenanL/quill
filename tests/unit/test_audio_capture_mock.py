"""
Unit tests for AudioCapture with mocked sounddevice.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time

from Quill.audio.capture import AudioCapture

pytestmark = pytest.mark.unit


class TestAudioCaptureMocked:
    """Unit tests for AudioCapture using mocked sounddevice (fast)."""

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_init_with_default_params(self, mock_stream_class, mock_query_devices):
        """Test initialization with default parameters."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}

        capture = AudioCapture(sample_rate=16000, channels=1)

        assert capture.sample_rate == 16000
        assert capture.channels == 1
        assert capture.is_recording is False
        assert capture.buffer is not None

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_start_creates_stream(self, mock_stream_class, mock_query_devices):
        """Test that start() creates and starts a sounddevice stream."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        mock_instance = MagicMock()
        mock_stream_class.return_value = mock_instance

        capture = AudioCapture(sample_rate=16000, channels=1)
        capture.start()

        # Verify InputStream was created with correct parameters
        mock_stream_class.assert_called_once()
        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs['samplerate'] == 16000
        assert call_kwargs['channels'] == 1
        assert call_kwargs['dtype'] == np.float32

        # Verify stream was started
        mock_instance.start.assert_called_once()
        assert capture.is_recording is True

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stop_closes_stream(self, mock_stream_class, mock_query_devices):
        """Test that stop() closes the stream."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        mock_instance = MagicMock()
        mock_stream_class.return_value = mock_instance

        capture = AudioCapture(sample_rate=16000, channels=1)
        capture.start()
        # Add some data to buffer AFTER start() so stop() doesn't raise AudioCaptureError
        capture.buffer.put(np.ones(100, dtype=np.float32))
        audio = capture.stop()

        # Verify stream was stopped and closed
        mock_instance.stop.assert_called_once()
        mock_instance.close.assert_called_once()
        assert capture.is_recording is False
        # Verify stop() returns audio data
        assert isinstance(audio, np.ndarray)

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stop_without_start(self, mock_stream_class, mock_query_devices):
        """Test that stop() without start() doesn't crash."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        capture = AudioCapture(sample_rate=16000, channels=1)

        # Should not raise exception, returns empty array
        result = capture.stop()
        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_callback_appends_to_buffer(self, mock_stream_class, mock_query_devices):
        """Test that audio callback appends data to buffer."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        # Disable noise gate so audio is not modified
        capture = AudioCapture(sample_rate=16000, channels=1, noise_gate_threshold=0.0)
        capture.is_recording = True  # Enable recording so callback processes data

        # Simulate callback with audio data
        audio_chunk = np.random.randn(160).astype(np.float32)
        capture._audio_callback(audio_chunk, frames=160, time_info=None, status=None)

        # Buffer should have data
        assert not capture.buffer.empty()
        stored_chunks = capture.buffer.get_all()
        assert len(stored_chunks) == 1
        # With noise gate disabled, audio should match exactly
        np.testing.assert_array_equal(stored_chunks[0], audio_chunk)

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stop_concatenates_chunks(self, mock_stream_class, mock_query_devices):
        """Test that stop() returns concatenated audio from buffer."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        capture = AudioCapture(sample_rate=16000, channels=1)

        # Add multiple chunks to buffer
        chunk1 = np.ones(100, dtype=np.float32)
        chunk2 = np.ones(100, dtype=np.float32) * 2
        chunk3 = np.ones(100, dtype=np.float32) * 3

        capture.buffer.put(chunk1)
        capture.buffer.put(chunk2)
        capture.buffer.put(chunk3)

        # Simulate recording state
        capture.is_recording = True
        capture.stream = MagicMock()

        audio = capture.stop()

        # Should be concatenated
        assert len(audio) == 300
        np.testing.assert_array_equal(audio[:100], chunk1)
        np.testing.assert_array_equal(audio[100:200], chunk2)
        np.testing.assert_array_equal(audio[200:300], chunk3)

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stop_clears_buffer(self, mock_stream_class, mock_query_devices):
        """Test that stop() clears the buffer via get_all()."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        capture = AudioCapture(sample_rate=16000, channels=1)

        capture.buffer.put(np.ones(100, dtype=np.float32))

        # Simulate recording state
        capture.is_recording = True
        capture.stream = MagicMock()

        capture.stop()

        # Buffer should be empty (get_all() clears it)
        assert capture.buffer.empty()

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stop_with_empty_buffer_raises_error(self, mock_stream_class, mock_query_devices):
        """Test that stop() with empty buffer raises AudioCaptureError."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        capture = AudioCapture(sample_rate=16000, channels=1)

        # Simulate recording state with empty buffer
        capture.is_recording = True
        capture.stream = MagicMock()

        # Should raise error when no audio was recorded
        from Quill.utils.errors import AudioCaptureError
        with pytest.raises(AudioCaptureError, match="No audio data recorded"):
            capture.stop()

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_multiple_start_stop_cycles(self, mock_stream_class, mock_query_devices):
        """Test multiple start/stop cycles."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        mock_instance = MagicMock()
        mock_stream_class.return_value = mock_instance

        capture = AudioCapture(sample_rate=16000, channels=1)

        # First cycle
        capture.start()
        assert capture.is_recording is True
        capture.buffer.put(np.ones(100, dtype=np.float32))
        capture.stop()
        assert capture.is_recording is False

        # Second cycle (should work fine)
        capture.start()
        assert capture.is_recording is True
        capture.buffer.put(np.ones(100, dtype=np.float32))
        capture.stop()
        assert capture.is_recording is False

        # Verify stream was created twice
        assert mock_stream_class.call_count == 2

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_callback_handles_status_errors(self, mock_stream_class, mock_query_devices):
        """Test that callback logs status errors."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}
        capture = AudioCapture(sample_rate=16000, channels=1)
        capture.is_recording = True  # Enable recording

        # Simulate callback with error status
        audio_chunk = np.random.randn(160).astype(np.float32)
        status = Mock()
        status.__str__ = Mock(return_value="Input overflow")

        # Should not crash
        capture._audio_callback(audio_chunk, frames=160, time_info=None, status=status)

        # Data should still be buffered
        assert not capture.buffer.empty()

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_different_sample_rates(self, mock_stream_class, mock_query_devices):
        """Test initialization with different sample rates."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}

        # 16kHz (standard)
        capture1 = AudioCapture(sample_rate=16000, channels=1)
        assert capture1.sample_rate == 16000

        # 44.1kHz
        capture2 = AudioCapture(sample_rate=44100, channels=1)
        assert capture2.sample_rate == 44100

        # 48kHz
        capture3 = AudioCapture(sample_rate=48000, channels=1)
        assert capture3.sample_rate == 48000

    @patch('sounddevice.query_devices')
    @patch('sounddevice.InputStream')
    def test_stereo_vs_mono(self, mock_stream_class, mock_query_devices):
        """Test mono vs stereo channel configuration."""
        mock_query_devices.return_value = {'name': 'Mock Input Device', 'max_input_channels': 2}

        # Mono
        capture_mono = AudioCapture(sample_rate=16000, channels=1)
        assert capture_mono.channels == 1

        # Stereo
        capture_stereo = AudioCapture(sample_rate=16000, channels=2)
        assert capture_stereo.channels == 2
