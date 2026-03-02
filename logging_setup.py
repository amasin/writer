"""Structured logging setup for WriterAgent."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with a simple format and level."""
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    logging.basicConfig(stream=sys.stderr, level=level.upper(), format=fmt)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
