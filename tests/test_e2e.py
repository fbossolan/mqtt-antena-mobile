"""End-to-end integration test for Task 6.1: Local Verification.

Tests the full MQTT Antena Mobile flow against the local 'main' broker:
  1. Broker profile exists in storage.
  2. Connect - status turns CONNECTED.
  3. Subscribe to # on the connected broker.
  4. Publish a test payload.
  5. Confirm the published message is received in the subscription stream.
  6. Disconnect - active session registry clears.

Run with:
    make test
or directly:
    .venv/bin/pytest tests/test_e2e.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Resolve project root regardless of where pytest is invoked from.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# When running outside the Flet runner, use the Flet app data dir where the
# 'main' broker was originally created via the UI.
FLET_DATA_DIR = PROJECT_ROOT / "src" / ".flet" / "storage" / "data" / "data"
FALLBACK_DATA_DIR = PROJECT_ROOT / "data"

# Pick whichever data directory actually contains the DB.
def _resolve_db_path() -> Path:
    flet_db = FLET_DATA_DIR / "antena.db"
    if flet_db.exists():
        return flet_db
    fallback_db = FALLBACK_DATA_DIR / "antena.db"
    return fallback_db  # may not exist yet; StorageEngine will create it


DB_PATH = _resolve_db_path()

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def storage():
    """Return a StorageEngine pointed at the real app database."""
    from src.storage import StorageEngine
    return StorageEngine(str(DB_PATH))


@pytest.fixture
def main_broker(storage):
    """Return the 'main' BrokerProfile, creating it if missing."""
    from src.models import BrokerProfile
    brokers = storage.get_all_brokers()
    broker = next((b for b in brokers if b.name == "main"), None)
    if broker is None:
        broker = storage.create_broker(
            BrokerProfile(
                name="main",
                host="192.168.3.33",
                port=1883,
                use_ssl=False,
                username="buzz",
                password="KafeSemAcucar",
            )
        )
    return broker


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestE2EFlow:
    """Task 6.1 end-to-end verification tests."""

    @pytest.mark.asyncio
    async def test_step1_broker_profile_exists(self, main_broker):
        """Step 1: Broker profile is saved and retrievable from storage."""
        assert main_broker.id is not None
        assert main_broker.name == "main"
        assert main_broker.host == "192.168.3.33"
        assert main_broker.port == 1883
        assert main_broker.is_valid

    @pytest.mark.asyncio
    async def test_step2_connect_status_connected(self, main_broker):
        """Step 2: Connecting sets status to CONNECTED and count increments."""
        from src.mqtt_client import (
            connect_broker,
            disconnect_broker,
            get_connected_broker_count,
            get_connected_broker_ids,
        )
        from src.models import ConnectionStatus

        ok, err = await connect_broker(main_broker)
        try:
            assert ok, f"connect_broker failed: {err}"
            assert get_connected_broker_count() == 1
            assert main_broker.id in get_connected_broker_ids()
        finally:
            await disconnect_broker(main_broker.id)

    @pytest.mark.asyncio
    async def test_step3_subscribe_listens(self, main_broker):
        """Step 3: subscribe() succeeds and registers callback."""
        from src.mqtt_client import connect_broker, disconnect_broker, subscribe, unsubscribe
        from src.models import MQTTMessage

        received: list[MQTTMessage] = []

        await connect_broker(main_broker)
        try:
            ok, err = await subscribe(main_broker.id, "#", received.append)
            assert ok, f"subscribe failed: {err}"
        finally:
            await unsubscribe(main_broker.id, "#")
            await disconnect_broker(main_broker.id)

    @pytest.mark.asyncio
    async def test_step4_publish_succeeds(self, main_broker):
        """Step 4: publish_message() returns success for a valid topic/payload."""
        from src.mqtt_client import connect_broker, disconnect_broker, publish_message

        await connect_broker(main_broker)
        try:
            ok, err = await publish_message(
                main_broker.id,
                "test/antena/e2e_verification",
                '{"source": "pytest_e2e", "status": "ok"}',
                qos=0,
                retain=False,
            )
            assert ok, f"publish_message failed: {err}"
        finally:
            await disconnect_broker(main_broker.id)

    @pytest.mark.asyncio
    async def test_step5_message_received_in_console(self, main_broker):
        """Step 5: Published message arrives in subscription callback (full round-trip)."""
        from src.mqtt_client import (
            connect_broker,
            disconnect_broker,
            subscribe,
            unsubscribe,
            publish_message,
        )
        from src.models import MQTTMessage

        test_topic = "test/antena/e2e_roundtrip"
        test_payload = '{"step": 5, "check": "round_trip"}'
        received: list[MQTTMessage] = []

        await connect_broker(main_broker)
        try:
            ok, _ = await subscribe(main_broker.id, "#", received.append)
            assert ok

            ok, err = await publish_message(main_broker.id, test_topic, test_payload)
            assert ok, f"publish failed: {err}"

            # Allow up to 3 s for the message to loop back.
            for _ in range(30):
                if any(m.topic == test_topic for m in received):
                    break
                await asyncio.sleep(0.1)

            matched = [m for m in received if m.topic == test_topic]
            assert matched, (
                f"Published message not received within 3 s. "
                f"Total messages received: {len(received)}"
            )
            msg = matched[0]
            assert msg.payload == test_payload
            # Verify summary format: [HH:MM:SS.mmm] topic (QoS N)
            assert msg.topic in msg.summary
            assert "QoS 0" in msg.summary
        finally:
            await unsubscribe(main_broker.id, "#")
            await disconnect_broker(main_broker.id)

    @pytest.mark.asyncio
    async def test_step6_disconnect_clears_registry(self, main_broker):
        """Step 6: After disconnect, broker is removed from active session registry."""
        from src.mqtt_client import (
            connect_broker,
            disconnect_broker,
            get_connected_broker_count,
            get_connected_broker_ids,
        )

        await connect_broker(main_broker)
        assert get_connected_broker_count() == 1

        ok, err = await disconnect_broker(main_broker.id)
        assert ok, f"disconnect_broker failed: {err}"
        assert get_connected_broker_count() == 0
        assert main_broker.id not in get_connected_broker_ids()

    @pytest.mark.asyncio
    async def test_full_e2e_flow(self, main_broker):
        """Complete Task 6.1 flow: connect → subscribe → publish → receive → disconnect."""
        from src.mqtt_client import (
            connect_broker,
            disconnect_broker,
            subscribe,
            unsubscribe,
            publish_message,
            get_connected_broker_count,
            get_connected_broker_ids,
        )
        from src.models import MQTTMessage

        received: list[MQTTMessage] = []
        test_topic = "test/antena/full_e2e"
        test_payload = '{"e2e": true, "task": "6.1"}'

        # 1. Connect
        ok, err = await connect_broker(main_broker)
        assert ok, f"Step 2 failed: {err}"
        assert get_connected_broker_count() == 1

        # 2. Subscribe
        ok, err = await subscribe(main_broker.id, "#", received.append)
        assert ok, f"Step 3 failed: {err}"

        # 3. Publish
        ok, err = await publish_message(main_broker.id, test_topic, test_payload)
        assert ok, f"Step 4 failed: {err}"

        # 4. Wait for round-trip
        for _ in range(30):
            if any(m.topic == test_topic for m in received):
                break
            await asyncio.sleep(0.1)
        assert any(m.topic == test_topic for m in received), "Step 5 failed: no message received"

        # 5. Unsubscribe + Disconnect
        await unsubscribe(main_broker.id, "#")
        ok, err = await disconnect_broker(main_broker.id)
        assert ok, f"Step 6 failed: {err}"
        assert get_connected_broker_count() == 0
        assert main_broker.id not in get_connected_broker_ids()
