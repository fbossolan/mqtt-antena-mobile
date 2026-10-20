"""MQTT message publishing view."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from models import BrokerProfile
from mqtt_client import get_connected_broker_ids, publish_message
from storage import StorageEngine, get_storage_engine
from views.common import COLORS, notify


class PublishView(ft.Column):
    """Compose and publish an MQTT message through a connected broker."""

    def __init__(
        self,
        page: ft.Page,
        storage: StorageEngine | None = None,
        go_to_brokers: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=14, scroll=ft.ScrollMode.AUTO)
        self.app_page = page
        self.storage = storage or get_storage_engine()
        self.go_to_brokers = go_to_brokers or (lambda: None)
        self.broker_dropdown = ft.Dropdown(label="Active broker", on_select=lambda _: self.app_page.update())
        self.topic = ft.TextField(label="Destination topic", hint_text="e.g. sensors/kitchen/command")
        self.qos = ft.SegmentedButton(
            segments=[ft.Segment(value=str(level), label=ft.Text(str(level))) for level in range(3)],
            selected=["0"],
        )
        self.retain = ft.Switch(label="Retain message", value=False)
        self.payload = ft.TextField(label="Message payload", multiline=True, min_lines=4, max_lines=10)
        self.publish_button = ft.FilledButton(
            "Publish",
            icon=ft.Icons.PUBLISH,
            bgcolor=COLORS["lavender"],
            color=COLORS["base"],
            on_click=self.publish,
        )
        self.empty_state = ft.Container(
            visible=False,
            padding=16,
            bgcolor=COLORS["surface"],
            border_radius=12,
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("No active broker connected", weight=ft.FontWeight.W_600),
                    ft.Text("Connect a broker from the Brokers tab before publishing.", color=COLORS["muted"]),
                    ft.TextButton("Go to Brokers", on_click=lambda _: self.go_to_brokers()),
                ],
            ),
        )
        self.controls = [
            ft.Text("Publish", size=24, weight=ft.FontWeight.W_600),
            ft.Text("Send a message to an active broker", color=COLORS["muted"]),
            self.empty_state,
            self.broker_dropdown,
            self.topic,
            ft.Text("Quality of Service (QoS)", weight=ft.FontWeight.W_500),
            self.qos,
            self.retain,
            self.payload,
            self.publish_button,
        ]
        self.refresh_connected_brokers()

    def _connected_profiles(self) -> list[BrokerProfile]:
        connected_ids = set(get_connected_broker_ids())
        return [broker for broker in self.storage.get_all_brokers() if broker.id in connected_ids]

    def refresh_connected_brokers(self) -> None:
        """Update active-broker choices and disable publishing when none remain."""
        brokers = self._connected_profiles()
        keys = {str(broker.id) for broker in brokers}
        self.broker_dropdown.options = [
            ft.DropdownOption(key=str(broker.id), text=f"{broker.name} ({broker.display_address})")
            for broker in brokers
        ]
        if self.broker_dropdown.value not in keys:
            self.broker_dropdown.value = next(iter(keys), None)
        enabled = bool(brokers)
        self.broker_dropdown.disabled = not enabled
        self.publish_button.disabled = not enabled
        self.empty_state.visible = not enabled

    async def publish(self, _: ft.Event[ft.Button] | None = None) -> None:
        topic = self.topic.value.strip()
        if not topic:
            self.topic.error = "A destination topic is required."
            self.app_page.update()
            return
        if "+" in topic or "#" in topic:
            self.topic.error = "Publish topics cannot contain + or #."
            self.app_page.update()
            return
        if not self.broker_dropdown.value:
            notify(self.app_page, "Connect and select a broker before publishing.", False)
            return
        self.topic.error = None
        qos = int(next(iter(self.qos.selected), "0"))
        ok, error = await publish_message(
            int(self.broker_dropdown.value),
            topic,
            self.payload.value,
            qos=qos,
            retain=bool(self.retain.value),
        )
        if ok:
            notify(self.app_page, "Message published.")
        else:
            notify(self.app_page, error or "Message could not be published.", False)
