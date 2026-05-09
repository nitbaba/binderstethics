from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from src.config import ScraperConfig, config as app_config

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


class Scraper:
    def __init__(self, scraper_config: ScraperConfig | None = None) -> None:
        self._cfg = scraper_config or app_config.scraper
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "Scraper":
        self._client = httpx.AsyncClient(
            base_url=self._cfg.base_url,
            timeout=self._cfg.request_timeout,
            follow_redirects=True,
            headers={"User-Agent": "MyApp/0.1"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_html(self, url: str, *, parser: str = "lxml") -> BeautifulSoup:
        if self._client is None:
            raise RuntimeError("Scraper must be used as an async context manager.")

        await self._rate_limit()

        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ScraperError(f"HTTP {exc.response.status_code} for {url}") from exc
        except httpx.RequestError as exc:
            raise ScraperError(f"Request failed for {url}: {exc}") from exc

        logger.info("Fetched %s (%d bytes)", url, len(response.content))
        return BeautifulSoup(response.text, parser)

    async def _rate_limit(self) -> None:
        if self._cfg.rate_limit_delay > 0:
            await asyncio.sleep(self._cfg.rate_limit_delay)
