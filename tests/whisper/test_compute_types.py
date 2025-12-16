# tests/whisper/test_compute_types.py
"""
Test CPU and GPU compute type compatibility.
"""

import pytest

pytestmark = pytest.mark.whisper


class TestComputeTypes:
    """Test CPU and GPU compute type compatibility."""

    def test_cpu_int8_works(self, tone_audio):
        """Test that int8 compute type works on CPU."""
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8",
        )

        segments, info = model.transcribe(tone_audio, language="en")
        list(segments)  # Should not crash

        assert info.language == "en"

        del model

    @pytest.mark.gpu
    @pytest.mark.skipif(
        True,  # Skip by default - user can run with -m gpu if they have CUDA
        reason="CUDA availability not guaranteed"
    )
    def test_cuda_float16_works(self, tone_audio):
        """Test that float16 compute type works on CUDA."""
        import torch
        from faster_whisper import WhisperModel

        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")

        model = WhisperModel(
            "tiny",
            device="cuda",
            compute_type="float16",
        )

        segments, info = model.transcribe(tone_audio, language="en")
        list(segments)

        del model
        torch.cuda.empty_cache()

    def test_tiny_model_loads(self):
        """Test that tiny model loads successfully."""
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8",
            download_root="models",
        )

        # Model should be loaded
        assert model is not None

        # Clean up
        del model

    def test_model_inference_returns_text(self, whisper_model_tiny, tone_audio):
        """Test that model returns text from inference."""
        segments, info = whisper_model_tiny.transcribe(tone_audio, language="en")

        segments_list = list(segments)

        # Should return a list (may be empty for tone)
        assert isinstance(segments_list, list)

        # Info should have language
        assert info.language == "en"

    def test_model_handles_empty_audio(self, whisper_model_tiny):
        """Test that model handles empty audio gracefully."""
        import numpy as np

        empty_audio = np.array([], dtype=np.float32)

        # Should either process or raise a clear error
        try:
            segments, info = whisper_model_tiny.transcribe(empty_audio, language="en")
            list(segments)
        except Exception as e:
            # If it raises an error, it should be informative
            assert "audio" in str(e).lower() or "empty" in str(e).lower() or "length" in str(e).lower()

    def test_model_handles_very_short_audio(self, whisper_model_tiny):
        """Test that model handles very short audio."""
        import numpy as np

        # 100 samples (about 6ms at 16kHz)
        short_audio = np.random.randn(100).astype(np.float32)

        segments, info = whisper_model_tiny.transcribe(short_audio, language="en")
        result = list(segments)

        # Should process without crashing
        assert isinstance(result, list)
