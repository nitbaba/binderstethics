from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise OSError(f"Required environment variable '{key}' is not set.")
    return value


def _get(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class AppConfig:
    name: str = field(default_factory=lambda: _get("APP_NAME", "BindersEthics"))
    log_level: str = field(default_factory=lambda: _get("LOG_LEVEL", "INFO"))


@dataclass(frozen=True)
class ApiConfig:
    # Loaded lazily via _require so startup fails fast with a clear message
    # if the key is missing, rather than failing silently on first API call.
    pokemon_tcg_api_key: str = field(default_factory=lambda: _require("POKEMON_TCG_API_KEY"))


@dataclass(frozen=True)
class DbConfig:
    path: Path = field(default_factory=lambda: Path(_get("DB_PATH", "data/binders.db")))


@dataclass(frozen=True)
class GuiConfig:
    window_width: int = field(default_factory=lambda: int(_get("GUI_WINDOW_WIDTH", "1400")))
    window_height: int = field(default_factory=lambda: int(_get("GUI_WINDOW_HEIGHT", "900")))


@dataclass(frozen=True)
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    db: DbConfig = field(default_factory=DbConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)


config = Config()
