from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    if not root.handlers:
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
