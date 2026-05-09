"""Integration tests — config and multi-layer smoke tests."""

from __future__ import annotations

import logging

from src.config import Config


def test_config_loads_defaults() -> None:
    cfg = Config()
    assert cfg.app.name
    assert cfg.scraper.request_timeout > 0
    assert cfg.gui.window_width > 0


def test_config_log_level_is_valid() -> None:
    cfg = Config()
    assert hasattr(logging, cfg.app.log_level.upper()), (
        f"'{cfg.app.log_level}' is not a valid log level"
    )


def test_scraper_config_delay_non_negative() -> None:
    cfg = Config()
    assert cfg.scraper.rate_limit_delay >= 0
