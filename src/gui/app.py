from __future__ import annotations

import logging

import flet as ft

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

    # Load persisted preset before touching the window.
    state.active_preset = db.get_preset()

    # ── Page setup ───────────────────────────────────────────────────

    page.title = f"{config.app.name}"
    page.bgcolor = COLORS["bg"]
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.dark_theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.theme_mode = ft.ThemeMode.DARK

    # ── Preset application ───────────────────────────────────────────

    def _apply_preset(preset: Preset, *, save: bool = True) -> None:
        state.active_preset = preset
        if save:
            db.save_preset(preset)

        if preset.fullscreen:
            page.window.full_screen = True
        else:
            page.window.full_screen = False
            page.window.width = preset.width
            page.window.height = preset.height

        sidebar.width = _sidebar_width()
        state.notify_binder_changed()
        state.notify_scale_changed()
        page.update()

    def _sidebar_width() -> int:
        return max(180, int(page.width * 0.12))

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

    # ── Window close ─────────────────────────────────────────────────

    def _on_close(_: ft.ControlEvent) -> None:
        if state.active_binder is not None:
            db.save_binder(state.active_binder)
            logger.info("Auto-saved on close: binder id=%d", state.active_binder.id)
        db.close()

    page.on_close = _on_close

    # ── Build views ──────────────────────────────────────────────────

    search_view = build_search_view(page, state)
    binder_view = build_binder_view(page, state, on_save=_save_active_binder)

    main_content = ft.Container(
        content=ft.Column(
            [
                ft.Container(content=search_view, expand=True, padding=16),
                ft.Container(
                    content=binder_view,
                    expand=True,
                    padding=ft.Padding.only(left=16, right=16, bottom=16, top=0),
                ),
            ],
            spacing=0,
            expand=True,
        ),
        expand=True,
    )

    settings_view = build_settings_view(
        page, state, db, on_preset_apply=_apply_preset
    )

    settings_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(content=settings_view, expand=True, padding=24),
            ],
            expand=True,
        ),
        expand=True,
        visible=False,
    )

    # Overlay: either main content or settings
    content_stack = ft.Stack(
        [main_content, settings_container],
        expand=True,
    )

    def _show_settings() -> None:
        settings_container.visible = True
        main_content.visible = False
        page.update()

    def _hide_settings() -> None:
        settings_container.visible = False
        main_content.visible = True
        page.update()

    # Add a back button to the settings view header area
    settings_view_wrapped = ft.Column(
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
    )
    settings_container.content = ft.Container(
        content=settings_view_wrapped, expand=True, padding=24
    )

    sidebar = build_sidebar(page, state, db, on_show_settings=_show_settings)

    # ── on_resize: snap to nearest preset ────────────────────────────

    def _on_resize(_: ft.ControlEvent) -> None:
        # Don't snap if fullscreen is active.
        if state.active_preset.fullscreen:
            return

        snapped = nearest_preset(page.width, page.height)
        if snapped.key != state.active_preset.key:
            # Apply without saving — manual resizes don't persist.
            _apply_preset(snapped, save=False)
        else:
            # Same preset, just reflow layout.
            sidebar.width = _sidebar_width()
            state.notify_binder_changed()
            page.update()

    page.on_resize = _on_resize

    # ── Apply initial preset (no save, already persisted) ────────────
    _apply_preset(state.active_preset, save=False)

    # ── Root layout ──────────────────────────────────────────────────

    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                content_stack,
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )