from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from src.db.models import Card

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.pokemontcg.io/v2"
_PAGE_SIZE = 50


@dataclass
class SearchResult:
    cards: list[Card]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size


class PokemonTcgError(Exception):
    pass


class PokemonTcgClient:
    """Async client for the Pokemon TCG API (api.pokemontcg.io/v2).

    Must be used as an async context manager:

        async with PokemonTcgClient(api_key) as client:
            result = await client.search_cards(name="Pikachu", page=1)
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> PokemonTcgClient:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"X-Api-Key": self._api_key},
            timeout=15,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_cards(
        self,
        name: str = "",
        set_name: str = "",
        page: int = 1,
    ) -> SearchResult:
        """Search cards by name and/or set name (both are AND conditions).

        Args:
            name:     Partial card name. Empty string skips this filter.
            set_name: Partial set name. Empty string skips this filter.
            page:     1-indexed page number.

        Returns:
            SearchResult containing matched cards and pagination metadata.

        Raises:
            PokemonTcgError: On HTTP or network failures.
        """
        if self._client is None:
            raise RuntimeError("Client must be used as an async context manager.")

        parts: list[str] = []
        if name.strip():
            parts.append(f'name:"{name.strip()}*"')
        if set_name.strip():
            parts.append(f'set.name:"{set_name.strip()}*"')

        # If neither filter is given, return an empty result rather than
        # fetching the entire card database.
        if not parts:
            return SearchResult(cards=[], total_count=0, page=1, page_size=_PAGE_SIZE)

        query = " ".join(parts)
        params = {
            "q": query,
            "page": page,
            "pageSize": _PAGE_SIZE,
            "select": "id,name,set,number,images",
        }

        try:
            response = await self._client.get("/cards", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PokemonTcgError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise PokemonTcgError(f"Request failed: {exc}") from exc

        data = response.json()
        cards = [_parse_card(raw) for raw in data.get("data", []) if _is_valid(raw)]
        total = data.get("totalCount", 0)

        logger.info("Search q=%r page=%d → %d/%d cards", query, page, len(cards), total)
        return SearchResult(cards=cards, total_count=total, page=page, page_size=_PAGE_SIZE)


def _is_valid(raw: dict[str, Any]) -> bool:
    """Return True only if the card has the fields we need to display it."""
    images = raw.get("images", {})
    return bool(
        raw.get("id")
        and raw.get("name")
        and raw.get("set")
        and images.get("small")
        and images.get("large")
    )


def _parse_card(raw: dict[str, Any]) -> Card:
    tcg_set = raw["set"]
    images = raw["images"]
    return Card(
        api_id=raw["id"],
        name=raw["name"],
        set_name=tcg_set.get("name", ""),
        set_id=tcg_set.get("id", ""),
        number=raw.get("number", ""),
        image_small=images["small"],
        image_large=images["large"],
    )
