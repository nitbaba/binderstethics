from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import httpx

from src.db.models import Card, CardSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.scryfall.com"
_PAGE_SIZE = 50


class ScryfallError(Exception):
    pass


@dataclass
class SearchResult:
    cards: list[Card]
    total_count: int
    page: int
    page_size: int = _PAGE_SIZE
    has_more: bool = False

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return math.ceil(self.total_count / self.page_size) if self.total_count else 1


class ScryfallClient:
    """Async client for the Scryfall API. No API key required."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"User-Agent": "BindersEthics/1.0"},
            timeout=10.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(
        self,
        name: str = "",
        set_name: str = "",
        page: int = 1,
    ) -> SearchResult:
        parts: list[str] = []
        if name.strip():
            parts.append(name.strip())
        if set_name.strip():
            parts.append(f"set:{set_name.strip()}")

        if not parts:
            return SearchResult(cards=[], total_count=0, page=1)

        query = " ".join(parts)
        params = {"q": query, "page": page, "order": "name"}

        try:
            resp = await self._client.get("/cards/search", params=params)
            if resp.status_code == 404:
                return SearchResult(cards=[], total_count=0, page=page)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise ScryfallError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ScryfallError(f"Request failed: {exc}") from exc

        cards = [_to_card(raw) for raw in data.get("data", [])][:_PAGE_SIZE]

        return SearchResult(
            cards=cards,
            total_count=data.get("total_cards", 0),
            page=page,
            page_size=_PAGE_SIZE,
            has_more=data.get("has_more", False),
        )


def _to_card(raw: dict) -> Card:
    images = raw.get("image_uris", {})
    if not images and "card_faces" in raw:
        images = raw["card_faces"][0].get("image_uris", {})

    return Card(
        api_id=raw["id"],
        name=raw.get("name", ""),
        set_name=raw.get("set_name", ""),
        set_id=raw.get("set", ""),
        number=raw.get("collector_number", ""),
        image_small=images.get("small", images.get("normal", "")),
        image_large=images.get("large", images.get("normal", "")),
        source=CardSource.MTG,
    )