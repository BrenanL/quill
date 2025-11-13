"""Abstract transcription engine interface."""

from abc import ABC, abstractmethod
import numpy as np


class TranscriptionEngine(ABC):
    """Abstract base class for transcription engines."""

    @abstractmethod
    def load_model(self, model_size: str, device: str = "cuda") -> None:
        """
        Load transcription model.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            device: Device to load on (cuda, cpu)
        """
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Unload model and free memory."""
        pass

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data (numpy array)

        Returns:
            Transcribed text
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        pass
