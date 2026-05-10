from __future__ import annotations

import logging
from typing import Optional

import flet as ft

from src.db.models import Binder, Card
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)

_DRAG_GROUP = "card"
_BASE_CARD_W = 90
_BASE_CARD_H = 126
_MIN_ZOOM = 0.5
_MAX_ZOOM = 1.6
_ZOOM_STEP = 0.1


# ---------------------------------------------------------------------------
# Spread model
#
# A "spread" is one view of two facing pages, like an open book.
# For a binder with N physical pages, spreads are indexed 0..N:
#
#   spread 0        : [Front Cover]      | [Page 1, side 0]
#   spread 1        : [Page 1, side 1]   | [Page 2, side 0]
#   spread k (1<=k<N): [Page k, side 1]  | [Page k+1, side 0]
#   spread N        : [Page N, side 1]   | [Back Cover]
#
# Total spreads = N + 1
# ---------------------------------------------------------------------------

def _spread_sides(spread: int, total_pages: int) -> tuple:
    """Return (left_page, left_side, right_page, right_side).

    page=0 means cover panel (no card slots).
    """
    if spread == 0:
        return (0, 0, 1, 0)                          # cover | p1 front
    if spread == total_pages:
        return (total_pages, 1, 0, 1)                # pN back | cover
    return (spread, 1, spread + 1, 0)                # pK back | pK+1 front


