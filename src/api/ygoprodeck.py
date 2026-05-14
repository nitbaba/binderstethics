from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import httpx

from src.db.models import Card, CardSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://db.ygoprodeck.com/api/v7"
_PAGE_SIZE = 50


class YgoError(Exception):
    pass


@dataclass
class SearchResult:
    cards: list[Card]
    total_count: int
    page: int
    page_size: int = _PAGE_SIZE

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return math.ceil(self.total_count / self.page_size) if self.total_count else 1


class YgoClient:
    """Async client for the YGOPRODeck API. No API key required."""

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
        if not name.strip() and not set_name.strip():
            return SearchResult(cards=[], total_count=0, page=1)

        params: dict = {"num": _PAGE_SIZE, "offset": (page - 1) * _PAGE_SIZE}
        if name.strip():
            params["fname"] = name.strip()  # fuzzy name search
        if set_name.strip():
            params["cardset"] = set_name.strip()

        try:
            resp = await self._client.get("/cardinfo.php", params=params)
            if resp.status_code == 400:
                # YGOPRODeck returns 400 with a message when no cards found
                return SearchResult(cards=[], total_count=0, page=page)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise YgoError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise YgoError(f"Request failed: {exc}") from exc

        total = data.get("meta", {}).get("total_rows", len(data.get("data", [])))
        cards = [_to_card(raw) for raw in data.get("data", [])]

        return SearchResult(
            cards=cards,
            total_count=total,
            page=page,
            page_size=_PAGE_SIZE,
        )


def _to_card(raw: dict) -> Card:
    # Use the first card image available
    images = raw.get("card_images", [{}])
    image = images[0] if images else {}

    # card_sets holds set info; use the first one
    sets = raw.get("card_sets", [{}])
    first_set = sets[0] if sets else {}

    return Card(
        api_id=str(raw.get("id", "")),
        name=raw.get("name", ""),
        set_name=first_set.get("set_name", ""),
        set_id=first_set.get("set_code", ""),
        number=first_set.get("set_code", ""),
        image_small=image.get("image_url_small", ""),
        image_large=image.get("image_url", ""),
        source=CardSource.YGO,
    )