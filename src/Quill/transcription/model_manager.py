"""Model download and management."""

from pathlib import Path
from typing import Optional
from loguru import logger

from ..utils.errors import ModelError


class ModelManager:
    """Manages Whisper model download, verification, and loading."""

    def __init__(self, models_dir: str | Path = "models"):
        """
        Initialize model manager.

        Args:
            models_dir: Directory to store models
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.current_model = None
        self.current_size = None
        self.current_device = None

    def get_model_path(self, model_size: str) -> Path:
        """
        Get path for model.

        Args:
            model_size: Model size

        Returns:
            Path to model directory
        """
        return self.models_dir / f"whisper-{model_size}"

    def is_model_downloaded(self, model_size: str) -> bool:
        """
        Check if model is downloaded.

        Args:
            model_size: Model size

        Returns:
            True if model exists locally
        """
        model_path = self.get_model_path(model_size)
        return model_path.exists() and any(model_path.iterdir())

    def download_model(self, model_size: str) -> Path:
        """
        Download model if not present.

        Args:
            model_size: Model size

        Returns:
            Path to model

        Raises:
            ModelError: If download fails
        """
        if self.is_model_downloaded(model_size):
            logger.info(f"Model {model_size} already downloaded")
            return self.get_model_path(model_size)

        try:
            logger.info(f"Downloading {model_size} model (this may take a while)...")

            # Note: faster-whisper will auto-download on first use
            # We just ensure the directory exists
            model_path = self.get_model_path(model_size)
            model_path.mkdir(parents=True, exist_ok=True)

            return model_path

        except Exception as e:
            raise ModelError(f"Failed to download model {model_size}: {e}")

    def load_model(self, model_size: str, device: str = "cuda", compute_type: str = "float16"):
        """
        Load model.

        Args:
            model_size: Model size
            device: Device (cuda/cpu)
            compute_type: Compute type

        Returns:
            Loaded model

        Raises:
            ModelError: If load fails
        """
        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading {model_size} model on {device}...")

            # Load model (faster-whisper handles download)
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(self.models_dir),
            )

            self.current_model = model
            self.current_size = model_size
            self.current_device = device

            logger.info(f"Model {model_size} loaded successfully")

            return model

        except Exception as e:
            raise ModelError(f"Failed to load model {model_size}: {e}")

    def unload_model(self) -> None:
        """Unload current model and free memory."""
        if self.current_model is None:
            return

        try:
            # Delete model
            del self.current_model
            self.current_model = None

            # Free GPU memory if using CUDA
            if self.current_device == "cuda":
                try:
                    import torch
                    torch.cuda.empty_cache()
                except ImportError:
                    pass

            logger.info(f"Model {self.current_size} unloaded")

            self.current_size = None
            self.current_device = None

        except Exception as e:
            logger.error(f"Error unloading model: {e}")

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.current_model is not None
