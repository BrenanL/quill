# tests/integration/test_audio_pipeline.py
"""
Integration tests for audio capture and preprocessing pipeline.
"""

import pytest
import numpy as np
from Quill.audio.preprocessing import apply_noise_gate, convert_to_mono, normalize_audio, resample_audio

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestAudioPipeline:
    """Integration tests for audio capture and preprocessing."""

    def test_full_preprocessing_pipeline(self, tone_audio):
        """Test full audio preprocessing pipeline."""
        # Start with tone audio (1 second, 16kHz)
        audio = tone_audio

        # Apply preprocessing steps
        mono = convert_to_mono(audio)
        gated = apply_noise_gate(mono, threshold=0.01)
        normalized = normalize_audio(gated, target_level=0.8)

        # Verify output
        assert normalized.dtype == np.float32
        assert len(normalized) == len(audio)
        assert np.max(np.abs(normalized)) <= 1.0

    def test_resampling_workflow(self):
        """Test resampling from different sample rates."""
        # Create 44.1kHz audio
        duration = 1.0
        orig_sr = 44100
        target_sr = 16000

        t = np.linspace(0, duration, int(duration * orig_sr), dtype=np.float32)
        audio_44k = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Resample to 16kHz
        audio_16k = resample_audio(audio_44k, orig_sr=orig_sr, target_sr=target_sr)

        # Verify output
        expected_length = int(duration * target_sr)
        assert len(audio_16k) == expected_length
        assert audio_16k.dtype == np.float32

    def test_stereo_to_mono_conversion(self):
        """Test stereo to mono conversion."""
        # Create stereo audio (left=1.0, right=0.5)
        duration = 1.0
        sample_rate = 16000
        samples = int(duration * sample_rate)

        stereo = np.zeros((samples, 2), dtype=np.float32)
        stereo[:, 0] = 1.0  # Left channel
        stereo[:, 1] = 0.5  # Right channel

        # Convert to mono
        mono = convert_to_mono(stereo)

        # Should average channels
        assert mono.shape == (samples,)
        assert np.allclose(mono, 0.75)  # (1.0 + 0.5) / 2 = 0.75

    def test_noise_gate_removes_silence(self, silence_audio):
        """Test that noise gate removes silence."""
        # Create audio with silence and signal
        audio = np.concatenate([
            silence_audio[:8000],  # 0.5s silence
            np.ones(8000, dtype=np.float32) * 0.5  # 0.5s signal
        ])

        # Apply noise gate
        gated = apply_noise_gate(audio, threshold=0.1)

        # Silence should be zeroed
        assert np.all(gated[:8000] == 0.0)
        # Signal should remain
        assert np.all(gated[8000:] == 0.5)

    def test_normalization_preserves_zero(self):
        """Test that normalization of silence remains zero."""
        audio = np.zeros(16000, dtype=np.float32)

        normalized = normalize_audio(audio, target_level=0.9)

        # Should remain zero (avoid division by zero)
        assert np.all(normalized == 0.0)

    def test_pipeline_with_real_world_levels(self):
        """Test pipeline with realistic audio levels."""
        # Simulate quiet recording (low amplitude)
        quiet_audio = np.random.randn(16000).astype(np.float32) * 0.1

        # Process
        gated = apply_noise_gate(quiet_audio, threshold=0.01)
        normalized = normalize_audio(gated, target_level=0.8)

        # Should boost to target level
        peak = np.max(np.abs(normalized))
        assert peak > 0.5  # Should be boosted significantly
        assert peak <= 1.0  # But not clipped
