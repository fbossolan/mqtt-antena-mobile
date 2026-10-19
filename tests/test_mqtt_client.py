# tests/test_mqtt_client.py
"""Unit tests for the MQTT client implementation (src/mqtt_client.py).

These tests cover:
* Session creation and retrieval via ``connect_broker``/``get_active_session``.
* Topic subscription handling, including callback registration.
* Publishing with wildcard validation.
* Callback dispatch when a message is received.
"""

import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

# Import the module under test.
from src import mqtt_client
from src.models import BrokerProfile, MQTTMessage, ConnectionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DummyClient:
    """A lightweight mock of ``paho.mqtt.client.Client``.

    The dummy records the callbacks set by the ``ActiveSession`` and provides
    ``connect_async``, ``loop_start``, ``loop_stop``, ``disconnect``, ``subscribe``,
    ``unsubscribe`` and ``publish`` methods used by the implementation.
    """

    def __init__(self, *_, **__):
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self._connected = False
        self._broker_id = None

    def username_pw_set(self, *_, **__):
        pass

    def tls_set_context(self, *_, **__):
        pass

    def connect_async(self, host, port, keepalive=60):
        # Simulate immediate successful connection.
        self._connected = True
        if self.on_connect:
            # rc=0 means success.
            self.on_connect(self, None, None, 0)

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def disconnect(self):
        self._connected = False
        if self.on_disconnect:
            self.on_disconnect(self, None, 0)

    def subscribe(self, topic):
        # Return (result, mid) – 0 indicates success.
        return (0, 1)

    def unsubscribe(self, topic):
        return (0, 1)

    def publish(self, topic, payload, qos, retain):
        return (0, 1)

    # Helper to trigger a received message.
    def trigger_message(self, topic, payload, qos=0, retain=False):
        if self.on_message:
            msg = SimpleNamespace(topic=topic, payload=payload.encode(), qos=qos, retain=retain)
            self.on_message(self, None, msg)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_mqtt_client(monkeypatch):
    """Patch the ``paho.mqtt.client.Client`` used inside the module.
    """
    monkeypatch.setattr(mqtt_client, "mqtt", SimpleNamespace(Client=DummyClient))
    # Ensure a clean global registry for each test.
    mqtt_client._active_sessions.clear()
    yield
    mqtt_client._active_sessions.clear()

@pytest.fixture
def broker():
    return BrokerProfile(id=1, name="Test", host="localhost", port=1883, use_ssl=False)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_and_get_active_session(broker):
    success, err = await mqtt_client.connect_broker(broker)
    assert success
    assert err is None
    session = mqtt_client.get_active_session(broker.id)
    assert isinstance(session, mqtt_client.ActiveSession)
    # The dummy client should have reported CONNECTED.
    assert session.status == ConnectionStatus.CONNECTED

@pytest.mark.asyncio
async def test_subscribe_registers_callback_and_topic(broker):
    await mqtt_client.connect_broker(broker)
    received = []

    def cb(msg: MQTTMessage):
        received.append(msg)

    ok, err = await mqtt_client.subscribe(broker.id, "test/topic", callback=cb)
    assert ok
    assert err is None
    session = mqtt_client.get_active_session(broker.id)
    assert "test/topic" in session.subscriptions
    assert cb in session.callbacks

    # Simulate a message arrival.
    session.client.trigger_message("test/topic", "payload")
    await asyncio.sleep(0)  # let the event loop run the callback.
    assert len(received) == 1
    assert received[0].topic == "test/topic"
    assert received[0].payload == "payload"

@pytest.mark.asyncio
async def test_unsubscribe_removes_topic(broker):
    await mqtt_client.connect_broker(broker)
    await mqtt_client.subscribe(broker.id, "a/b")
    ok, err = await mqtt_client.unsubscribe(broker.id, "a/b")
    assert ok
    assert err is None
    session = mqtt_client.get_active_session(broker.id)
    assert "a/b" not in session.subscriptions

@pytest.mark.asyncio
async def test_publish_validation_and_success(broker):
    await mqtt_client.connect_broker(broker)
    # Valid publish
    ok, err = await mqtt_client.publish_message(broker.id, "valid/topic", "hello")
    assert ok
    assert err is None

    # Invalid topic with wildcard
    ok, err = await mqtt_client.publish_message(broker.id, "invalid/#", "test")
    assert not ok
    assert "wildcard" in err.lower()

    # Non‑existent broker id
    ok, err = await mqtt_client.publish_message(999, "topic", "msg")
    assert not ok
    assert "no active session" in err.lower()

@pytest.mark.asyncio
async def test_error_when_no_session(broker):
    # Do not connect first.
    ok, err = await mqtt_client.subscribe(broker.id, "t")
    assert not ok
    assert "no active session" in err.lower()

    ok, err = await mqtt_client.unsubscribe(broker.id, "t")
    assert not ok
    assert "no active session" in err.lower()
