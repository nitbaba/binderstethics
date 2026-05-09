from __future__ import annotations

import logging
from typing import Optional

import flet as ft

from src.db.models import Binder, Card, PAGES_BY_SIZE
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)

_DRAG_GROUP = "card"

# Base card slot dimensions. Zoom scales these.
_BASE_CARD_W = 90
_BASE_CARD_H = 126
_MIN_ZOOM = 0.5
_MAX_ZOOM = 1.6
_ZOOM_STEP = 0.1


def build_binder_view(
    page: ft.Page,
    state: AppState,
    on_save: callable,  # type: ignore[type-arg]
) -> ft.Control:
    """Bottom half of the main area.

    Shows a book-style spread: left page (front) and right page (back) of the
    current physical page.  Arrow keys turn pages.
    """

    # ── View state ───────────────────────────────────────────────────
    _current_physical_page = 1  # 1-indexed
    _zoom = 1.0

    # ── Top bar ──────────────────────────────────────────────────────

    binder_title = ft.Text(
        "No binder open",
        size=15,
        weight=ft.FontWeight.W_700,
        color=COLORS["text_primary"],
    )

    page_indicator = ft.Text("", size=12, color=COLORS["text_muted"])

    save_btn = ft.ElevatedButton(
        content=ft.Text("Save", color=COLORS["text_primary"]),
        bgcolor=COLORS["accent"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        height=36,
        visible=False,
        on_click=lambda _: on_save(),
    )

    zoom_out_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_OUT,
        icon_color=COLORS["text_muted"],
        icon_size=18,
        on_click=lambda _: _adjust_zoom(-_ZOOM_STEP),
    )

    zoom_in_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_IN,
        icon_color=COLORS["text_muted"],
        icon_size=18,
        on_click=lambda _: _adjust_zoom(_ZOOM_STEP),
    )

    prev_page_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: _turn_page(-1),
    )

    next_page_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: _turn_page(1),
    )

    # ── Spread container ─────────────────────────────────────────────
    # The spread holds two page panels side by side.
    spread_row = ft.Row(
        [],
        spacing=16,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    spread_scroll = ft.GestureDetector(
        content=ft.Column(
            [spread_row],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    empty_label = ft.Text(
        "Open a binder from the sidebar to get started.",
        size=14,
        color=COLORS["text_muted"],
    )

    binder_body = ft.Stack(
        [
            ft.Container(
                content=empty_label,
                alignment=ft.Alignment(0, 0),
                expand=True,
            ),
        ],
        expand=True,
    )

    # ── Helpers ──────────────────────────────────────────────────────

    def _active_binder() -> Optional[Binder]:
        return state.active_binder

    def _card_w() -> float:
        available = max(600, page.width - 230)
        natural = (available / (_cols() + 1)) * 0.75
        return min(natural, _BASE_CARD_W * 2) * _zoom

    def _card_h() -> float:
        return _card_w() * 1.4

    def _total_pages() -> int:
        b = _active_binder()
        return b.total_pages if b else 0

    def _cols() -> int:
        b = _active_binder()
        if b is None:
            return 3
        size = b.size.value
        if size == 4:
            return 2
        if size == 9:
            return 3
        if size == 12:
            return 4  # 3 rows × 4 cols = 12
        return 4       # 16 → 4 × 4

    def _rows() -> int:
        b = _active_binder()
        if b is None:
            return 1
        size = b.size.value
        if size == 4:
            return 2
        if size == 9:
            return 3
        if size == 12:
            return 3  # 3 rows × 4 cols = 12
        return 4       # 16 → 4 × 4

    def _update_nav() -> None:
        nonlocal _current_physical_page
        total = _total_pages()
        prev_page_btn.disabled = _current_physical_page <= 1
        next_page_btn.disabled = _current_physical_page >= total
        if total > 0:
            page_indicator.value = f"Page {_current_physical_page} / {total}"
        else:
            page_indicator.value = ""

    def _refresh_spread() -> None:
        spread_row.controls.clear()
        b = _active_binder()
        if b is None:
            return
        # Front side (side=0) is the left page, back (side=1) is the right page.
        spread_row.controls.append(_build_page_panel(b, _current_physical_page, side=0))
        spread_row.controls.append(_build_page_panel(b, _current_physical_page, side=1))

    def _build_page_panel(binder: Binder, physical_page: int, side: int) -> ft.Control:
        side_label = "Front" if side == 0 else "Back"
        grid_controls: list[ft.Control] = []

        for pos in range(binder.pockets_per_side):
            slot = binder.get_slot(physical_page, side, pos)
            grid_controls.append(_build_slot(binder, physical_page, side, pos, slot.card))

        rows_list: list[ft.Control] = []
        cols = _cols()
        for i in range(0, len(grid_controls), cols):
            rows_list.append(
                ft.Row(
                    grid_controls[i : i + cols],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"p.{physical_page} · {side_label}",
                        size=11,
                        color=COLORS["text_muted"],
                    ),
                    ft.Column(rows_list, spacing=6),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"],
            border_radius=12,
            padding=16,
            border=ft.Border.all(1, COLORS["border"]),
        )

    def _build_slot(
        binder: Binder,
        physical_page: int,
        side: int,
        pos: int,
        card: Optional[Card],
    ) -> ft.Control:
        w = _card_w()
        h = _card_h()

        if card is not None:
            slot_content = ft.Stack(
                [
                    ft.Image(src=card.image_small, width=w, height=h, fit=ft.BoxFit.CONTAIN),
                    ft.Container(
                        content=ft.GestureDetector(
                            content=ft.Container(
                                content=ft.Icon(ft.Icons.CLOSE, color=COLORS["error"], size=14),
                                bgcolor=COLORS["surface"],
                                border_radius=10,
                                padding=2,
                            ),
                            on_tap=lambda _, pp=physical_page, s=side, p=pos: _remove_card(pp, s, p),
                        ),
                        right=2,
                        top=2,
                    ),
                ],
                width=w,
                height=h,
            )

            draggable_slot = ft.Draggable(
                group=_DRAG_GROUP,
                content=slot_content,
                content_feedback=ft.Container(
                    content=ft.Image(src=card.image_small, width=60, height=84, fit=ft.BoxFit.CONTAIN),
                    opacity=0.85,
                ),
                data={"page": physical_page, "side": side, "pos": pos, "card": card},
                on_drag_start=lambda _, pp=physical_page, s=side, p=pos, c=card: _on_binder_drag_start(pp, s, p, c),
                on_drag_complete=lambda _: _on_binder_drag_complete(),
            )

            inner: ft.Control = draggable_slot
        else:
            inner = ft.Container(
                width=w,
                height=h,
                bgcolor=COLORS["slot_empty"],
                border_radius=4,
                border=ft.Border.all(1, COLORS["slot_border"]),
            )

        return ft.DragTarget(
            group=_DRAG_GROUP,
            content=ft.Container(
                content=inner,
                width=w,
                height=h,
                border_radius=4,
            ),
            on_accept=lambda e, pp=physical_page, s=side, p=pos: _on_drop(e, pp, s, p),
            on_will_accept=lambda e: _on_will_accept(e),
            on_leave=lambda e: _on_leave(e),
        )

    # ── Drag handlers ────────────────────────────────────────────────

    def _on_binder_drag_start(physical_page: int, side: int, pos: int, card: Card) -> None:
        state.drag_payload = {
            "source": "binder",
            "card": card,
            "page": physical_page,
            "side": side,
            "pos": pos,
        }

    def _on_binder_drag_complete() -> None:
        state.drag_payload = None

    def _on_will_accept(e: ft.DragWillAcceptEvent) -> None:
        e.control.content.border = ft.Border.all(2, COLORS["accent"])  # type: ignore[union-attr]
        e.control.content.update()

    def _on_leave(e: ft.DragTargetLeaveEvent) -> None:
        e.control.content.border = ft.Border.all(1, COLORS["slot_border"])  # type: ignore[union-attr]
        e.control.content.update()

    def _on_drop(e: ft.DragTargetEvent, dst_page: int, dst_side: int, dst_pos: int) -> None:
        binder = _active_binder()
        if binder is None or state.drag_payload is None:
            return

        payload = state.drag_payload
        incoming_card: Card = payload["card"]

        if payload["source"] == "search":
            dst_slot = binder.get_slot(dst_page, dst_side, dst_pos)
            if dst_slot.card is not None:
                # Swap: the existing card gets displaced — just replace it.
                binder.place_card(dst_page, dst_side, dst_pos, incoming_card)
            else:
                binder.place_card(dst_page, dst_side, dst_pos, incoming_card)
            state.clear_preview()

        elif payload["source"] == "binder":
            src_page = payload["page"]
            src_side = payload["side"]
            src_pos = payload["pos"]
            binder.swap_slots(src_page, src_side, src_pos, dst_page, dst_side, dst_pos)

        state.drag_payload = None
        _refresh_and_update()

    def _remove_card(physical_page: int, side: int, pos: int) -> None:
        binder = _active_binder()
        if binder:
            binder.remove_card(physical_page, side, pos)
            _refresh_and_update()

    # ── Page navigation ──────────────────────────────────────────────

    def _turn_page(delta: int) -> None:
        nonlocal _current_physical_page
        total = _total_pages()
        new_page = _current_physical_page + delta
        if 1 <= new_page <= total:
            _current_physical_page = new_page
            _refresh_and_update()

    def _on_scroll(e: ft.ScrollEvent) -> None:
        # Scroll on the binder area zooms in/out.
        if e.scroll_delta_y < 0:
            _adjust_zoom(_ZOOM_STEP)
        else:
            _adjust_zoom(-_ZOOM_STEP)

    def _adjust_zoom(delta: float) -> None:
        nonlocal _zoom
        _zoom = round(max(_MIN_ZOOM, min(_MAX_ZOOM, _zoom + delta)), 2)
        _refresh_and_update()

    spread_scroll.on_scroll = _on_scroll

    # ── Full refresh ─────────────────────────────────────────────────

    def _refresh_and_update() -> None:
        _refresh_spread()
        _update_nav()
        binder_body.controls = [spread_scroll] if _active_binder() else [
            ft.Container(
                content=empty_label,
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        ]
        page.update()

    # ── Public refresh callback (called by app.py when binder changes) ─

    def refresh() -> None:
        nonlocal _current_physical_page
        _current_physical_page = 1
        b = _active_binder()
        if b:
            binder_title.value = f"{b.name}  ·  {b.size.value}-pocket"
            save_btn.visible = True
        else:
            binder_title.value = "No binder open"
            save_btn.visible = False
        _refresh_and_update()

    state.register_binder_listener(refresh)

    # ── Keyboard navigation ──────────────────────────────────────────
    # Registered on the page; only acts when a binder is open.

    def _on_key(e: ft.KeyboardEvent) -> None:
        if e.key == "Arrow Left":
            _turn_page(-1)
        elif e.key == "Arrow Right":
            _turn_page(1)

    page.on_keyboard_event = _on_key

    # ── Layout ───────────────────────────────────────────────────────

    top_bar = ft.Row(
        [
            binder_title,
            ft.Container(expand=True),
            zoom_out_btn,
            zoom_in_btn,
            prev_page_btn,
            page_indicator,
            next_page_btn,
            save_btn,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )

    def _on_page_resize(_: ft.ControlEvent) -> None:
        if _active_binder() is not None:
            _refresh_and_update()

    page.on_resize = _on_page_resize

    return ft.Column(
        [
            ft.Divider(height=1, color=COLORS["border"]),
            top_bar,
            binder_body,
        ],
        spacing=8,
        expand=True,
    )
