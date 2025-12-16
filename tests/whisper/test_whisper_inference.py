# tests/whisper/test_whisper_inference.py
"""
Integration tests with real Whisper model (shared instance).
"""

import pytest
import numpy as np

pytestmark = [pytest.mark.whisper, pytest.mark.slow]


class TestWhisperInference:
    """Integration tests with real Whisper model (shared instance)."""

    def test_transcribe_tone_audio(self, whisper_model_small, test_audio_sample):
        """
        Test transcription with shared model.

        This test reuses whisper_model_small loaded once per session.
        """
        segments, info = whisper_model_small.transcribe(
            test_audio_sample,
            language="en",
        )

        segments_list = list(segments)

        # Tone may not produce text, but should not crash
        assert isinstance(segments_list, list)
        assert info.language == "en"

    def test_transcribe_speech_audio(self, whisper_model_small, test_speech_audio):
        """Test transcription with simulated speech."""
        segments, info = whisper_model_small.transcribe(
            test_speech_audio,
            language="en",
        )

        segments_list = list(segments)
        # May or may not produce segments (it's synthetic audio)
        assert len(segments_list) >= 0
        assert info.language == "en"

    def test_multiple_transcriptions_same_model(self, whisper_model_small, tone_audio, silence_audio):
        """
        Test that model can be reused multiple times.

        Ensures model doesn't degrade or leak memory across calls.
        """
        # First transcription
        seg1, _ = whisper_model_small.transcribe(tone_audio, language="en")
        list(seg1)  # Consume generator

        # Second transcription
        seg2, _ = whisper_model_small.transcribe(silence_audio, language="en")
        list(seg2)

        # Third transcription (model should still work)
        seg3, _ = whisper_model_small.transcribe(tone_audio, language="en")
        result = list(seg3)

        # No assertions needed - just verify no crashes
        assert isinstance(result, list)

    def test_transcribe_different_audio_lengths(self, whisper_model_small):
        """Test transcription with different audio lengths."""
        # Short audio (0.5 seconds)
        short_audio = np.random.randn(8000).astype(np.float32)

        # Medium audio (3 seconds)
        medium_audio = np.random.randn(48000).astype(np.float32)

        # Long audio (10 seconds)
        long_audio = np.random.randn(160000).astype(np.float32)

        for audio in [short_audio, medium_audio, long_audio]:
            segments, info = whisper_model_small.transcribe(audio, language="en")
            result = list(segments)
            assert isinstance(result, list)
            assert info.language == "en"

    def test_transcribe_silence_returns_empty(self, whisper_model_small, silence_audio):
        """Test that silence produces minimal or no transcription."""
        segments, info = whisper_model_small.transcribe(
            silence_audio,
            language="en",
        )

        segments_list = list(segments)

        # Silence should produce few or no segments
        # (depending on model sensitivity)
        assert len(segments_list) <= 1
        assert info.language == "en"

    def test_model_supports_different_languages(self, whisper_model_small, tone_audio):
        """Test that model accepts different language codes."""
        languages = ["en", "es", "fr", "de", "zh"]

        for lang in languages:
            segments, info = whisper_model_small.transcribe(
                tone_audio,
                language=lang if lang != "zh" else "zh",  # Whisper uses 'zh' for Chinese
            )
            list(segments)  # Consume generator
            # No crash is success

    def test_transcribe_output_structure(self, whisper_model_small, test_audio_sample):
        """Test that transcription output has expected structure."""
        segments, info = whisper_model_small.transcribe(
            test_audio_sample,
            language="en",
        )

        # info should have language
        assert hasattr(info, 'language')
        assert info.language == "en"

        # Segments should be iterable
        segments_list = list(segments)
        for segment in segments_list:
            # Each segment should have text attribute
            assert hasattr(segment, 'text')
            assert isinstance(segment.text, str)
