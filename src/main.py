"""Persistent application shell for MQTT Antena Mobile."""

from __future__ import annotations

from typing import Final

import flet as ft

from mqtt_client import get_connected_broker_count, shutdown_all_sessions
from views import BrokersView, PublishView, SubscribeView


# Catppuccin Mocha design tokens, shared by the Phase 5 feature views.
MOCHA: Final[dict[str, str]] = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface": "#313244",
    "surface_border": "#45475a",
    "lavender": "#b4befe",
    "blue": "#89b4fa",
    "text": "#cdd6f4",
    "muted": "#a6adc8",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "crust": "#11111b",
}


def build_mocha_theme() -> ft.Theme:
    """Return the shared Catppuccin Mocha Material theme."""
    return ft.Theme(
        color_scheme_seed=MOCHA["lavender"],
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=MOCHA["lavender"],
            on_primary=MOCHA["base"],
            primary_container=MOCHA["surface"],
            on_primary_container=MOCHA["text"],
            secondary=MOCHA["blue"],
            on_secondary=MOCHA["base"],
            surface=MOCHA["surface"],
            on_surface=MOCHA["text"],
            on_surface_variant=MOCHA["muted"],
            outline=MOCHA["surface_border"],
            error=MOCHA["red"],
            on_error=MOCHA["base"],
        ),
        scaffold_bgcolor=MOCHA["base"],
        canvas_color=MOCHA["base"],
        card_bgcolor=MOCHA["surface"],
        divider_color=MOCHA["surface_border"],
        text_theme=ft.TextTheme(
            body_large=ft.TextStyle(color=MOCHA["text"]),
            body_medium=ft.TextStyle(color=MOCHA["text"]),
            body_small=ft.TextStyle(color=MOCHA["muted"]),
            headline_small=ft.TextStyle(color=MOCHA["text"], weight=ft.FontWeight.W_600),
            title_large=ft.TextStyle(color=MOCHA["text"], weight=ft.FontWeight.W_600),
            label_large=ft.TextStyle(color=MOCHA["text"]),
        ),
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=MOCHA["mantle"],
            indicator_color=MOCHA["surface"],
            elevation=0,
            label_text_style=ft.TextStyle(color=MOCHA["text"]),
        ),
    )


def _connection_badge(count: int) -> ft.Container:
    """Build the compact active-connection indicator in the header."""
    connected = count > 0
    color = MOCHA["green"] if connected else MOCHA["red"]
    label = f"{count} connected" if connected else "No connections"
    return ft.Container(
        padding=ft.Padding(left=10, top=6, right=10, bottom=6),
        border=ft.Border.all(1, color),
        border_radius=16,
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if connected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    size=16,
                    color=color,
                ),
                ft.Text(label, size=12, color=color, weight=ft.FontWeight.W_500),
            ],
        ),
    )


async def main(page: ft.Page) -> None:
    """Configure and display the themed shell with persistent navigation."""
    page.title = "MQTT Antena Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = build_mocha_theme()
    page.dark_theme = build_mocha_theme()
    page.bgcolor = MOCHA["base"]
    page.padding = 0

    status_badge = _connection_badge(get_connected_broker_count())
    page.appbar = ft.AppBar(
        bgcolor=MOCHA["mantle"],
        elevation=0,
        title=ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("📡 MQTT Antena Mobile", weight=ft.FontWeight.W_600),
                status_badge,
            ],
        ),
    )

    # Feature views are instantiated once, preserving their forms and log state
    # while the user moves between the persistent navigation destinations.
    views: list[ft.Control] = []
    view_host = ft.Container(expand=True, padding=20)

    def refresh_connection_indicator() -> None:
        replacement = _connection_badge(get_connected_broker_count())
        page.appbar.title.controls[1] = replacement

    def show_view(index: int) -> None:
        if index is None or not 0 <= index < len(views):
            return
        view_host.content = views[index]
        if page.navigation_bar is not None:
            page.navigation_bar.selected_index = index
        refresher = getattr(views[index], "refresh_connected_brokers", None)
        if callable(refresher):
            refresher()
        refresh_connection_indicator()
        page.update()

    brokers_view = BrokersView(page, on_sessions_changed=refresh_connection_indicator)
    subscribe_view = SubscribeView(page, go_to_brokers=lambda: show_view(0))
    publish_view = PublishView(page, go_to_brokers=lambda: show_view(0))
    views.extend([brokers_view, subscribe_view, publish_view])
    view_host.content = views[0]

    def switch_view(event: ft.Event[ft.NavigationBar]) -> None:
        index = event.control.selected_index
        if index is not None:
            show_view(index)

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=MOCHA["mantle"],
        indicator_color=MOCHA["surface"],
        on_change=switch_view,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.ROUTER_OUTLINED,
                selected_icon=ft.Icons.ROUTER,
                label="Brokers",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PODCASTS_OUTLINED,
                selected_icon=ft.Icons.PODCASTS,
                label="Subscribe",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SEND_OUTLINED,
                selected_icon=ft.Icons.SEND,
                label="Publish",
            ),
        ],
    )

    shutdown_started = False

    async def shutdown(_: ft.Event[ft.Page] | None = None) -> None:
        """Terminate MQTT loops when the Flet page session ends."""
        nonlocal shutdown_started
        if shutdown_started:
            return
        shutdown_started = True
        await shutdown_all_sessions()

    page.on_disconnect = shutdown
    page.on_close = shutdown
    page.add(ft.SafeArea(expand=True, content=view_host))


if __name__ == "__main__":
    ft.run(main)
