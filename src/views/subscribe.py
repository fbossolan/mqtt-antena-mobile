"""Live MQTT topic subscription view."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

import flet as ft

from src.models import BrokerProfile, MQTTMessage
from src.mqtt_client import get_connected_broker_ids, subscribe, unsubscribe
from src.storage import StorageEngine, get_storage_engine
from src.views.common import COLORS, notify


class SubscribeView(ft.Column):
    """Select a connected broker and render its message stream as a terminal."""

    def __init__(
        self,
        page: ft.Page,
        storage: StorageEngine | None = None,
        go_to_brokers: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=14)
        self.app_page = page
        self.storage = storage or get_storage_engine()
        self.go_to_brokers = go_to_brokers or (lambda: None)
        self.messages: deque[MQTTMessage] = deque(maxlen=500)
        self._listening_broker_id: int | None = None
        self._subscription_topic: str | None = None

        self.broker_dropdown = ft.Dropdown(label="Active broker", expand=True, on_select=self._broker_changed)
        self.topic = ft.TextField(label="Topic filter", hint_text="Leave empty for # to listen to all", expand=True)
        self.listen_button = ft.FilledButton("Start listening", icon=ft.Icons.PLAY_ARROW, on_click=self.toggle_listening)
        self.console = ft.ListView(expand=True, spacing=8, auto_scroll=True, padding=12)
        self.empty_state = ft.Container(
            visible=False,
            padding=16,
            bgcolor=COLORS["surface"],
            border_radius=12,
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("No active broker connected", weight=ft.FontWeight.W_600),
                    ft.Text("Connect a broker from the Brokers tab to start listening.", color=COLORS["muted"]),
                    ft.TextButton("Go to Brokers", on_click=lambda _: self.go_to_brokers()),
                ],
            ),
        )
        self.controls = [
            ft.Text("Subscribe", size=24, weight=ft.FontWeight.W_600),
            ft.Text("Monitor live MQTT traffic", color=COLORS["muted"]),
            self.empty_state,
            ft.Row(controls=[self.broker_dropdown]),
            ft.Row(controls=[self.topic]),
            ft.Row(
                controls=[
                    self.listen_button,
                    ft.OutlinedButton("Clear console", icon=ft.Icons.DELETE, on_click=self.clear_console),
                ]
            ),
            ft.Container(
                expand=True,
                bgcolor=COLORS["crust"],
                border=ft.Border.all(1, COLORS["surface_border"]),
                border_radius=12,
                content=self.console,
            ),
        ]
        self.refresh_connected_brokers()

    def _connected_profiles(self) -> list[BrokerProfile]:
        connected_ids = set(get_connected_broker_ids())
        return [broker for broker in self.storage.get_all_brokers() if broker.id in connected_ids]

    def refresh_connected_brokers(self) -> None:
        """Refresh dropdown options without discarding a valid selection."""
        brokers = self._connected_profiles()
        keys = {str(broker.id) for broker in brokers}
        self.broker_dropdown.options = [
            ft.DropdownOption(key=str(broker.id), text=f"{broker.name} ({broker.display_address})")
            for broker in brokers
        ]
        if self.broker_dropdown.value not in keys:
            self.broker_dropdown.value = next(iter(keys), None)
        has_brokers = bool(brokers)
        self.broker_dropdown.disabled = not has_brokers
        self.empty_state.visible = not has_brokers
        self.listen_button.disabled = not has_brokers

    def _broker_changed(self, _: ft.Event[ft.Dropdown]) -> None:
        self.app_page.update()

    async def toggle_listening(self, _: ft.Event[ft.Button] | None = None) -> None:
        if self._listening_broker_id is not None:
            await self.stop_listening()
            return

        if not self.broker_dropdown.value:
            notify(self.app_page, "Connect and select a broker before listening.", False)
            return
        broker_id = int(self.broker_dropdown.value)
        topic = self.topic.value.strip() or "#"
        ok, error = await subscribe(broker_id, topic, self._on_message)
        if not ok:
            notify(self.app_page, error or "Could not start subscription.", False)
            return
        self._listening_broker_id = broker_id
        self._subscription_topic = topic
        self.listen_button.content = "Stop listening"
        self.listen_button.icon = ft.Icons.STOP
        self.listen_button.bgcolor = COLORS["red"]
        self.topic.disabled = True
        self.broker_dropdown.disabled = True
        self.app_page.update()
        notify(self.app_page, f"Listening on {topic}.")

    async def stop_listening(self) -> None:
        if self._listening_broker_id is None or self._subscription_topic is None:
            return
        ok, error = await unsubscribe(self._listening_broker_id, self._subscription_topic)
        self._listening_broker_id = None
        self._subscription_topic = None
        self.listen_button.content = "Start listening"
        self.listen_button.icon = ft.Icons.PLAY_ARROW
        self.listen_button.bgcolor = None
        self.topic.disabled = False
        self.refresh_connected_brokers()
        self.app_page.update()
        if not ok:
            notify(self.app_page, error or "Could not stop subscription.", False)

    def _on_message(self, message: MQTTMessage) -> None:
        if message.broker_id != self._listening_broker_id:
            return
        self.app_page.run_task(self._append_message, message)

    async def _append_message(self, message: MQTTMessage) -> None:
        if len(self.messages) == self.messages.maxlen:
            self.console.controls.pop(0)
        self.messages.append(message)
        self.console.controls.append(
            ft.Column(
                tight=True,
                spacing=2,
                controls=[
                    ft.Text(message.summary, color=COLORS["lavender"], font_family="monospace", size=12),
                    ft.Text(f"↳ {message.payload}", color=COLORS["text"], font_family="monospace", size=12),
                ],
            )
        )
        self.app_page.update()

    def clear_console(self, _: ft.Event[ft.Button] | None = None) -> None:
        self.messages.clear()
        self.console.controls.clear()
        self.app_page.update()
