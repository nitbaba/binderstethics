from __future__ import annotations

from typing import Callable, Optional

from src.db.models import Binder, Card


class AppState:
    """Single shared state object.

    Views mutate this and call the registered refresh callbacks so other
    views can react.  This avoids any global variables and makes the data
    flow explicit: views read from state, write to state, then trigger
    a refresh.
    """

    def __init__(self) -> None:
        self.active_binder: Optional[Binder] = None
        self.preview_card: Optional[Card] = None

        # Drag source: set when a drag begins so the drop target knows
        # where the card is coming from.
        # Format: {"source": "search"|"binder", "card": Card,
        #           "page": int, "side": int, "pos": int}  (binder only)
        self.drag_payload: Optional[dict] = None  # type: ignore[type-arg]

        self._on_binder_change: list[Callable[[], None]] = []
        self._on_preview_change: list[Callable[[], None]] = []
        self._on_sidebar_change: list[Callable[[], None]] = []

    def register_binder_listener(self, cb: Callable[[], None]) -> None:
        self._on_binder_change.append(cb)

    def register_preview_listener(self, cb: Callable[[], None]) -> None:
        self._on_preview_change.append(cb)

    def register_sidebar_listener(self, cb: Callable[[], None]) -> None:
        self._on_sidebar_change.append(cb)

    def notify_binder_changed(self) -> None:
        for cb in self._on_binder_change:
            cb()

    def notify_preview_changed(self) -> None:
        for cb in self._on_preview_change:
            cb()

    def notify_sidebar_changed(self) -> None:
        for cb in self._on_sidebar_change:
            cb()

    def set_preview(self, card: Optional[Card]) -> None:
        self.preview_card = card
        self.notify_preview_changed()

    def clear_preview(self) -> None:
        self.set_preview(None)
