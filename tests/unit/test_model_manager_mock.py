"""
Unit tests for ModelManager with mocked faster-whisper.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from Quill.transcription.model_manager import ModelManager
from Quill.utils.errors import ModelError

pytestmark = pytest.mark.unit


class TestModelManagerMocked:
    """Unit tests for ModelManager using mocked faster-whisper."""

    def test_init_with_config(self, mock_config, temp_models_dir):
        """Test initialization with configuration."""
        mock_config.transcription.model_size = "small"
        mock_config.transcription.device = "cpu"

        manager = ModelManager(models_dir=temp_models_dir)

        assert manager.current_model is None
        assert manager.model_size == "small"
        assert manager.device == "cpu"
        assert manager.models_dir == temp_models_dir

    def test_is_loaded_false_when_no_model(self, mock_config, temp_models_dir):
        """Test is_loaded() returns False when no model loaded."""
        manager = ModelManager(models_dir=temp_models_dir)

        assert manager.is_loaded() is False

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_is_loaded_true_when_model_loaded(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test is_loaded() returns True when model loaded."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        assert manager.is_loaded() is True

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_load_model_creates_whisper_model(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test that load_model() creates WhisperModel instance."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        # Verify WhisperModel was created with correct parameters
        mock_whisper_class.assert_called_once()
        call_args = mock_whisper_class.call_args

        assert call_args[0][0] == "small"  # model_size
        assert call_args[1]["device"] == "cpu"
        assert call_args[1]["compute_type"] == "int8"
        assert call_args[1]["download_root"] == str(temp_models_dir)

        assert manager.current_model is mock_model

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_load_model_with_different_sizes(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test loading different model sizes."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        for size in ["tiny", "base", "small", "medium", "large"]:
            mock_config.transcription.model_size = size
            manager = ModelManager(models_dir=temp_models_dir)
            manager.load_model()

            # Verify correct model size was used
            call_args = mock_whisper_class.call_args
            assert call_args[0][0] == size

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_load_model_with_cuda_device(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test loading model on CUDA device."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        mock_config.transcription.device = "cuda"
        mock_config.transcription.compute_type = "float16"

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        call_args = mock_whisper_class.call_args
        assert call_args[1]["device"] == "cuda"
        assert call_args[1]["compute_type"] == "float16"

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_load_model_twice_unloads_previous(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test that loading model twice unloads the previous one."""
        mock_model1 = Mock()
        mock_model2 = Mock()
        mock_whisper_class.side_effect = [mock_model1, mock_model2]

        manager = ModelManager(models_dir=temp_models_dir)

        # Load first model
        manager.load_model()
        assert manager.current_model is mock_model1

        # Load second model (should unload first)
        manager.load_model()
        assert manager.current_model is mock_model2

        # First model should be deleted (we can't really test this with mocks,
        # but we can verify it was replaced)
        assert manager.current_model is not mock_model1

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_unload_model_sets_to_none(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test that unload_model() sets current_model to None."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        assert manager.current_model is not None

        manager.unload_model()

        assert manager.current_model is None
        assert manager.is_loaded() is False

    @patch('Quill.transcription.model_manager.WhisperModel')
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.empty_cache')
    def test_unload_model_clears_cuda_cache(self, mock_empty_cache, mock_cuda_available,
                                             mock_whisper_class, mock_config, temp_models_dir):
        """Test that unload_model() clears CUDA cache if GPU was used."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model
        mock_cuda_available.return_value = True

        mock_config.transcription.device = "cuda"

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()
        manager.unload_model()

        # Should have cleared CUDA cache
        mock_empty_cache.assert_called_once()

    def test_unload_model_when_no_model_loaded(self, mock_config, temp_models_dir):
        """Test that unload_model() when no model loaded doesn't crash."""
        manager = ModelManager(models_dir=temp_models_dir)

        # Should not raise exception
        manager.unload_model()

        assert manager.current_model is None

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_transcribe_with_loaded_model(self, mock_whisper_class, mock_config,
                                          temp_models_dir, mock_audio_data):
        """Test transcription with loaded model."""
        # Setup mock model with transcribe method
        mock_model = Mock()
        segment1 = Mock()
        segment1.text = "Hello"
        segment2 = Mock()
        segment2.text = " world"
        info = Mock()
        info.language = "en"

        mock_model.transcribe.return_value = ([segment1, segment2], info)
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        text = manager.transcribe(mock_audio_data)

        assert text == "Hello world"
        mock_model.transcribe.assert_called_once_with(
            mock_audio_data,
            language="en"
        )

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_transcribe_without_model_raises_error(self, mock_whisper_class, mock_config,
                                                    temp_models_dir, mock_audio_data):
        """Test that transcribe() raises error if no model loaded."""
        manager = ModelManager(models_dir=temp_models_dir)

        with pytest.raises(ModelError, match="No model loaded"):
            manager.transcribe(mock_audio_data)

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_transcribe_with_empty_result(self, mock_whisper_class, mock_config,
                                          temp_models_dir, mock_audio_data):
        """Test transcription when model returns empty segments."""
        mock_model = Mock()
        info = Mock()
        info.language = "en"

        mock_model.transcribe.return_value = ([], info)  # No segments
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        text = manager.transcribe(mock_audio_data)

        assert text == ""

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_transcribe_strips_whitespace(self, mock_whisper_class, mock_config,
                                          temp_models_dir, mock_audio_data):
        """Test that transcription result is stripped of extra whitespace."""
        mock_model = Mock()
        segment = Mock()
        segment.text = "  Hello world  "
        info = Mock()

        mock_model.transcribe.return_value = ([segment], info)
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        text = manager.transcribe(mock_audio_data)

        assert text == "Hello world"

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_load_model_failure_raises_error(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test that model load failure raises appropriate error."""
        mock_whisper_class.side_effect = Exception("GPU out of memory")

        manager = ModelManager(models_dir=temp_models_dir)

        with pytest.raises(ModelError, match="Failed to load model"):
            manager.load_model()

    @patch('Quill.transcription.model_manager.WhisperModel')
    def test_get_model_info(self, mock_whisper_class, mock_config, temp_models_dir):
        """Test get_model_info() returns model information."""
        mock_model = Mock()
        mock_whisper_class.return_value = mock_model

        manager = ModelManager(models_dir=temp_models_dir)
        manager.load_model()

        info = manager.get_model_info()

        assert info["model_size"] == "small"
        assert info["device"] == "cpu"
        assert info["compute_type"] == "int8"
        assert info["loaded"] is True

    def test_get_model_info_when_not_loaded(self, mock_config, temp_models_dir):
        """Test get_model_info() when no model loaded."""
        manager = ModelManager(models_dir=temp_models_dir)

        info = manager.get_model_info()

        assert info["loaded"] is False
        assert info["model_size"] == "small"
        assert info["device"] == "cpu"
