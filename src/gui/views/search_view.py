from __future__ import annotations

import asyncio
import logging

import flet as ft

from src.api import PokemonTcgClient, PokemonTcgError, SearchResult
from src.config import config
from src.db.models import Card
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)

_DRAG_GROUP = "card"
_THUMBNAIL_W = 80
_THUMBNAIL_H = 112


def build_search_view(page: ft.Page, state: AppState) -> ft.Control:
    """Top half of the main area.

    Layout: [search controls] → [results list | preview panel]
    """

    # ── Internal state ───────────────────────────────────────────────
    _result: SearchResult | None = None
    _current_page = 1

    # ── Widgets ──────────────────────────────────────────────────────
    name_field = ft.TextField(
        hint_text="Card name…",
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        color=COLORS["text_primary"],
        fill_color=COLORS["surface_2"],
        filled=True,
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        cursor_color=COLORS["accent"],
        expand=True,
        on_submit=lambda _: asyncio.ensure_future(_do_search()),
    )

    set_field = ft.TextField(
        hint_text="Set name…",
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        color=COLORS["text_primary"],
        fill_color=COLORS["surface_2"],
        filled=True,
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        cursor_color=COLORS["accent"],
        expand=True,
        on_submit=lambda _: asyncio.ensure_future(_do_search()),
    )

    search_btn = ft.ElevatedButton(
        content=ft.Text("Search", color=COLORS["text_primary"]),
        bgcolor=COLORS["accent"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        height=48,
        on_click=lambda _: asyncio.ensure_future(_do_search()),
    )

    status_text = ft.Text("", size=12, color=COLORS["text_muted"])
    loading_ring = ft.ProgressRing(
        width=16, height=16, color=COLORS["accent"], visible=False
    )

    results_list = ft.ListView(
        expand=True,
        spacing=4,
        padding=ft.Padding.symmetric(vertical=4, horizontal=0),
    )

    prev_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: asyncio.ensure_future(_go_prev()),
    )

    next_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        icon_color=COLORS["text_primary"],
        disabled=True,
        on_click=lambda _: asyncio.ensure_future(_go_next()),
    )

    page_label = ft.Text("", size=12, color=COLORS["text_muted"])

    preview_image = ft.Image(
        src="",
        width=220,
        height=308,
        fit=ft.BoxFit.CONTAIN,
        border_radius=8,
        visible=False,
    )

    preview_name = ft.Text("", size=13, weight=ft.FontWeight.W_600,
                           color=COLORS["text_primary"])
    preview_set = ft.Text("", size=11, color=COLORS["text_muted"])
    preview_number = ft.Text("", size=11, color=COLORS["text_muted"])

    close_preview_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=COLORS["text_muted"],
        icon_size=16,
        visible=False,
        on_click=lambda _: _clear_preview(),
    )

    preview_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Text("Preview", size=12, color=COLORS["text_muted"]), close_preview_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                preview_image,
                preview_name,
                preview_set,
                preview_number,
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS["surface"],
        border_radius=10,
        padding=12,
        width=248,
        border=ft.Border.all(1, COLORS["border"]),
    )

    # ── Helpers ──────────────────────────────────────────────────────

    def _set_loading(active: bool) -> None:
        loading_ring.visible = active
        search_btn.disabled = active
        page.update()

    def _update_pagination() -> None:
        nonlocal _result
        if _result is None or _result.total_count == 0:
            prev_btn.disabled = True
            next_btn.disabled = True
            page_label.value = ""
            return
        prev_btn.disabled = _current_page <= 1
        next_btn.disabled = _current_page >= _result.total_pages
        page_label.value = f"{_current_page} / {_result.total_pages}"

    def _render_results(cards: list[Card]) -> None:
        results_list.controls.clear()
        for card in cards:
            results_list.controls.append(_build_card_row(card))

    def _build_card_row(card: Card) -> ft.Control:
        thumbnail = ft.Image(
            src=card.image_small,
            width=_THUMBNAIL_W,
            height=_THUMBNAIL_H,
            fit=ft.BoxFit.CONTAIN,
            border_radius=4,
        )

        draggable_thumbnail = ft.Draggable(
            group=_DRAG_GROUP,
            content=thumbnail,
            content_feedback=ft.Container(
                content=ft.Image(
                    src=card.image_small,
                    width=60,
                    height=84,
                    fit=ft.BoxFit.CONTAIN,
                ),
                opacity=0.85,
            ),
            data=card,
            on_drag_start=lambda _: _on_drag_start(card),
            on_drag_complete=lambda _: _on_drag_complete(),
        )

        info_col = ft.Column(
            [
                ft.Text(card.name, size=13, weight=ft.FontWeight.W_600,
                        color=COLORS["text_primary"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(card.set_name, size=11, color=COLORS["text_muted"]),
                ft.Text(f"#{card.number}", size=11, color=COLORS["text_muted"]),
            ],
            spacing=2,
            expand=True,
        )

        row = ft.Container(
            content=ft.Row(
                [draggable_thumbnail, info_col],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"],
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            border=ft.Border.all(1, COLORS["border"]),
            on_click=lambda _, c=card: _show_preview(c),
        )
        return row

    def _show_preview(card: Card) -> None:
        preview_image.src = card.image_large
        preview_image.visible = True
        preview_name.value = card.name
        preview_set.value = card.set_name
        preview_number.value = f"#{card.number}"
        close_preview_btn.visible = True
        state.set_preview(card)
        page.update()

    def _clear_preview() -> None:
        preview_image.visible = False
        preview_image.src = ""
        preview_name.value = ""
        preview_set.value = ""
        preview_number.value = ""
        close_preview_btn.visible = False
        state.clear_preview()
        page.update()

    def _on_drag_start(card: Card) -> None:
        state.drag_payload = {"source": "search", "card": card}
        # Close preview when drag begins and card ends up in binder area.
        # The binder drop handler will call clear_preview if drop succeeds.

    def _on_drag_complete() -> None:
        state.drag_payload = None

    # ── Async actions ─────────────────────────────────────────────────

    async def _do_search(reset_page: bool = True) -> None:
        nonlocal _result, _current_page
        if reset_page:
            _current_page = 1

        _set_loading(True)
        status_text.value = "Searching…"

        try:
            async with PokemonTcgClient(config.api.pokemon_tcg_api_key) as client:
                _result = await client.search_cards(
                    name=name_field.value or "",
                    set_name=set_field.value or "",
                    page=_current_page,
                )
        except PokemonTcgError as exc:
            status_text.value = f"Error: {exc}"
            logger.error("Search failed: %s", exc)
            _set_loading(False)
            return

        _render_results(_result.cards)
        _update_pagination()

        if _result.total_count == 0:
            status_text.value = "No results."
        else:
            start = (_current_page - 1) * _result.page_size + 1
            end = min(_current_page * _result.page_size, _result.total_count)
            status_text.value = f"{start}–{end} of {_result.total_count} cards"

        _set_loading(False)

    async def _go_prev() -> None:
        nonlocal _current_page
        if _current_page > 1:
            _current_page -= 1
            await _do_search(reset_page=False)

    async def _go_next() -> None:
        nonlocal _current_page
        if _result and _current_page < _result.total_pages:
            _current_page += 1
            await _do_search(reset_page=False)

    # ── Layout ───────────────────────────────────────────────────────

    search_bar = ft.Row(
        [name_field, set_field, search_btn, loading_ring],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    pagination_row = ft.Row(
        [prev_btn, page_label, next_btn, ft.Container(expand=True), status_text],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    results_panel = ft.Column(
        [pagination_row, results_list],
        spacing=4,
        expand=True,
    )

    body = ft.Row(
        [results_panel, preview_panel],
        spacing=12,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    return ft.Column(
        [search_bar, body],
        spacing=10,
        expand=True,
    )
