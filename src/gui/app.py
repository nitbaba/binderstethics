from __future__ import annotations

import asyncio
import logging

import flet as ft

from src.api.scryfall import ScryfallClient
from src.api.ygoprodeck import YgoClient
from src.config import config
from src.db import Database, nearest_preset
from src.db.models import Preset
from src.gui.colors import COLORS
from src.gui.sidebar import build_sidebar
from src.gui.state import AppState
from src.gui.views.binder_view import build_binder_view
from src.gui.views.search_view import build_search_view
from src.gui.views.settings_view import build_settings_view

logger = logging.getLogger(__name__)


def build_app(page: ft.Page) -> None:
    db = Database(config.db.path)
    state = AppState()
    state.active_preset = db.get_preset()

    scryfall_client = ScryfallClient()
    ygo_client = YgoClient()

    page.title = config.app.name
    page.bgcolor = COLORS["bg"]
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.dark_theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.theme_mode = ft.ThemeMode.DARK

    # ── Helpers ────────────────────────────────────────────────────────────

    def _sidebar_width() -> int:
        return max(180, int(page.width * 0.12))

    def _save_active_binder() -> None:
        if state.active_binder is not None:
            db.save_binder(state.active_binder)
            _show_snack("Binder saved.")
            logger.info("Manual save: binder id=%d", state.active_binder.id)

    def _show_snack(message: str) -> None:
        snack = ft.SnackBar(
            content=ft.Text(message, color=COLORS["text_primary"]),
            bgcolor=COLORS["surface_2"],
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def _on_close(_: ft.ControlEvent) -> None:
        if state.active_binder is not None:
            db.save_binder(state.active_binder)
            logger.info("Auto-saved on close: binder id=%d", state.active_binder.id)
        db.close()
        async def _cleanup():
            await asyncio.gather(scryfall_client.aclose(), ygo_client.aclose())
        asyncio.run_coroutine_threadsafe(_cleanup(), page.loop)

    page.on_close = _on_close

    # ── Shell containers (content replaced on every rebuild) ───────────────

    search_container = ft.Container(expand=True, padding=16)
    binder_container = ft.Container(
        expand=True,
        padding=ft.Padding.only(left=16, right=16, bottom=16, top=0),
    )
    sidebar_container = ft.Container(expand=False)

    main_content = ft.Container(
        content=ft.Column(
            [search_container, binder_container],
            spacing=0,
            expand=True,
        ),
        expand=True,
    )

    settings_container = ft.Container(expand=True, visible=False)
    content_stack = ft.Stack([main_content, settings_container], expand=True)

    def _show_settings() -> None:
        settings_container.visible = True
        main_content.visible = False
        page.update()

    def _hide_settings() -> None:
        settings_container.visible = False
        main_content.visible = True
        page.update()

    # ── Rebuild ────────────────────────────────────────────────────────────

    def _rebuild_views() -> None:
        state.clear_listeners()

        search_container.content = build_search_view(
            page, state, scryfall_client=scryfall_client, ygo_client=ygo_client
        )
        binder_container.content = build_binder_view(
            page, state, on_save=_save_active_binder
        )

        new_sidebar = build_sidebar(
            page, state, db, on_show_settings=_show_settings
        )
        sidebar_container.content = new_sidebar
        sidebar_container.width = _sidebar_width()

        settings_view = build_settings_view(
            page, state, db, _apply_preset
        )
        settings_container.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color=COLORS["text_muted"],
                                on_click=lambda _: _hide_settings(),
                            ),
                            ft.Text(
                                "Settings",
                                size=16,
                                weight=ft.FontWeight.W_700,
                                color=COLORS["text_primary"],
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Container(content=settings_view, expand=True),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            padding=24,
        )

        page.update()

    # ── Preset application ─────────────────────────────────────────────────

    def _apply_preset(preset: Preset, *, save: bool = True) -> None:
        asyncio.ensure_future(_apply_preset_async(preset, save=save))

    async def _apply_preset_async(preset: Preset, *, save: bool = True) -> None:
        state.active_preset = preset
        if save:
            db.save_preset(preset)

        if preset.fullscreen:
            page.window.full_screen = True
        else:
            page.window.full_screen = False
            page.window.width = preset.width
            page.window.height = preset.height

        page.update()
        await asyncio.sleep(0.2)
        _rebuild_views()

    # ── on_resize ──────────────────────────────────────────────────────────

    def _on_resize(_: ft.ControlEvent) -> None:
        if state.active_preset.fullscreen:
            return
        snapped = nearest_preset(page.width, page.height)
        if snapped.key != state.active_preset.key:
            state.active_preset = snapped
        _rebuild_views()

    page.on_resize = _on_resize

    # ── Root layout ────────────────────────────────────────────────────────

    page.add(
        ft.Row(
            [
                sidebar_container,
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                content_stack,
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )

    # ── Apply initial preset ───────────────────────────────────────────────

    initial = state.active_preset
    if initial.fullscreen:
        page.window.full_screen = True
    else:
        page.window.full_screen = False
        page.window.width = initial.width
        page.window.height = initial.height

    _rebuild_views()