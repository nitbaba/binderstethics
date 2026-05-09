from __future__ import annotations

import logging

import flet as ft

from src.config import GuiConfig, config as app_config
from src.scraper import Scraper, ScraperError

logger = logging.getLogger(__name__)

COLORS = {
    "bg":           "#0F1117",
    "surface":      "#1A1D27",
    "surface_2":    "#22263A",
    "accent":       "#6C63FF",
    "accent_dim":   "#3D3880",
    "success":      "#3DDC84",
    "error":        "#FF5370",
    "text_primary": "#E8E9F3",
    "text_muted":   "#6B7280",
    "border":       "#2A2D3E",
}

FONT_MONO = "monospace"

NAV_ITEMS = [
    ("Scraper",  ft.Icons.TRAVEL_EXPLORE_ROUNDED, ft.Icons.TRAVEL_EXPLORE_ROUNDED),
    ("History",  ft.Icons.HISTORY_ROUNDED,         ft.Icons.HISTORY_ROUNDED),
    ("Settings", ft.Icons.TUNE_ROUNDED,            ft.Icons.TUNE_ROUNDED),
]


def build_scraper_view(page: ft.Page) -> ft.Control:
    url_field = ft.TextField(
        value=app_config.scraper.base_url,
        hint_text="https://…",
        border_radius=10,
        filled=True,
        fill_color=COLORS["surface_2"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        color=COLORS["text_primary"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        cursor_color=COLORS["accent"],
        expand=True,
        text_size=14,
    )

    status_chip = ft.Container(
        content=ft.Text("Ready", size=12, color=COLORS["text_muted"]),
        bgcolor=COLORS["surface_2"],
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
    )

    result_text = ft.Text(
        value="Results will appear here after scraping.",
        color=COLORS["text_muted"],
        font_family=FONT_MONO,
        size=13,
        selectable=True,
    )

    result_card = ft.Container(
        content=ft.Column([result_text], scroll=ft.ScrollMode.AUTO, expand=True),
        bgcolor=COLORS["surface"],
        border_radius=12,
        padding=20,
        expand=True,
        border=ft.Border.all(1, COLORS["border"]),
    )

    progress_bar = ft.ProgressBar(
        visible=False,
        color=COLORS["accent"],
        bgcolor=COLORS["surface_2"],
        height=2,
    )

    def set_status(text: str, color: str = COLORS["text_muted"]) -> None:
        status_chip.content = ft.Text(text, size=12, color=color)  # type: ignore[union-attr]
        status_chip.update()

    async def on_scrape(_: ft.ControlEvent) -> None:
        url = url_field.value or ""
        if not url.strip():
            set_status("Enter a URL first.", COLORS["error"])
            return

        scrape_btn.disabled = True
        progress_bar.visible = True
        set_status("Scraping…", COLORS["accent"])
        result_text.value = ""
        page.update()

        try:
            async with Scraper() as scraper:
                soup = await scraper.fetch_html(url)

            title = soup.title.string.strip() if soup.title and soup.title.string else "(no <title>)"
            preview = soup.get_text(separator="\n", strip=True)[:1200]
            result_text.value = f"TITLE\n{'─' * 60}\n{title}\n\nBODY PREVIEW\n{'─' * 60}\n{preview}\n…"
            set_status("Done", COLORS["success"])
        except ScraperError as exc:
            result_text.value = f"Error: {exc}"
            set_status("Failed", COLORS["error"])
            logger.error("Scrape failed: %s", exc)
        finally:
            scrape_btn.disabled = False
            progress_bar.visible = False
            page.update()

    scrape_btn = ft.ElevatedButton(
        content=ft.Text("Scrape", color=COLORS["text_primary"]),
        bgcolor=COLORS["accent"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        height=48,
        on_click=on_scrape,
    )

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Web Scraper", size=22, weight=ft.FontWeight.W_700,
                                    color=COLORS["text_primary"]),
                            ft.Text("Fetch and parse any web page", size=13,
                                    color=COLORS["text_muted"]),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    status_chip,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=1, color=COLORS["border"]),
            progress_bar,
            ft.Row(
                [url_field, scrape_btn],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            result_card,
        ],
        spacing=16,
        expand=True,
    )


def build_history_view(_: ft.Page) -> ft.Control:
    return ft.Column(
        [
            ft.Text("History", size=22, weight=ft.FontWeight.W_700, color=COLORS["text_primary"]),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Text("No scrape history yet.", size=14, color=COLORS["text_muted"]),
        ],
        spacing=16,
    )


def build_settings_view(_: ft.Page) -> ft.Control:
    return ft.Column(
        [
            ft.Text("Settings", size=22, weight=ft.FontWeight.W_700, color=COLORS["text_primary"]),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Text("Configuration options coming soon.", size=14, color=COLORS["text_muted"]),
        ],
        spacing=16,
    )


def build_app(page: ft.Page, gui_config: GuiConfig | None = None) -> None:
    cfg = gui_config or app_config.gui

    page.title = app_config.app.name
    page.bgcolor = COLORS["bg"]
    page.window_width = cfg.window_width
    page.window_height = cfg.window_height
    page.window_min_width = 700
    page.window_min_height = 500
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.dark_theme = ft.Theme(color_scheme_seed=COLORS["accent"])
    page.theme_mode = ft.ThemeMode.DARK

    views = [
        build_scraper_view(page),
        build_history_view(page),
        build_settings_view(page),
    ]

    main_content = ft.Container(content=views[0], expand=True, padding=24)

    def on_nav_change(e: ft.ControlEvent) -> None:
        main_content.content = views[int(e.control.selected_index)]
        page.update()

    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor=COLORS["surface"],
        indicator_color=COLORS["accent_dim"],
        indicator_shape=ft.RoundedRectangleBorder(radius=10),
        leading=ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.MANAGE_SEARCH, color=COLORS["accent"], size=28),
                    ft.Text(app_config.app.name, size=12, weight=ft.FontWeight.W_600,
                            color=COLORS["text_primary"]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding.symmetric(horizontal=0, vertical=20),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=icon,
                selected_icon=icon_sel,
                label=label,
                padding=ft.Padding.symmetric(horizontal=0, vertical=4),
            )
            for label, icon, icon_sel in NAV_ITEMS
        ],
        on_change=on_nav_change,
        min_width=80,
        min_extended_width=160,
    )

    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                main_content,
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )