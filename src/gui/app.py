from __future__ import annotations

import logging

import flet as ft

from src.config import config
from src.db import Database
from src.gui.colors import COLORS
from src.gui.sidebar import build_sidebar
from src.gui.state import AppState
from src.gui.views.binder_view import build_binder_view
from src.gui.views.search_view import build_search_view

logger = logging.getLogger(__name__)


def build_app(page: ft.Page) -> None:
    cfg = config.gui
    db = Database(config.db.path)
    state = AppState()

    # ── Page setup ───────────────────────────────────────────────────

    page.title = f"{config.app.name} — {cfg.window_width}×{cfg.window_height}"
    page.bgcolor = COLORS["bg"]
    page.window.width = cfg.window_width
    page.window.height = cfg.window_height
    page.window.min_width = 900
    page.window.min_height = 600
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.dark_theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.theme_mode = ft.ThemeMode.DARK

    # ── Save helper ──────────────────────────────────────────────────

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

    # ── Window close: auto-save ──────────────────────────────────────

    def _on_close(_: ft.ControlEvent) -> None:
        if state.active_binder is not None:
            db.save_binder(state.active_binder)
            logger.info("Auto-saved on close: binder id=%d", state.active_binder.id)
        db.close()

    page.on_close = _on_close

    # ── Build views ──────────────────────────────────────────────────

    sidebar = build_sidebar(page, state, db)

    search_view = build_search_view(page, state)

    binder_view = build_binder_view(page, state, on_save=_save_active_binder)

    main_area = ft.Column(
        [
            ft.Container(content=search_view, expand=True, padding=16),
            ft.Container(content=binder_view, expand=True, padding=ft.Padding.only(left=16, right=16, bottom=16, top=0)),
        ],
        spacing=0,
        expand=True,
    )

    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                main_area,
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )
