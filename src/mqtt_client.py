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
the ``BrokerProfile`` and ``ConnectionStatus`` definitions from
``src.models``.
"""

from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional

import paho.mqtt.client as mqtt

from .models import BrokerProfile, ConnectionStatus

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
    """

    client: mqtt.Client
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    subscriptions: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Attach simple callbacks for status tracking.
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):  # pragma: no cover
        # rc 0 means success.
        self.status = ConnectionStatus.CONNECTED if rc == 0 else ConnectionStatus.ERROR

    def _on_disconnect(self, client, userdata, rc):  # pragma: no cover
        # rc == 0 is a clean disconnect.
        self.status = ConnectionStatus.DISCONNECTED


def _build_mqtt_client(broker: BrokerProfile) -> mqtt.Client:
    """Create and configure a ``paho.mqtt.client.Client`` for ``broker``.

    SSL/TLS is enabled when ``broker.use_ssl`` is ``True``. Username/password
    authentication is applied when provided.
    """
    client_id = f"mqtt_antena_{broker.id or 'temp'}"
    client = mqtt.Client(client_id=client_id, clean_session=True)

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
