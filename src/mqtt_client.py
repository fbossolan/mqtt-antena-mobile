# mqtt_client.py
"""Asynchronous MQTT client implementation for MQTT Antena Mobile.

This module provides a lightweight async wrapper around the Paho MQTT client,
maintaining an ``ActiveSession`` per broker. It supports connecting and
disconnecting brokers with SSL/TLS and credential handling as required by
Task 3.1 in ``specs/tasks.md``.

The public API consists of:
* ``ActiveSession`` – dataclass tracking the client instance, connection status
  and a set of active subscriptions.
* ``connect_broker(broker)`` – async function establishing a connection to the
  specified ``BrokerProfile``. Returns ``(bool, Optional[str])`` where ``bool``
  indicates success and the optional string contains an error message on
  failure.
* ``disconnect_broker(broker_id)`` – async function gracefully disconnecting a
  broker identified by its database ``id``.

All operations are performed inside the project's virtual environment and use
the ``BrokerProfile`` and ``ConnectionStatus`` definitions from ``models``.
"""

from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional, Callable

import paho.mqtt.client as mqtt

from models import BrokerProfile, ConnectionStatus, MQTTMessage

# ---------------------------------------------------------------------------
# Global registry of active sessions keyed by ``broker.id``.
# ---------------------------------------------------------------------------
_active_sessions: Dict[int, "ActiveSession"] = {}


@dataclass
class ActiveSession:
    """Container for a live MQTT broker session.

    Attributes
    ----------
    client: mqtt.Client
        The underlying Paho MQTT client instance.
    status: ConnectionStatus
        Current connection state of the session.
    subscriptions: Set[str]
        Set of topic strings the client is subscribed to.
    message_queue: asyncio.Queue[MQTTMessage]
        Queue receiving incoming MQTTMessage objects for UI consumption.
    callbacks: Set[Callable[[MQTTMessage], None]]
        Registered callbacks invoked on each received message.
    """

    client: mqtt.Client
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    subscriptions: Set[str] = field(default_factory=set)
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    callbacks: Set[Callable] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Attach callbacks for status and message handling.
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_message(self, client, userdata, msg) -> None:  # pragma: no cover
        """Process incoming MQTT messages, enqueue and notify callbacks."""
        from models import MQTTMessage
        message = MQTTMessage(
            timestamp=None,
            topic=msg.topic,
            payload=msg.payload.decode(errors="ignore"),
            qos=msg.qos,
            retained=bool(msg.retain),
            broker_id=getattr(client, "_broker_id", None),
        )
        try:
            self.message_queue.put_nowait(message)
        except asyncio.QueueFull:
            # Discard oldest if full.
            try:
                self.message_queue.get_nowait()
                self.message_queue.put_nowait(message)
            except Exception:
                pass
        for cb in list(self.callbacks):
            try:
                cb(message)
            except Exception:
                pass

    def _on_connect(self, client, userdata, flags, reason_code, properties):  # pragma: no cover
        """Paho v2 on_connect callback: reason_code 0 means success."""
        self.status = (
            ConnectionStatus.CONNECTED if reason_code == 0 else ConnectionStatus.ERROR
        )

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):  # pragma: no cover
        """Paho v2 on_disconnect callback."""
        self.status = ConnectionStatus.DISCONNECTED


def _build_mqtt_client(broker: BrokerProfile) -> mqtt.Client:
    """Create and configure a ``paho.mqtt.client.Client`` for ``broker``.

    SSL/TLS is enabled when ``broker.use_ssl`` is ``True``. Username/password
    authentication is applied when provided.
    Uses Paho CallbackAPIVersion.VERSION2 to avoid deprecation warnings.
    """
    client_id = f"mqtt_antena_{broker.id or 'temp'}"
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        clean_session=True,
    )
    # Paho callbacks only receive the client, so retain the owning profile id
    # there for the UI's per-broker subscription stream.
    setattr(client, "_broker_id", broker.id)

    if broker.username:
        client.username_pw_set(broker.username, broker.password or "")

    if broker.use_ssl:
        # Use default SSL context with certificate verification disabled to keep
        # the example simple. In production you would load proper CA bundles.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)

    return client


