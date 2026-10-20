"""Shared view styling and small UI helpers."""

from __future__ import annotations

import flet as ft


COLORS: dict[str, str] = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface": "#313244",
    "surface_border": "#45475a",
    "lavender": "#b4befe",
    "text": "#cdd6f4",
    "muted": "#a6adc8",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "crust": "#11111b",
}


def notify(page: ft.Page, message: str, success: bool = True) -> None:
    """Show concise feedback using Flet's current dialog-based snackbar API."""
    page.show_dialog(
        ft.SnackBar(
            ft.Text(message, color=COLORS["base"]),
            bgcolor=COLORS["green"] if success else COLORS["red"],
            show_close_icon=True,
        )
    )
