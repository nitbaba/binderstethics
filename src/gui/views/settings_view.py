from __future__ import annotations

import logging

import flet as ft

from src.db import Database, Preset, PRESETS
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)


def build_settings_view(
    page: ft.Page,
    state: AppState,
    db: Database,
    on_preset_apply: callable,  # type: ignore[type-arg]
) -> ft.Control:
    """Settings page — display preset selector."""

    def _build_preset_card(preset: Preset) -> ft.Control:
        is_active = preset.key == state.active_preset.key

        if preset.fullscreen:
            sub = "Fills the entire screen"
        else:
            sub = f"{preset.width} × {preset.height}  ·  scale {preset.scale_factor:.2f}×"

        indicator = ft.Container(
            width=10,
            height=10,
            border_radius=5,
            bgcolor=COLORS["success"] if is_active else COLORS["surface_2"],
            border=ft.Border.all(1, COLORS["border"]),
        )

        return ft.Container(
            content=ft.Row(
                [
                    indicator,
                    ft.Column(
                        [
                            ft.Text(
                                preset.label,
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=COLORS["text_primary"],
                            ),
                            ft.Text(sub, size=12, color=COLORS["text_muted"]),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        content=ft.Text(
                            "Active" if is_active else "Apply",
                            color=COLORS["text_primary"],
                            size=12,
                        ),
                        bgcolor=COLORS["accent_dim"] if is_active else COLORS["accent"],
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        height=34,
                        disabled=is_active,
                        on_click=lambda _, p=preset: _apply(p),
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["surface"] if not is_active else COLORS["surface_2"],
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border=ft.Border.all(
                2 if is_active else 1,
                COLORS["accent"] if is_active else COLORS["border"],
            ),
        )

    preset_col = ft.Column(spacing=8)

    def _render() -> None:
        preset_col.controls = [_build_preset_card(p) for p in PRESETS]
        try:
            preset_col.update()
        except RuntimeError:
            pass

    def _apply(preset: Preset) -> None:
        state.active_preset = preset
        db.save_preset(preset)
        on_preset_apply(preset)
        _render()

    _render()

    return ft.Column(
        [
            ft.Text(
                "Display",
                size=18,
                weight=ft.FontWeight.W_700,
                color=COLORS["text_primary"],
            ),
            ft.Text(
                "Choose a resolution preset. The window will resize and all "
                "UI elements will scale accordingly.",
                size=13,
                color=COLORS["text_muted"],
            ),
            ft.Divider(height=1, color=COLORS["border"]),
            preset_col,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )