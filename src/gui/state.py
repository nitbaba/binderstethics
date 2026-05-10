from __future__ import annotations

from typing import Callable, Optional

from src.db.models import Binder, Card, Preset, DEFAULT_PRESET


class AppState:
    def __init__(self) -> None:
        self.active_binder: Optional[Binder] = None
        self.preview_card: Optional[Card] = None
        self.active_preset: Preset = DEFAULT_PRESET
        self.drag_payload: Optional[dict] = None  # type: ignore[type-arg]

        self._on_binder_change: list[Callable[[], None]] = []
        self._on_preview_change: list[Callable[[], None]] = []
        self._on_sidebar_change: list[Callable[[], None]] = []
        self._on_scale_change: list[Callable[[], None]] = []

    def clear_listeners(self) -> None:
        """Remove all registered listeners. Called before rebuilding views
        to prevent accumulation across rebuilds."""
        self._on_binder_change.clear()
        self._on_preview_change.clear()
        self._on_sidebar_change.clear()
        self._on_scale_change.clear()

    def register_binder_listener(self, cb: Callable[[], None]) -> None:
        self._on_binder_change.append(cb)

    def register_preview_listener(self, cb: Callable[[], None]) -> None:
        self._on_preview_change.append(cb)

    def register_sidebar_listener(self, cb: Callable[[], None]) -> None:
        self._on_sidebar_change.append(cb)

    def register_scale_listener(self, cb: Callable[[], None]) -> None:
        self._on_scale_change.append(cb)

    def notify_binder_changed(self) -> None:
        for cb in self._on_binder_change:
            cb()

    def notify_preview_changed(self) -> None:
        for cb in self._on_preview_change:
            cb()

    def notify_sidebar_changed(self) -> None:
        for cb in self._on_sidebar_change:
            cb()

    def notify_scale_changed(self) -> None:
        for cb in self._on_scale_change:
            cb()

    def set_preview(self, card: Optional[Card]) -> None:
        self.preview_card = card
        self.notify_preview_changed()

    def clear_preview(self) -> None:
        self.set_preview(None)

    @property
    def scale_factor(self) -> float:
        return self.active_preset.scale_factor