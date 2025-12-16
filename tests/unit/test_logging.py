"""
Tests for logging system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from loguru import logger

from Quill.utils.logging import setup_logging, get_logger

pytestmark = pytest.mark.unit


class TestLogging:
    """Test logging configuration and functionality."""

    def setup_method(self):
        """Remove all handlers before each test."""
        logger.remove()

    def test_setup_logging_creates_log_file(self):
        """Test that setup_logging creates the log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(log_file=log_file, log_level="INFO")

            # Write a log message
            logger.info("Test message")

            # Verify log file was created
            assert log_file.exists()

    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "logs" / "nested" / "test.log"

            setup_logging(log_file=log_file, log_level="INFO")

            # Write a log message
            logger.info("Test message")

            # Verify directory and file were created
            assert log_file.parent.exists()
            assert log_file.exists()

    def test_setup_logging_respects_log_level(self):
        """Test that log level filtering works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # Set log level to WARNING
            setup_logging(log_file=log_file, log_level="WARNING")

            # Write messages at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Wait for async logging to complete
            logger.complete()

            # Read log file
            with open(log_file, "r") as f:
                log_content = f.read()

            # DEBUG and INFO should not be in log
            assert "Debug message" not in log_content
            assert "Info message" not in log_content

            # WARNING and ERROR should be in log
            assert "Warning message" in log_content
            assert "Error message" in log_content

    def test_setup_logging_different_levels(self):
        """Test setup with different log levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test DEBUG level
            log_file = Path(tmpdir) / "debug.log"
            setup_logging(log_file=log_file, log_level="DEBUG")
            logger.debug("Debug test")

            logger.complete()

            with open(log_file, "r") as f:
                assert "Debug test" in f.read()

            logger.remove()

            # Test ERROR level
            log_file = Path(tmpdir) / "error.log"
            setup_logging(log_file=log_file, log_level="ERROR")
            logger.info("Info test")
            logger.error("Error test")

            logger.complete()

            with open(log_file, "r") as f:
                content = f.read()
                assert "Info test" not in content
                assert "Error test" in content

    def test_get_logger(self):
        """Test get_logger returns a bound logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_file=log_file, log_level="INFO")

            # Get a logger for a module
            test_logger = get_logger("test_module")

            # Write a message
            test_logger.info("Test from module")

            # Verify it was logged
            with open(log_file, "r") as f:
                assert "Test from module" in f.read()

    def test_logging_writes_to_file(self):
        """Test that log messages are written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(log_file=log_file, log_level="INFO")

            # Write various log messages
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Wait for async logging to complete
            logger.complete()

            # Read and verify
            with open(log_file, "r") as f:
                content = f.read()
                assert "Info message" in content
                assert "Warning message" in content
                assert "Error message" in content

    def test_logging_format_contains_required_fields(self):
        """Test that log format includes timestamp, level, and message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(log_file=log_file, log_level="INFO")
            logger.info("Test message")

            # Wait for async logging to complete
            logger.complete()

            with open(log_file, "r") as f:
                content = f.read()

                # Should contain timestamp (YYYY-MM-DD HH:MM:SS format)
                assert any(char.isdigit() for char in content)

                # Should contain log level
                assert "INFO" in content

                # Should contain the message
                assert "Test message" in content

    def test_multiple_setup_calls(self):
        """Test that calling setup_logging multiple times works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file1 = Path(tmpdir) / "test1.log"
            log_file2 = Path(tmpdir) / "test2.log"

            setup_logging(log_file=log_file1, log_level="INFO")
            logger.info("Message 1")

            # Setup again with different file
            setup_logging(log_file=log_file2, log_level="DEBUG")
            logger.debug("Message 2")

            # Wait for async logging to complete
            logger.complete()

            # Both files should exist and contain their respective messages
            assert log_file1.exists()
            assert log_file2.exists()

            with open(log_file2, "r") as f:
                content = f.read()
                assert "Message 2" in content
