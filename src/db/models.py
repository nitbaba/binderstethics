from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BinderSize(Enum):
    FOUR = 4
    NINE = 9
    TWELVE = 12
    SIXTEEN = 16


PAGES_BY_SIZE: dict[BinderSize, int] = {
    BinderSize.FOUR: 20,
    BinderSize.NINE: 20,
    BinderSize.TWELVE: 20,
    BinderSize.SIXTEEN: 34,
}


@dataclass
class Card:
    api_id: str
    name: str
    set_name: str
    set_id: str
    number: str
    image_small: str
    image_large: str


@dataclass
class BinderSlot:
    page_number: int
    side: int
    position: int
    card: Optional[Card] = None


@dataclass
class Binder:
    id: int
    name: str
    size: BinderSize
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


# ---------------------------------------------------------------------------
# Display presets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    width: int
    height: int
    scale_factor: float
    fullscreen: bool = False


PRESETS: list[Preset] = [
    Preset("hd",         "HD  1280×720",    1280,  720,  0.75),
    Preset("fhd",        "FHD  1920×1080",  1920, 1080,  1.0),
    Preset("qhd",        "2K  2560×1440",   2560, 1440,  1.25),
    Preset("uhd",        "4K  3840×2160",   3840, 2160,  1.5),
    Preset("fullscreen", "Fullscreen",          0,    0,  1.0, fullscreen=True),
]

DEFAULT_PRESET: Preset = PRESETS[1]  # FHD

PRESET_BY_KEY: dict[str, Preset] = {p.key: p for p in PRESETS}


def nearest_preset(width: float, height: float) -> Preset:
    """Return the preset whose resolution is closest to the given dimensions."""
    non_fullscreen = [p for p in PRESETS if not p.fullscreen]
    return min(
        non_fullscreen,
        key=lambda p: abs(p.width - width) + abs(p.height - height),
    )