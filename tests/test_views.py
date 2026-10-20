"""Focused state tests for the Phase 5 Flet views."""

from __future__ import annotations

import pytest

from src.models import BrokerProfile, MQTTMessage
from src.storage import StorageEngine
from src.views.brokers import BrokersView
from src.views.publish import PublishView
from src.views.subscribe import SubscribeView


class FakePage:
    """Enough of Flet's Page API to exercise view-owned state without Flutter."""

    def __init__(self) -> None:
        self.update_calls = 0
        self.dialogs = []

    def update(self) -> None:
        self.update_calls += 1

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

    def run_task(self, handler, *args):
        # Tests call the coroutine directly where its effects matter.
        return handler(*args)


@pytest.fixture
def storage() -> StorageEngine:
    return StorageEngine(":memory:")


def test_brokers_view_lists_saved_profile(storage: StorageEngine):
    storage.create_broker(BrokerProfile(name="Lab", host="mqtt.local", use_ssl=True))
    view = BrokersView(FakePage(), storage)

    assert len(view.cards.controls) == 1
    card = view.cards.controls[0]
    assert card.content.controls[0].controls[0].value == "Lab"


def test_subscribe_view_uses_connected_brokers_and_caps_console(monkeypatch, storage: StorageEngine):
    broker = storage.create_broker(BrokerProfile(name="Lab", host="mqtt.local"))
    monkeypatch.setattr("src.views.subscribe.get_connected_broker_ids", lambda: [broker.id])
    page = FakePage()
    view = SubscribeView(page, storage)

    assert view.broker_dropdown.value == str(broker.id)
    assert view.listen_button.disabled is False

    for index in range(501):
        view.messages.append(MQTTMessage(topic=f"telemetry/{index}", payload="ok", broker_id=broker.id))
    assert len(view.messages) == 500
    assert view.messages[0].topic == "telemetry/1"


@pytest.mark.asyncio
async def test_publish_view_validates_and_passes_qos_retain(monkeypatch, storage: StorageEngine):
    broker = storage.create_broker(BrokerProfile(name="Lab", host="mqtt.local"))
    monkeypatch.setattr("src.views.publish.get_connected_broker_ids", lambda: [broker.id])
    published = {}

    async def fake_publish(broker_id, topic, payload, qos=0, retain=False):
        published.update(broker_id=broker_id, topic=topic, payload=payload, qos=qos, retain=retain)
        return True, None

    monkeypatch.setattr("src.views.publish.publish_message", fake_publish)
    page = FakePage()
    view = PublishView(page, storage)
    view.topic.value = "devices/light/set"
    view.payload.value = '{"on": true}'
    view.qos.selected = ["2"]
    view.retain.value = True

    await view.publish()

    assert published == {
        "broker_id": broker.id,
        "topic": "devices/light/set",
        "payload": '{"on": true}',
        "qos": 2,
        "retain": True,
    }
    assert page.dialogs  # success snackbar

    view.topic.value = "devices/#"
    await view.publish()
    assert view.topic.error == "Publish topics cannot contain + or #."
