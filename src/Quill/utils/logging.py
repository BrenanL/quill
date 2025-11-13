"""
Logging configuration for Quill using loguru.

Provides structured logging with file rotation and custom formatting.
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    log_file: str | Path = "logs/Quill.log",
    log_level: str = "INFO",
    max_size_mb: int = 10,
    rotation_count: int = 5,
) -> None:
    """
    Configure logging for Quill application.

    Args:
        log_file: Path to log file (created if doesn't exist)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        max_size_mb: Maximum log file size before rotation (MB)
        rotation_count: Number of rotated log files to keep

    Example:
        >>> setup_logging("logs/Quill.log", "DEBUG", max_size_mb=20)
    """
    # Remove default logger
    logger.remove()

    # Format for console output (simpler)
    console_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Format for file output (more detailed)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Add console logger (stderr)
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add file logger with rotation
    logger.add(
        log_file,
        format=file_format,
        level=log_level.upper(),
        rotation=f"{max_size_mb} MB",  # Rotate when file reaches size
        retention=rotation_count,  # Keep this many old log files
        compression="zip",  # Compress rotated logs
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )

    logger.info(f"Logging initialized: level={log_level.upper()}, file={log_file}")


def get_logger(name: str):
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance bound to the module name

    Example:
        >>> log = get_logger(__name__)
        >>> log.info("Hello from module")
    """
    return logger.bind(name=name)