def build_binder_view(
    page: ft.Page,
    state: AppState,
    on_save: callable,  # type: ignore[type-arg]
) -> ft.Control:

    def s(n: float) -> int:
        return max(1, int(n * state.scale_factor))

    _current_spread = 0
    _zoom = 1.0
    _pan_offset_x: float = 0.0
    _pan_offset_y: float = 0.0

    # ── Top bar ──────────────────────────────────────────────────────

    binder_title = ft.Text(
        "No binder open",
        size=s(15),
        weight=ft.FontWeight.W_700,
        color=COLORS["text_primary"],
    )

    page_indicator = ft.Text("", size=s(12), color=COLORS["text_muted"])

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
        icon_size=s(18),
        on_click=lambda _: _adjust_zoom(-_ZOOM_STEP),
    )

    zoom_in_btn = ft.IconButton(
        icon=ft.Icons.ZOOM_IN,
        icon_color=COLORS["text_muted"],
        icon_size=s(18),
        on_click=lambda _: _adjust_zoom(_ZOOM_STEP),
    )

    prev_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: _turn_page(-1),
    )

    next_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: _turn_page(1),
    )

    # ── Spread ───────────────────────────────────────────────────────

    spread_row = ft.Row(
        [],
        spacing=2,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
        animate_offset=ft.Animation(80, ft.AnimationCurve.EASE_OUT),
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
        size=s(14),
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

    # ── Sizing helpers ────────────────────────────────────────────────

    def _card_w() -> float:
        available = max(600, page.width - 230)
        natural = (available / (_cols() + 1)) * 0.75
        return min(natural, _BASE_CARD_W * 2) * _zoom * state.scale_factor

    def _card_h() -> float:
        return _card_w() * 1.4

    def _cols() -> int:
        b = _active_binder()
        if b is None:
            return 3
        v = b.size.value
        return 2 if v == 4 else 3 if v == 9 else 4

    def _total_spreads() -> int:
        b = _active_binder()
        return b.total_pages + 1 if b else 0

    def _active_binder() -> Optional[Binder]:
        return state.active_binder

    # ── Nav ───────────────────────────────────────────────────────────

    def _update_nav() -> None:
        total = _total_spreads()
        prev_btn.disabled = _current_spread <= 0
        next_btn.disabled = _current_spread >= total - 1
        if total > 0:
            page_indicator.value = f"Spread {_current_spread + 1} / {total}"
        else:
            page_indicator.value = ""

    # ── Panel builders ────────────────────────────────────────────────

    def _build_cover_panel(label: str) -> ft.Control:
        w = _card_w()
        h = _card_h()
        cols = _cols()
        pockets = _active_binder().pockets_per_side if _active_binder() else 9
        rows = (pockets + cols - 1) // cols

        inner_w = cols * w + (cols - 1) * 6
        inner_h = rows * h + (rows - 1) * 6

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            label,
                            size=s(13),
                            color=COLORS["text_muted"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        alignment=ft.Alignment(0, 0),
                        width=inner_w,
                        height=inner_h,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"],
            border_radius=12,
            padding=16,
            border=ft.Border.all(1, COLORS["border"]),
            opacity=0.5,
        )

    def _build_page_panel(physical_page: int, side: int) -> ft.Control:
        binder = _active_binder()
        if binder is None:
            return ft.Container()

        side_label = "Front" if side == 0 else "Back"
        grid_controls: list[ft.Control] = []
        for pos in range(binder.pockets_per_side):
            slot = binder.get_slot(physical_page, side, pos)
            grid_controls.append(
                _build_slot(binder, physical_page, side, pos, slot.card)
            )

        cols = _cols()
        rows_list: list[ft.Control] = []
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
                        size=s(11),
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
                                content=ft.Icon(ft.Icons.CLOSE, color=COLORS["error"], size=s(14)),
                                bgcolor=COLORS["surface"],
                                border_radius=10,
                                padding=2,
                            ),
                            on_tap=lambda _, pp=physical_page, sd=side, p=pos: _remove_card(pp, sd, p),
                        ),
                        right=2,
                        top=2,
                    ),
                ],
                width=w,
                height=h,
            )

            inner: ft.Control = ft.Draggable(
                group=_DRAG_GROUP,
                content=slot_content,
                content_feedback=ft.Container(
                    content=ft.Image(src=card.image_small, width=s(60), height=s(84), fit=ft.BoxFit.CONTAIN),
                    opacity=0.85,
                ),
                data={"page": physical_page, "side": side, "pos": pos, "card": card},
                on_drag_start=lambda _, pp=physical_page, sd=side, p=pos, c=card: _on_binder_drag_start(pp, sd, p, c),
                on_drag_complete=lambda _: _on_binder_drag_complete(),
            )
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
            content=ft.Container(content=inner, width=w, height=h, border_radius=4),
            on_accept=lambda e, pp=physical_page, sd=side, p=pos: _on_drop(e, pp, sd, p),
            on_will_accept=_on_will_accept,
            on_leave=_on_leave,
        )

    # ── Spread refresh ────────────────────────────────────────────────

    def _refresh_spread() -> None:
        spread_row.controls.clear()
        b = _active_binder()
        if b is None:
            return

        left_page, left_side, right_page, right_side = _spread_sides(
            _current_spread, b.total_pages
        )

        if left_page == 0:
            left_panel = _build_cover_panel("Front Cover")
        else:
            left_panel = _build_page_panel(left_page, left_side)

        if right_page == 0:
            right_panel = _build_cover_panel("Back Cover")
        else:
            right_panel = _build_page_panel(right_page, right_side)

        # Spine divider between the two pages
        spine = ft.Container(
            width=4,
            bgcolor=COLORS["border"],
            border_radius=2,
        )

        spread_row.controls = [left_panel, spine, right_panel]

    # ── Drag handlers ─────────────────────────────────────────────────

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
            binder.place_card(dst_page, dst_side, dst_pos, incoming_card)
            state.clear_preview()
        elif payload["source"] == "binder":
            binder.swap_slots(
                payload["page"], payload["side"], payload["pos"],
                dst_page, dst_side, dst_pos,
            )

        state.drag_payload = None
        _refresh_and_update()

    def _remove_card(physical_page: int, side: int, pos: int) -> None:
        binder = _active_binder()
        if binder:
            binder.remove_card(physical_page, side, pos)
            _refresh_and_update()

    # ── Navigation ────────────────────────────────────────────────────

    def _turn_page(delta: int) -> None:
        nonlocal _current_spread
        total = _total_spreads()
        new_spread = _current_spread + delta
        if 0 <= new_spread < total:
            _current_spread = new_spread
            _refresh_and_update()

    def _on_scroll(e: ft.ScrollEvent) -> None:
        if e.scroll_delta.y < 0:
            _adjust_zoom(_ZOOM_STEP)
        else:
            _adjust_zoom(-_ZOOM_STEP)

    def _adjust_zoom(delta: float) -> None:
        nonlocal _zoom
        _zoom = round(max(_MIN_ZOOM, min(_MAX_ZOOM, _zoom + delta)), 2)
        _refresh_and_update()

    def _on_pan_update(e: ft.DragUpdateEvent) -> None:
        nonlocal _pan_offset_x, _pan_offset_y
        _pan_offset_x += e.local_delta.x
        _pan_offset_y += e.local_delta.y
        spread_row.offset = ft.Offset(
            _pan_offset_x / (page.width or 1),
            _pan_offset_y / (page.height or 1),
        )
        spread_row.update()

    def _on_pan_start(_: ft.DragStartEvent) -> None:
        pass

    spread_scroll.on_scroll = _on_scroll
    spread_scroll.on_pan_update = _on_pan_update
    spread_scroll.on_pan_start = _on_pan_start

    # ── Full refresh ──────────────────────────────────────────────────

    def _refresh_and_update() -> None:
        nonlocal _pan_offset_x, _pan_offset_y
        _pan_offset_x = 0.0
        _pan_offset_y = 0.0
        spread_row.offset = ft.Offset(0, 0)
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

    def refresh() -> None:
        nonlocal _current_spread
        _current_spread = 0
        b = _active_binder()
        if b:
            binder_title.value = f"{b.name}  ·  {b.size.value}-pocket"
            save_btn.visible = True
        else:
            binder_title.value = "No binder open"
            save_btn.visible = False
        _refresh_and_update()

    state.register_binder_listener(refresh)

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
            prev_btn,
            page_indicator,
            next_btn,
            save_btn,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )

    return ft.Column(
        [
            ft.Divider(height=1, color=COLORS["border"]),
            top_bar,
            binder_body,
        ],
        spacing=8,
        expand=True,
    )