"""Broker profile management view."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from models import BrokerProfile, ConnectionStatus
from mqtt_client import connect_broker, disconnect_broker, get_active_session
from storage import StorageEngine, get_storage_engine
from views.common import COLORS, notify


class BrokersView(ft.Column):
    """List, edit, and connect locally persisted broker profiles."""

    def __init__(
        self,
        page: ft.Page,
        storage: StorageEngine | None = None,
        on_sessions_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16)
        self.app_page = page
        self.storage = storage or get_storage_engine()
        self.on_sessions_changed = on_sessions_changed or (lambda: None)
        self.cards = ft.Column(spacing=10)
        self.controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=2,
                        controls=[
                            ft.Text("Brokers", size=24, weight=ft.FontWeight.W_600),
                            ft.Text("Saved MQTT connection profiles", color=COLORS["muted"]),
                        ],
                    ),
                    ft.FilledButton(
                        "Add broker",
                        icon=ft.Icons.ADD,
                        bgcolor=COLORS["lavender"],
                        color=COLORS["base"],
                        on_click=self.open_add_dialog,
                    ),
                ],
            ),
            self.cards,
        ]
        self.refresh()

    def _status(self, broker_id: int | None) -> ConnectionStatus:
        session = get_active_session(broker_id) if broker_id is not None else None
        return session.status if session else ConnectionStatus.DISCONNECTED

    def _status_badge(self, status: ConnectionStatus) -> ft.Container:
        colors = {
            ConnectionStatus.CONNECTED: COLORS["green"],
            ConnectionStatus.CONNECTING: COLORS["yellow"],
            ConnectionStatus.ERROR: COLORS["red"],
            ConnectionStatus.DISCONNECTED: COLORS["red"],
        }
        color = colors[status]
        label = "Connecting…" if status == ConnectionStatus.CONNECTING else status.display_name
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border=ft.Border.all(1, color),
            border_radius=12,
            content=ft.Text(label, size=12, color=color),
        )

    def _card(self, broker: BrokerProfile) -> ft.Container:
        status = self._status(broker.id)
        connected = status == ConnectionStatus.CONNECTED

        # Async closures capture ``broker`` via a default argument to avoid
        # the classic late-binding loop closure issue.
        async def _on_connect(_: ft.Event, b: BrokerProfile = broker) -> None:
            await self.connect(b)

        async def _on_disconnect(_: ft.Event, b: BrokerProfile = broker) -> None:
            await self.disconnect(b)

        primary = ft.FilledButton(
            "Disconnect" if connected else "Connect",
            icon=ft.Icons.CLOSE if connected else ft.Icons.PLAY_ARROW,
            bgcolor=COLORS["red"] if connected else COLORS["lavender"],
            color=COLORS["base"],
            on_click=_on_disconnect if connected else _on_connect,
        )
        return ft.Container(
            padding=16,
            bgcolor=COLORS["surface"],
            border=ft.Border.all(1, COLORS["surface_border"]),
            border_radius=12,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(broker.name, size=18, weight=ft.FontWeight.W_600),
                            self._status_badge(status),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Text(broker.display_address, color=COLORS["muted"]),
                            ft.Text("TLS", size=12, color=COLORS["lavender"], visible=broker.use_ssl),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            primary,
                            ft.IconButton(ft.Icons.EDIT, tooltip="Edit broker", on_click=lambda _: self.open_edit_dialog(broker)),
                            ft.IconButton(ft.Icons.DELETE, tooltip="Delete broker", icon_color=COLORS["red"], on_click=lambda _: self.open_delete_dialog(broker)),
                        ],
                    ),
                ],
            ),
        )

    def refresh(self) -> None:
        """Reload cards after any profile or connection state change."""
        brokers = self.storage.get_all_brokers()
        if not brokers:
            self.cards.controls = [
                ft.Container(
                    padding=24,
                    bgcolor=COLORS["surface"],
                    border_radius=12,
                    content=ft.Text("No broker profiles yet. Add one to get started.", color=COLORS["muted"]),
                )
            ]
        else:
            self.cards.controls = [self._card(broker) for broker in brokers]

    async def connect(self, broker: BrokerProfile) -> None:
        self.refresh()
        self.app_page.update()
        ok, error = await connect_broker(broker)
        self.refresh()
        self.on_sessions_changed()
        self.app_page.update()
        notify(self.app_page, f"Connected to {broker.name}." if ok else (error or "Could not connect."), ok)

    async def disconnect(self, broker: BrokerProfile) -> None:
        if broker.id is None:
            return
        ok, error = await disconnect_broker(broker.id)
        self.refresh()
        self.on_sessions_changed()
        self.app_page.update()
        notify(self.app_page, f"Disconnected from {broker.name}." if ok else (error or "Could not disconnect."), ok)

    def open_add_dialog(self, _: ft.Event[ft.Button] | None = None) -> None:
        self._open_form_dialog()

    def open_edit_dialog(self, broker: BrokerProfile) -> None:
        self._open_form_dialog(broker)

    def _open_form_dialog(self, broker: BrokerProfile | None = None) -> None:
        name = ft.TextField(label="Connection name", value=broker.name if broker else "")
        host = ft.TextField(label="Broker host / URL", value=broker.host if broker else "")
        port = ft.TextField(label="Port", value=str(broker.port if broker else 1883))
        use_ssl = ft.Switch(label="Use SSL / TLS", value=broker.use_ssl if broker else False)
        username = ft.TextField(label="Username (optional)", value=broker.username or "" if broker else "")
        password = ft.TextField(label="Password (optional)", value=broker.password or "" if broker else "", password=True, can_reveal_password=True)

        async def save(_: ft.Event[ft.Button]) -> None:
            try:
                profile = BrokerProfile(
                    id=broker.id if broker else None,
                    name=name.value,
                    host=host.value,
                    port=int(port.value),
                    use_ssl=use_ssl.value,
                    username=username.value.strip() or None,
                    password=password.value or None,
                    created_at=broker.created_at if broker else None,
                )
                if broker:
                    if not self.storage.update_broker(profile):
                        raise ValueError("Broker profile no longer exists.")
                    message = "Broker profile updated."
                else:
                    self.storage.create_broker(profile)
                    message = "Broker profile saved."
            except (TypeError, ValueError) as exc:
                notify(self.app_page, str(exc), False)
                return
            self.app_page.pop_dialog()
            self.refresh()
            self.app_page.update()
            notify(self.app_page, message)

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["mantle"],
            title=ft.Text("Edit broker" if broker else "Add broker"),
            content=ft.Column(tight=True, width=360, controls=[name, host, port, use_ssl, username, password]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.app_page.pop_dialog()),
                ft.FilledButton("Save", bgcolor=COLORS["lavender"], color=COLORS["base"], on_click=save),
            ],
        )
        self.app_page.show_dialog(dialog)

    def open_delete_dialog(self, broker: BrokerProfile) -> None:
        async def delete(_: ft.Event[ft.Button]) -> None:
            if broker.id is not None and get_active_session(broker.id):
                await disconnect_broker(broker.id)
            deleted = broker.id is not None and self.storage.delete_broker(broker.id)
            self.app_page.pop_dialog()
            self.refresh()
            self.on_sessions_changed()
            self.app_page.update()
            notify(self.app_page, "Broker deleted." if deleted else "Broker profile no longer exists.", bool(deleted))

        self.app_page.show_dialog(
            ft.AlertDialog(
                modal=True,
                bgcolor=COLORS["mantle"],
                title=ft.Text("Delete broker?"),
                content=ft.Text(f"Remove {broker.name}? This cannot be undone."),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: self.app_page.pop_dialog()),
                    ft.FilledButton("Delete", bgcolor=COLORS["red"], color=COLORS["base"], on_click=delete),
                ],
            )
        )
