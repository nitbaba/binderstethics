from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)


def _get(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class AppConfig:
    name: str = field(default_factory=lambda: _get("APP_NAME", "MyApp"))
    log_level: str = field(default_factory=lambda: _get("LOG_LEVEL", "INFO"))


@dataclass(frozen=True)
class ScraperConfig:
    base_url: str = field(default_factory=lambda: _get("SCRAPER_BASE_URL", "https://example.com"))
    request_timeout: int = field(default_factory=lambda: int(_get("SCRAPER_REQUEST_TIMEOUT", "10")))
    rate_limit_delay: float = field(default_factory=lambda: float(_get("SCRAPER_RATE_LIMIT_DELAY", "1.0")))


@dataclass(frozen=True)
class GuiConfig:
    window_width: int = field(default_factory=lambda: int(_get("GUI_WINDOW_WIDTH", "1100")))
    window_height: int = field(default_factory=lambda: int(_get("GUI_WINDOW_HEIGHT", "720")))


@dataclass(frozen=True)
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)


config = Config()
