from __future__ import annotations

import logging

import flet as ft

from src.db import Database, Binder, BinderSize
from src.gui.colors import COLORS
from src.gui.state import AppState

logger = logging.getLogger(__name__)

_SIZE_LABELS = {
    BinderSize.FOUR: "4-Pocket",
    BinderSize.NINE: "9-Pocket",
    BinderSize.TWELVE: "12-Pocket",
    BinderSize.SIXTEEN: "16-Pocket",
}

_BINDER_COUNTER: dict[BinderSize, int] = {s: 0 for s in BinderSize}


def build_sidebar(
    page: ft.Page,
    state: AppState,
    db: Database,
    on_show_settings: callable,
) -> ft.Control:

    def s(n: float) -> int:
        return max(1, int(n * state.scale_factor))

    binder_list_col = ft.Column([], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    new_size_dropdown = ft.Dropdown(
        options=[ft.DropdownOption(key=str(sv.value), text=_SIZE_LABELS[sv]) for sv in BinderSize],
        value=str(BinderSize.NINE.value),
        bgcolor=COLORS["surface_2"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        color=COLORS["text_primary"],
        border_radius=8,
        expand=True,
    )

    add_btn = ft.IconButton(
        icon=ft.Icons.ADD,
        icon_color=COLORS["accent"],
        icon_size=s(20),
        on_click=lambda _: _create_binder(),
    )

    settings_btn = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SETTINGS, color=COLORS["text_muted"], size=s(16)),
                ft.Text("Settings", size=s(13), color=COLORS["text_muted"]),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLORS["surface"],
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        margin=ft.Margin(left=4, right=4, top=2, bottom=8),
        on_click=lambda _: on_show_settings(),
    )

    _binders: list[Binder] = []
    _active_id: int | None = None

    def _load_and_render() -> None:
        nonlocal _binders
        _binders = db.list_binders()
        _render_list()

    def _render_list() -> None:
        binder_list_col.controls.clear()
        grouped: dict[BinderSize, list[Binder]] = {sv: [] for sv in BinderSize}
        for b in _binders:
            grouped[b.size].append(b)
        for size in BinderSize:
            group = grouped[size]
            if not group:
                continue
            binder_list_col.controls.append(
                ft.Container(
                    content=ft.Text(
                        _SIZE_LABELS[size].upper(),
                        size=s(10),
                        weight=ft.FontWeight.W_700,
                        color=COLORS["text_muted"],
                    ),
                    padding=ft.Padding.only(left=12, top=12, bottom=4, right=0),
                )
            )
            for binder in group:
                binder_list_col.controls.append(_build_binder_row(binder))
        try:
            binder_list_col.update()
        except RuntimeError:
            pass

    def _build_binder_row(binder: Binder) -> ft.Control:
        is_active = binder.id == _active_id
        capacity = binder.total_pages * 2 * binder.pockets_per_side
        filled = sum(1 for sl in binder.slots.values() if sl.card is not None)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(binder.name, size=s(13), color=COLORS["text_primary"],
                                    expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{filled}/{capacity}", size=s(10), color=COLORS["text_muted"]),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_color=COLORS["text_muted"],
                        icon_size=s(16),
                        items=[
                            ft.PopupMenuItem(
                                content=ft.Text("Rename", color=COLORS["text_primary"]),
                                on_click=lambda _, b=binder: _prompt_rename(b),
                            ),
                            ft.PopupMenuItem(
                                content=ft.Text("Delete", color=COLORS["error"]),
                                on_click=lambda _, b=binder: _confirm_delete(b),
                            ),
                        ],
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=COLORS["accent_dim"] if is_active else COLORS["surface"],
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            margin=ft.Margin(left=4, right=4, top=2, bottom=2),
            on_click=lambda _, b=binder: _open_binder(b),
        )

    def _create_binder() -> None:
        size_value = int(new_size_dropdown.value or str(BinderSize.NINE.value))
        size = BinderSize(size_value)
        _BINDER_COUNTER[size] += 1
        binder = db.create_binder(f"{_SIZE_LABELS[size]} #{_BINDER_COUNTER[size]}", size)
        _binders.append(binder)
        _render_list()

    def _open_binder(binder: Binder) -> None:
        nonlocal _active_id
        if state.active_binder is not None and state.active_binder.id != binder.id:
            db.save_binder(state.active_binder)
        _active_id = binder.id
        state.active_binder = binder
        state.notify_binder_changed()
        _render_list()

    def _prompt_rename(binder: Binder) -> None:
        name_field = ft.TextField(
            value=binder.name, color=COLORS["text_primary"], fill_color=COLORS["surface_2"],
            filled=True, border_radius=8, border_color=COLORS["border"],
            focused_border_color=COLORS["accent"], cursor_color=COLORS["accent"], autofocus=True,
        )
        def _do_rename(_: ft.ControlEvent) -> None:
            new_name = name_field.value.strip()
            if new_name:
                db.rename_binder(binder.id, new_name)
                binder.name = new_name
                if state.active_binder and state.active_binder.id == binder.id:
                    state.active_binder.name = new_name
                    state.notify_binder_changed()
            dlg.open = False
            _render_list()
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text("Rename Binder", color=COLORS["text_primary"]),
            content=name_field, bgcolor=COLORS["surface"],
            actions=[
                ft.TextButton(content=ft.Text("Cancel", color=COLORS["text_muted"]),
                              on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.TextButton(content=ft.Text("Rename", color=COLORS["accent"]),
                              on_click=_do_rename),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _confirm_delete(binder: Binder) -> None:
        def _do_delete(_: ft.ControlEvent) -> None:
            db.delete_binder(binder.id)
            _binders.remove(binder)
            if state.active_binder and state.active_binder.id == binder.id:
                state.active_binder = None
                state.notify_binder_changed()
            dlg.open = False
            _render_list()
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text("Delete Binder?", color=COLORS["text_primary"]),
            content=ft.Text(f'"{binder.name}" will be permanently deleted.', color=COLORS["text_muted"]),
            bgcolor=COLORS["surface"],
            actions=[
                ft.TextButton(content=ft.Text("Cancel", color=COLORS["text_muted"]),
                              on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                ft.TextButton(content=ft.Text("Delete", color=COLORS["error"]),
                              on_click=_do_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _on_scale_change() -> None:
        add_btn.icon_size = s(20)
        settings_btn.content = ft.Row(
            [
                ft.Icon(ft.Icons.SETTINGS, color=COLORS["text_muted"], size=s(16)),
                ft.Text("Settings", size=s(13), color=COLORS["text_muted"]),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        sidebar_container.width = max(180, int(page.width * 0.12))
        _render_list()
        page.update()

    state.register_scale_listener(_on_scale_change)
    _load_and_render()

    sidebar_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text("BINDERS", size=s(11), weight=ft.FontWeight.W_700,
                                    color=COLORS["text_muted"]),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=12),
                ),
                binder_list_col,
                ft.Divider(height=1, color=COLORS["border"]),
                ft.Container(
                    content=ft.Row([new_size_dropdown, add_btn], spacing=4,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                ),
                settings_btn,
            ],
            spacing=0,
            expand=True,
        ),
        bgcolor=COLORS["surface"],
        border_radius=0,
        width=max(180, int(page.width * 0.12)),
        expand=False,
    )
    return sidebar_container