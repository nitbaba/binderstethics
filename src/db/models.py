from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BinderSize(Enum):
    FOUR = 4
    NINE = 9
    TWELVE = 12
    SIXTEEN = 16


# Page counts per binder type, matching Vault X specs.
PAGES_BY_SIZE: dict[BinderSize, int] = {
    BinderSize.FOUR: 20,
    BinderSize.NINE: 20,
    BinderSize.TWELVE: 20,
    BinderSize.SIXTEEN: 34,
}


@dataclass
class Card:
    """A Pokemon TCG card as returned by the API."""
    api_id: str
    name: str
    set_name: str
    set_id: str
    number: str
    image_small: str   # URL — thumbnail shown in search results
    image_large: str   # URL — shown in preview panel


@dataclass
class BinderSlot:
    """One pocket in the binder. card is None when the slot is empty."""
    page_number: int   # 1-indexed physical page
    side: int          # 0 = front, 1 = back
    position: int      # 0-indexed within the side's grid
    card: Optional[Card] = None


@dataclass
class Binder:
    """A virtual binder with a fixed size and a collection of slots."""
    id: int
    name: str
    size: BinderSize
    # Slots are the authoritative in-memory state.
    # Key: (page_number, side, position)
    slots: dict[tuple[int, int, int], BinderSlot] = field(default_factory=dict)

    @property
    def total_pages(self) -> int:
        return PAGES_BY_SIZE[self.size]

    @property
    def pockets_per_side(self) -> int:
        return self.size.value

    def get_slot(self, page: int, side: int, position: int) -> BinderSlot:
        key = (page, side, position)
        if key not in self.slots:
            self.slots[key] = BinderSlot(page, side, position)
        return self.slots[key]

    def place_card(self, page: int, side: int, position: int, card: Card) -> None:
        self.get_slot(page, side, position).card = card

    def remove_card(self, page: int, side: int, position: int) -> None:
        self.get_slot(page, side, position).card = None

    def swap_slots(
        self,
        src_page: int, src_side: int, src_pos: int,
        dst_page: int, dst_side: int, dst_pos: int,
    ) -> None:
        src = self.get_slot(src_page, src_side, src_pos)
        dst = self.get_slot(dst_page, dst_side, dst_pos)
        src.card, dst.card = dst.card, src.card
