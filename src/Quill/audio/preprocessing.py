"""Audio preprocessing utilities."""

import numpy as np
from scipy import signal


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to target sample rate.

    Args:
        audio: Audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio
    """
    if orig_sr == target_sr:
        return audio

    # Calculate number of samples in resampled audio
    num_samples = int(len(audio) * target_sr / orig_sr)

    # Resample using scipy
    resampled = signal.resample(audio, num_samples)

    return resampled.astype(np.float32)


def apply_noise_gate(audio: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """
    Apply noise gate to audio (drop samples below threshold).

    Args:
        audio: Audio data
        threshold: Amplitude threshold (0.0 to 1.0)

    Returns:
        Audio with noise gate applied
    """
    if threshold <= 0.0:
        return audio

    # Get absolute values
    abs_audio = np.abs(audio)

    # Create mask for samples above threshold
    mask = abs_audio >= threshold

    # Apply mask
    gated = audio.copy()
    gated[~mask] = 0.0

    return gated


def convert_to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert stereo audio to mono.

    Args:
        audio: Audio data (can be 1D or 2D)

    Returns:
        Mono audio (1D array)
    """
    if audio.ndim == 1:
        return audio

    # Average channels
    return np.mean(audio, axis=1).astype(np.float32)


def normalize_audio(audio: np.ndarray, target_level: float = 0.9) -> np.ndarray:
    """
    Normalize audio to target level.

    Args:
        audio: Audio data
        target_level: Target peak level (0.0 to 1.0)

    Returns:
        Normalized audio
    """
    # Get peak level
    peak = np.max(np.abs(audio))

    if peak == 0.0:
        return audio

    # Calculate normalization factor
    factor = target_level / peak

    # Apply normalization
    return (audio * factor).astype(np.float32)
