"""
Configuration manager for loading and validating YAML config files.
"""

from pathlib import Path
from typing import Optional
from ruamel.yaml import YAML
from pydantic import ValidationError

from .schema import Config


class ConfigManager:
    """Manages loading, validation, and saving of configuration."""

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False

    @staticmethod
    def load(config_path: str | Path) -> Config:
        """
        Load and validate configuration from YAML file.

        Args:
            config_path: Path to config.yaml file

        Returns:
            Validated Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid or fails validation
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}. "
                f"Please create config.yaml from config.example.yaml"
            )

        # Load YAML
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = YAML().load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse YAML from {config_path}: {e}") from e

        # Validate with Pydantic
        try:
            config = Config(**config_data) if config_data else Config()
            return config
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed:\n{e}") from e

    @staticmethod
    def load_with_defaults(config_path: str | Path) -> Config:
        """
        Load configuration, or return defaults if file doesn't exist.

        Args:
            config_path: Path to config.yaml file

        Returns:
            Validated Config object (with defaults if file doesn't exist)
        """
        try:
            return ConfigManager.load(config_path)
        except FileNotFoundError:
            # Return default config if file doesn't exist
            return Config()

    def save(self, config: Config, config_path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: Config object to save
            config_path: Path to write config.yaml
        """
        config_path = Path(config_path)

        # Convert to dict
        config_dict = config.model_dump()

        # Write YAML
        with open(config_path, "w", encoding="utf-8") as f:
            self.yaml.dump(config_dict, f)

    @staticmethod
    def validate(config_data: dict) -> tuple[bool, Optional[str]]:
        """
        Validate configuration dictionary without loading from file.

        Args:
            config_data: Dictionary of configuration values

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            Config(**config_data)
            return True, None
        except ValidationError as e:
            return False, str(e)