async def connect_broker(broker: BrokerProfile) -> Tuple[bool, Optional[str]]:
    """Asynchronously connect to a broker and register an ``ActiveSession``.

    Parameters
    ----------
    broker: BrokerProfile
        The broker configuration to connect to.

    Returns
    -------
    Tuple[bool, Optional[str]]
        ``True`` and ``None`` on success; ``False`` and an error message on
        failure.
    """
    if broker.id is None:
        return False, "BrokerProfile.id is required to manage sessions."

    # If a session already exists, attempt a clean disconnect first.
    if broker.id in _active_sessions:
        await disconnect_broker(broker.id)

    client = _build_mqtt_client(broker)
    session = ActiveSession(client=client)
    session.status = ConnectionStatus.CONNECTING
    _active_sessions[broker.id] = session

    loop = asyncio.get_event_loop()
    try:
        # ``connect_async`` schedules the connection; we then start the network
        # loop in a background thread via ``loop_start``.
        client.connect_async(broker.host, broker.port, keepalive=60)
        client.loop_start()

        # Wait for the client to report a connected status or timeout.
        timeout = 10  # seconds
        for _ in range(timeout * 10):
            if session.status == ConnectionStatus.CONNECTED:
                return True, None
            if session.status == ConnectionStatus.ERROR:
                break
            await asyncio.sleep(0.1)
        session.status = ConnectionStatus.ERROR
        return False, "Connection timeout or error occurred."
    except Exception as exc:  # pragma: no cover
        # Ensure cleanup on unexpected exceptions.
        _active_sessions.pop(broker.id, None)
        return False, str(exc)


async def disconnect_broker(broker_id: int) -> Tuple[bool, Optional[str]]:
    """Gracefully disconnect the session associated with ``broker_id``.

    Returns a tuple ``(success, error_message)`` similar to ``connect_broker``.
    """
    session = _active_sessions.get(broker_id)
    if not session:
        return False, f"No active session for broker id {broker_id}."

    try:
        # ``disconnect`` is synchronous but will trigger the callback.
        session.client.disconnect()
        # Give the client a moment to process the disconnect.
        await asyncio.sleep(0.5)
        session.client.loop_stop()
        _active_sessions.pop(broker_id, None)
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)

# ---------------------------------------------------------------------------
# Helper utilities (internal) – not part of the public spec but convenient.
# ---------------------------------------------------------------------------
def get_active_session(broker_id: int) -> Optional[ActiveSession]:
    """Retrieve the ``ActiveSession`` for ``broker_id`` if it exists."""
    return _active_sessions.get(broker_id)


def get_connected_broker_count() -> int:
    """Return the number of currently connected MQTT sessions."""
    return sum(
        session.status == ConnectionStatus.CONNECTED
        for session in _active_sessions.values()
    )


def get_connected_broker_ids() -> list[int]:
    """Return ids for sessions that are currently ready for MQTT operations."""
    return [
        broker_id
        for broker_id, session in _active_sessions.items()
        if session.status == ConnectionStatus.CONNECTED
    ]


async def shutdown_all_sessions() -> None:
    """Gracefully stop every active MQTT client network loop.

    The function is idempotent because Flet may deliver both page disconnect
    and close events for the same session.
    """
    broker_ids = list(_active_sessions)
    if broker_ids:
        await asyncio.gather(
            *(disconnect_broker(broker_id) for broker_id in broker_ids),
            return_exceptions=True,
        )


async def subscribe(broker_id: int, topic: str, callback: Optional[Callable[[MQTTMessage], None]] = None) -> Tuple[bool, Optional[str]]:
    """Subscribe to a topic for a given broker session.

    Parameters
    ----------
    broker_id: int
        Identifier of the broker whose session we want to use.
    topic: str
        MQTT topic to subscribe to.
    callback: Callable[[MQTTMessage], None] | None, optional
        Optional function to be invoked when a message on *topic* arrives.

    Returns
    -------
    Tuple[bool, Optional[str]]
        ``True`` on success, ``False`` with an error message otherwise.
    """
    topic = topic.strip() or "#"
    session = get_active_session(broker_id)
    if not session:
        return False, f"No active session for broker id {broker_id}."
    try:
        rc, _ = session.client.subscribe(topic)
        if rc != 0:
            return False, f"Subscribe failed with code {rc}."
        session.subscriptions.add(topic)
        if callback:
            session.callbacks.add(callback)
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


async def unsubscribe(broker_id: int, topic: str) -> Tuple[bool, Optional[str]]:
    """Unsubscribe from a topic for a given broker session.

    Returns ``(True, None)`` on success, otherwise ``(False, error)``.
    """
    session = get_active_session(broker_id)
    if not session:
        return False, f"No active session for broker id {broker_id}."
    try:
        rc, _ = session.client.unsubscribe(topic)
        if rc != 0:
            return False, f"Unsubscribe failed with code {rc}."
        session.subscriptions.discard(topic)
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


async def publish_message(
    broker_id: int,
    topic: str,
    payload: str,
    qos: int = 0,
    retain: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Publish a message to a topic after validating the topic does not contain wildcards.

    Wildcard characters '+' and '#' are not allowed in publish topics.
    """
    topic = topic.strip()
    if not topic:
        return False, "A publish topic is required."
    if '+' in topic or '#' in topic:
        return False, "Topic contains wildcard characters which are not allowed for publishing."
    if qos not in (0, 1, 2):
        return False, "QoS must be 0, 1, or 2."
    session = get_active_session(broker_id)
    if not session:
        return False, f"No active session for broker id {broker_id}."
    try:
        rc, _ = session.client.publish(topic, payload, qos=qos, retain=retain)
        if rc != 0:
            return False, f"Publish failed with code {rc}."
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)

