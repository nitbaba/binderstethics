from __future__ import annotations

import asyncio
import logging

import flet as ft

from src.api import PokemonTcgClient, PokemonTcgError, SearchResult
from src.api.scryfall import ScryfallClient, ScryfallError
from src.api.ygoprodeck import YgoClient, YgoError
from src.config import config
from src.db.models import Card, CardSource
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)

_DRAG_GROUP = "card"
_MAX_SUGGESTIONS = 8


def build_search_view(
    page: ft.Page,
    state: AppState,
    scryfall_client: ScryfallClient | None = None,
    ygo_client: YgoClient | None = None,
) -> ft.Control:

    def s(n: float) -> int:
        return max(1, int(n * state.scale_factor))

    _result: SearchResult | None = None
    _current_page = 1
    _active_tab: str = "pokemon"

    _sets_cache: dict[str, list[dict]] = {"pokemon": [], "mtg": [], "ygo": []}
    _sets_loaded: dict[str, bool] = {"pokemon": False, "mtg": False, "ygo": False}

    # ── Tab bar ────────────────────────────────────────────────────────────

    def _tab_style(active: bool) -> dict:
        return {
            "bgcolor": COLORS["surface_2"] if active else "transparent",
            "border_radius": 6,
            "padding": ft.Padding.symmetric(horizontal=12, vertical=6),
        }

    pokemon_tab_text = ft.Text(
        "Pokémon", size=12, weight=ft.FontWeight.W_600, color=COLORS["accent"]
    )
    mtg_tab_text = ft.Text(
        "MTG", size=12, weight=ft.FontWeight.W_600, color=COLORS["text_muted"]
    )
    ygo_tab_text = ft.Text(
        "Yu-Gi-Oh", size=12, weight=ft.FontWeight.W_600, color=COLORS["text_muted"]
    )

    pokemon_tab = ft.Container(
        content=pokemon_tab_text,
        on_click=lambda _: _switch_tab("pokemon"),
        **_tab_style(True),
    )
    mtg_tab = ft.Container(
        content=mtg_tab_text,
        on_click=lambda _: _switch_tab("mtg"),
        **_tab_style(False),
    )
    ygo_tab = ft.Container(
        content=ygo_tab_text,
        on_click=lambda _: _switch_tab("ygo"),
        **_tab_style(False),
    )

    tab_bar = ft.Row([pokemon_tab, mtg_tab, ygo_tab], spacing=4)

    def _switch_tab(tab: str) -> None:
        nonlocal _active_tab, _result, _current_page
        if _active_tab == tab:
            return
        _active_tab = tab
        _result = None
        _current_page = 1
        results_grid.controls.clear()
        status_text.value = ""
        _hide_suggestions()
        _update_pagination()

        for t, txt in [
            (pokemon_tab, pokemon_tab_text),
            (mtg_tab, mtg_tab_text),
            (ygo_tab, ygo_tab_text),
        ]:
            t.bgcolor = "transparent"
            txt.color = COLORS["text_muted"]

        if tab == "pokemon":
            pokemon_tab.bgcolor = COLORS["surface_2"]
            pokemon_tab_text.color = COLORS["accent"]
            set_field.hint_text = "Set name…"
        elif tab == "mtg":
            mtg_tab.bgcolor = COLORS["surface_2"]
            mtg_tab_text.color = COLORS["accent_mtg"]
            set_field.hint_text = "MTG set code or name… e.g. blb, Bloomburrow"
        else:
            ygo_tab.bgcolor = COLORS["surface_2"]
            ygo_tab_text.color = COLORS["accent_ygo"]
            set_field.hint_text = "YGO set… e.g. Legend of Blue Eyes"

        page.update()

        if not _sets_loaded[tab]:
            asyncio.ensure_future(_load_sets(tab))

    # ── Set suggestions ────────────────────────────────────────────────────
    # Rendered inside a Stack below the search bar so it naturally aligns
    # with the set field without needing absolute screen coordinates.

    suggestions_list = ft.Column(spacing=0, tight=True)

    suggestions_box = ft.Container(
        content=suggestions_list,
        bgcolor=COLORS["surface_2"],
        border=ft.Border.all(1, COLORS["border"]),
        border_radius=ft.BorderRadius(0, 0, 8, 8),
        shadow=ft.BoxShadow(
            blur_radius=12,
            color="#88000000",
            offset=ft.Offset(0, 4),
        ),
        padding=ft.Padding.symmetric(vertical=4),
        visible=False,
    )

    def _hide_suggestions() -> None:
        suggestions_box.visible = False
        try:
            suggestions_box.update()
        except Exception:
            pass

    def _show_suggestions(matches: list[str]) -> None:
        suggestions_list.controls.clear()
        for label in matches:
            row = ft.Container(
                content=ft.Text(
                    label, size=s(12), color=COLORS["text_primary"], no_wrap=True
                ),
                padding=ft.Padding.symmetric(horizontal=s(12), vertical=s(8)),
                bgcolor="transparent",
                on_click=lambda _, l=label: _select_suggestion(l),
            )

            def _make_hover(r: ft.Container):
                def _hover(e: ft.HoverEvent):
                    r.bgcolor = (
                        COLORS["surface"] if e.data == "true" else "transparent"
                    )
                    r.update()
                return _hover

            row.on_hover = _make_hover(row)
            suggestions_list.controls.append(row)

        suggestions_box.visible = True
        try:
            suggestions_box.update()
        except Exception:
            pass

    def _select_suggestion(label: str) -> None:
        if _active_tab == "mtg" and "(" in label and label.endswith(")"):
            code = label.split("(")[-1].rstrip(")")
            set_field.value = code
        else:
            set_field.value = label
        _hide_suggestions()
        set_field.update()

    def _on_set_field_change(e: ft.ControlEvent) -> None:
        typed = e.control.value.strip().lower()
        if not typed:
            _hide_suggestions()
            return

        sets = _sets_cache.get(_active_tab, [])
        if not sets:
            return

        matches: list[str] = []
        if _active_tab == "pokemon":
            for entry in sets:
                if typed in entry["name"].lower():
                    matches.append(entry["name"])
                if len(matches) >= _MAX_SUGGESTIONS:
                    break
        elif _active_tab == "mtg":
            for entry in sets:
                if typed in entry["name"].lower() or typed in entry["code"].lower():
                    matches.append(f"{entry['name']} ({entry['code']})")
                if len(matches) >= _MAX_SUGGESTIONS:
                    break
        else:
            for entry in sets:
                if typed in entry["set_name"].lower():
                    matches.append(entry["set_name"])
                if len(matches) >= _MAX_SUGGESTIONS:
                    break

        if matches:
            _show_suggestions(matches)
        else:
            _hide_suggestions()

    async def _load_sets(tab: str) -> None:
        try:
            if tab == "pokemon":
                async with PokemonTcgClient(config.api.pokemon_tcg_api_key) as client:
                    sets = await client.fetch_sets()
                _sets_cache["pokemon"] = sets
            elif tab == "mtg" and scryfall_client:
                sets = await scryfall_client.fetch_sets()
                _sets_cache["mtg"] = sets
            elif tab == "ygo" and ygo_client:
                sets = await ygo_client.fetch_sets()
                _sets_cache["ygo"] = sets
            _sets_loaded[tab] = True
            logger.info("Loaded %d sets for tab %s", len(_sets_cache[tab]), tab)
        except Exception as exc:
            logger.warning("Failed to load sets for %s: %s", tab, exc)

    asyncio.ensure_future(_load_sets("pokemon"))

    # ── Widgets ────────────────────────────────────────────────────────────

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
        on_change=_on_set_field_change,
        on_submit=lambda _: (_hide_suggestions(), asyncio.ensure_future(_do_search())),
    )

    search_btn = ft.ElevatedButton(
        content=ft.Text("Search", color=COLORS["text_primary"]),
        bgcolor=COLORS["accent"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        height=48,
        on_click=lambda _: (_hide_suggestions(), asyncio.ensure_future(_do_search())),
    )

    status_text = ft.Text("", size=12, color=COLORS["text_muted"])
    loading_ring = ft.ProgressRing(
        width=16, height=16, color=COLORS["accent"], visible=False
    )

    results_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=220,
        spacing=6,
        run_spacing=6,
        padding=ft.Padding.symmetric(vertical=4, horizontal=4),
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
        width=s(300),
        height=s(420),
        fit=ft.BoxFit.CONTAIN,
        border_radius=8,
        visible=False,
    )

    preview_name = ft.Text(
        "", size=s(13), weight=ft.FontWeight.W_600, color=COLORS["text_primary"]
    )
    preview_set = ft.Text("", size=s(11), color=COLORS["text_muted"])
    preview_number = ft.Text("", size=s(11), color=COLORS["text_muted"])

    close_preview_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=COLORS["text_muted"],
        icon_size=s(16),
        visible=False,
        on_click=lambda _: _clear_preview(),
    )

    preview_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Preview", size=s(12), color=COLORS["text_muted"]),
                        close_preview_btn,
                    ],
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
        width=max(200, int(page.width * 0.22)),
        border=ft.Border.all(1, COLORS["border"]),
    )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_loading(active: bool) -> None:
        loading_ring.visible = active
        search_btn.disabled = active
        page.update()

    def _update_pagination() -> None:
        if _result is None or _result.total_count == 0:
            prev_btn.disabled = True
            next_btn.disabled = True
            page_label.value = ""
            return
        prev_btn.disabled = _current_page <= 1
        next_btn.disabled = _current_page >= _result.total_pages
        page_label.value = f"{_current_page} / {_result.total_pages}"

    def _render_results(cards: list[Card]) -> None:
        results_grid.controls.clear()
        for card in cards:
            results_grid.controls.append(_build_card_tile(card))

    def _source_color(source: CardSource) -> str:
        if source == CardSource.MTG:
            return COLORS["accent_mtg"]
        if source == CardSource.YGO:
            return COLORS["accent_ygo"]
        return COLORS["accent"]

    def _build_card_tile(card: Card) -> ft.Control:
        tw = s(80)
        th = s(112)

        thumbnail = ft.Image(
            src=card.image_small,
            width=tw,
            height=th,
            fit=ft.BoxFit.CONTAIN,
            border_radius=4,
        )

        draggable_thumbnail = ft.Draggable(
            group=_DRAG_GROUP,
            content=thumbnail,
            content_feedback=ft.Container(
                content=ft.Image(
                    src=card.image_small,
                    width=s(60),
                    height=s(84),
                    fit=ft.BoxFit.CONTAIN,
                ),
                opacity=0.85,
            ),
            data=card,
            on_drag_start=lambda _: _on_drag_start(card),
            on_drag_complete=lambda _: _on_drag_complete(),
        )

        source_dot = ft.Container(
            width=6, height=6,
            border_radius=3,
            bgcolor=_source_color(card.source),
            tooltip=card.source.value.upper(),
        )

        info_col = ft.Column(
            [
                ft.Text(
                    card.name,
                    size=s(11),
                    weight=ft.FontWeight.W_600,
                    color=COLORS["text_primary"],
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    card.set_name,
                    size=s(10),
                    color=COLORS["text_muted"],
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row(
                    [ft.Text(f"#{card.number}", size=s(10), color=COLORS["text_muted"]), source_dot],
                    spacing=4,
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Column(
                [draggable_thumbnail, info_col],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"],
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=6, vertical=8),
            border=ft.Border.all(1, COLORS["border"]),
            on_click=lambda _, c=card: _show_preview(c),
        )

    def _show_preview(card: Card) -> None:
        preview_image.src = card.image_large
        preview_image.width = s(300)
        preview_image.height = s(420)
        preview_image.visible = True
        preview_name.value = card.name
        preview_name.size = s(13)
        preview_set.value = card.set_name
        preview_set.size = s(11)
        preview_number.value = f"#{card.number}"
        preview_number.size = s(11)
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

    def _on_drag_complete() -> None:
        state.drag_payload = None

    # ── Scale refresh ──────────────────────────────────────────────────────

    def _on_scale_change() -> None:
        preview_image.width = s(300)
        preview_image.height = s(420)
        preview_name.size = s(13)
        preview_set.size = s(11)
        preview_number.size = s(11)
        close_preview_btn.icon_size = s(16)
        preview_panel.width = max(200, int(page.width * 0.22))
        if _result:
            _render_results(_result.cards)
        page.update()

    state.register_scale_listener(_on_scale_change)

    # ── Async actions ──────────────────────────────────────────────────────

    async def _do_search(reset_page: bool = True) -> None:
        nonlocal _result, _current_page
        if reset_page:
            _current_page = 1

        _set_loading(True)
        status_text.value = "Searching…"

        try:
            if _active_tab == "pokemon":
                async with PokemonTcgClient(config.api.pokemon_tcg_api_key) as client:
                    _result = await client.search_cards(
                        name=name_field.value or "",
                        set_name=set_field.value or "",
                        page=_current_page,
                    )
            elif _active_tab == "mtg":
                if scryfall_client is None:
                    status_text.value = "MTG search not available."
                    _set_loading(False)
                    return
                _result = await scryfall_client.search(
                    name=name_field.value or "",
                    set_name=set_field.value or "",
                    page=_current_page,
                )
            else:
                if ygo_client is None:
                    status_text.value = "Yu-Gi-Oh search not available."
                    _set_loading(False)
                    return
                _result = await ygo_client.search(
                    name=name_field.value or "",
                    set_name=set_field.value or "",
                    page=_current_page,
                )

        except (PokemonTcgError, ScryfallError, YgoError) as exc:
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

    # ── Layout ─────────────────────────────────────────────────────────────
    # The set field and its suggestions box sit in a Column so the dropdown
    # appears directly below the field, naturally aligned.

    set_field_col = ft.Column(
        [set_field, suggestions_box],
        spacing=0,
        expand=True,
    )

    search_bar = ft.Row(
        [name_field, set_field_col, search_btn, loading_ring],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    pagination_row = ft.Row(
        [prev_btn, page_label, next_btn, ft.Container(expand=True), status_text],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    results_panel = ft.Column(
        [pagination_row, results_grid],
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
        [tab_bar, search_bar, body],
        spacing=10,
        expand=True,
    )