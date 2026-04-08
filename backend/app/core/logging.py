"""
Structured Logging Configuration

Sets up named loggers for the LENA application with appropriate log levels
and formatters. Use this to get proper logger instances throughout the app.

Usage:
    from app.core.logging import get_logger
    logger = get_logger("lena.search")
    logger.info("Search completed", extra={"query": q, "results": n})
"""

import logging
import logging.config
import os
from typing import Optional


# Configure which loggers are used in this app
LOGGER_NAMES = {
    "lena.search": logging.INFO,
    "lena.pulse": logging.INFO,
    "lena.sources": logging.INFO,
    "lena.guardrails": logging.INFO,
    "lena.analytics": logging.DEBUG,
}


def setup_logging(env: str = "development") -> None:
    """
    Initialize the logging system.

    Args:
        env: Environment type - 'development' or 'production'
    """
    # Determine if we're in debug mode
    debug_mode = env.lower() != "production"

    # Create formatters
    if debug_mode:
        # Readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # More concise format for production (assumes centralized logging)
        formatter = logging.Formatter(
            fmt="%(name)s|%(levelname)s|%(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    root_logger.addHandler(console_handler)

    # Configure named loggers
    for logger_name, level in LOGGER_NAMES.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: Logger name (e.g., 'lena.search', 'lena.pulse')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Initialize on import with default settings
_env = os.getenv("ENV", "development")
setup_logging(_env)
