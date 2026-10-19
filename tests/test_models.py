"""Unit tests for src/models.py."""

from datetime import datetime
import pytest

from src.models import BrokerProfile, ConnectionStatus, MQTTMessage


class TestConnectionStatus:
    """Tests for ConnectionStatus enum."""

    def test_enum_members_and_values(self):
        assert ConnectionStatus.DISCONNECTED == "disconnected"
        assert ConnectionStatus.CONNECTING == "connecting"
        assert ConnectionStatus.CONNECTED == "connected"
        assert ConnectionStatus.ERROR == "error"

    def test_display_name(self):
        assert ConnectionStatus.DISCONNECTED.display_name == "Disconnected"
        assert ConnectionStatus.CONNECTING.display_name == "Connecting"
        assert ConnectionStatus.CONNECTED.display_name == "Connected"
        assert ConnectionStatus.ERROR.display_name == "Error"

    def test_case_insensitive_lookup(self):
        assert ConnectionStatus("disconnected") == ConnectionStatus.DISCONNECTED
        assert ConnectionStatus("DISCONNECTED") == ConnectionStatus.DISCONNECTED
        assert ConnectionStatus("Disconnected") == ConnectionStatus.DISCONNECTED
        assert ConnectionStatus("connecting") == ConnectionStatus.CONNECTING
        assert ConnectionStatus("connected") == ConnectionStatus.CONNECTED
        assert ConnectionStatus("error") == ConnectionStatus.ERROR

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            ConnectionStatus("unknown_status")


class TestBrokerProfile:
    """Tests for BrokerProfile dataclass."""

    def test_default_values(self):
        broker = BrokerProfile()
        assert broker.id is None
        assert broker.name == ""
        assert broker.host == ""
        assert broker.port == 1883
        assert broker.use_ssl is False
        assert broker.username is None
        assert broker.password is None
        assert broker.created_at is None
        assert broker.updated_at is None

    def test_custom_values(self):
        now = datetime.now()
        broker = BrokerProfile(
            id=1,
            name="Mosquitto Test",
            host="broker.hivemq.com",
            port=8883,
            use_ssl=True,
            username="admin",
            password="secret_password",
            created_at=now,
            updated_at=now,
        )
        assert broker.id == 1
        assert broker.name == "Mosquitto Test"
        assert broker.host == "broker.hivemq.com"
        assert broker.port == 8883
        assert broker.use_ssl is True
        assert broker.username == "admin"
        assert broker.password == "secret_password"
        assert broker.created_at == now
        assert broker.updated_at == now

    def test_positional_arguments_order(self):
        now = datetime.now()
        broker = BrokerProfile(
            42,
            "Lab Broker",
            "192.168.1.100",
            1883,
            False,
            "user",
            "pass",
            now,
        )
        assert broker.id == 42
        assert broker.name == "Lab Broker"
        assert broker.host == "192.168.1.100"
        assert broker.port == 1883
        assert broker.use_ssl is False
        assert broker.username == "user"
        assert broker.password == "pass"
        assert broker.created_at == now

    def test_type_coercion(self):
        broker = BrokerProfile(
            port="8883",
            use_ssl=1,
            created_at="2026-10-18T12:00:00",
            updated_at="2026-10-18 13:00:00",
        )
        assert broker.port == 8883
        assert broker.use_ssl is True
        assert isinstance(broker.created_at, datetime)
        assert broker.created_at.hour == 12
        assert isinstance(broker.updated_at, datetime)
        assert broker.updated_at.hour == 13

    def test_display_address(self):
        broker = BrokerProfile(host="localhost", port=1883)
        assert broker.display_address == "localhost:1883"

    def test_validation_valid(self):
        broker = BrokerProfile(name="Home", host="192.168.1.1", port=1883)
        assert broker.is_valid is True
        assert broker.validate() == []

    def test_validation_missing_name(self):
        broker = BrokerProfile(name="", host="192.168.1.1", port=1883)
        assert broker.is_valid is False
        assert "Broker name is required." in broker.validate()

    def test_validation_missing_host(self):
        broker = BrokerProfile(name="Home", host="  ", port=1883)
        assert broker.is_valid is False
        assert "Broker host is required." in broker.validate()

    def test_validation_invalid_port(self):
        broker = BrokerProfile(name="Home", host="192.168.1.1", port=70000)
        assert broker.is_valid is False
        assert "Port must be an integer between 1 and 65535." in broker.validate()

        broker_zero = BrokerProfile(name="Home", host="192.168.1.1", port=0)
        assert broker_zero.is_valid is False

    def test_to_dict_and_from_dict(self):
        now = datetime(2026, 10, 18, 15, 30, 0)
        broker = BrokerProfile(
            id=5,
            name="EMQX Cloud",
            host="broker.emqx.io",
            port=8883,
            use_ssl=True,
            username="test_user",
            password="test_pass",
            created_at=now,
            updated_at=now,
        )
        b_dict = broker.to_dict()
        assert b_dict["id"] == 5
        assert b_dict["name"] == "EMQX Cloud"
        assert b_dict["host"] == "broker.emqx.io"
        assert b_dict["port"] == 8883
        assert b_dict["use_ssl"] is True
        assert b_dict["username"] == "test_user"
        assert b_dict["password"] == "test_pass"
        assert b_dict["created_at"] == now.isoformat()
        assert b_dict["updated_at"] == now.isoformat()

        reconstructed = BrokerProfile.from_dict(b_dict)
        assert reconstructed.id == broker.id
        assert reconstructed.name == broker.name
        assert reconstructed.host == broker.host
        assert reconstructed.port == broker.port
        assert reconstructed.use_ssl == broker.use_ssl
        assert reconstructed.username == broker.username
        assert reconstructed.password == broker.password
        assert reconstructed.created_at == broker.created_at
        assert reconstructed.updated_at == broker.updated_at


class TestMQTTMessage:
    """Tests for MQTTMessage dataclass."""

    def test_default_values(self):
        msg = MQTTMessage()
        assert isinstance(msg.timestamp, datetime)
        assert msg.topic == ""
        assert msg.payload == ""
        assert msg.qos == 0
        assert msg.retained is False
        assert msg.broker_id is None

    def test_keyword_arguments(self):
        now = datetime(2026, 10, 18, 18, 24, 2, 105000)
        msg = MQTTMessage(
            timestamp=now,
            topic="sensors/kitchen/temp",
            payload='{"temperature": 22.4}',
            qos=1,
            retained=True,
            broker_id=3,
        )
        assert msg.timestamp == now
        assert msg.topic == "sensors/kitchen/temp"
        assert msg.payload == '{"temperature": 22.4}'
        assert msg.qos == 1
        assert msg.retained is True
        assert msg.broker_id == 3

    def test_positional_arguments_order(self):
        now = datetime(2026, 10, 18, 12, 0, 0)
        msg = MQTTMessage(
            now,
            "devices/light/state",
            "ON",
            2,
            False,
            10,
        )
        assert msg.timestamp == now
        assert msg.topic == "devices/light/state"
        assert msg.payload == "ON"
        assert msg.qos == 2
        assert msg.retained is False
        assert msg.broker_id == 10

    def test_topic_payload_shorthand(self):
        msg = MQTTMessage("sensors/bedroom/humidity", "45%")
        assert msg.topic == "sensors/bedroom/humidity"
        assert msg.payload == "45%"
        assert isinstance(msg.timestamp, datetime)

    def test_timestamp_from_string_and_epoch(self):
        msg_str = MQTTMessage(
            timestamp="2026-10-18T14:32:05.120",
            topic="test/topic",
            payload="ok",
        )
        assert isinstance(msg_str.timestamp, datetime)
        assert msg_str.timestamp.second == 5

        msg_epoch = MQTTMessage(
            timestamp=1700000000.0,
            topic="test/topic",
            payload="ok",
        )
        assert isinstance(msg_epoch.timestamp, datetime)

    def test_formatted_time(self):
        dt = datetime(2026, 10, 18, 18, 24, 2, 105000)
        msg = MQTTMessage(timestamp=dt, topic="test", payload="test")
        assert msg.formatted_time == "18:24:02.105"

    def test_summary_formatting(self):
        dt = datetime(2026, 10, 18, 18, 24, 2, 105000)
        msg = MQTTMessage(
            timestamp=dt,
            topic="sensors/kitchen/temp",
            payload='{"temperature": 22.4}',
            qos=0,
            retained=False,
        )
        assert msg.summary == "[18:24:02.105] sensors/kitchen/temp (QoS 0)"

        msg_retained = MQTTMessage(
            timestamp=dt,
            topic="sensors/kitchen/temp",
            payload="payload",
            qos=1,
            retained=True,
        )
        assert msg_retained.summary == "[18:24:02.105] sensors/kitchen/temp (QoS 1 | Retained)"

    def test_to_dict(self):
        dt = datetime(2026, 10, 18, 18, 24, 2, 105000)
        msg = MQTTMessage(
            timestamp=dt,
            topic="sensors/temp",
            payload="23.1",
            qos=1,
            retained=False,
            broker_id=2,
        )
        data = msg.to_dict()
        assert data["timestamp"] == dt.isoformat()
        assert data["topic"] == "sensors/temp"
        assert data["payload"] == "23.1"
        assert data["qos"] == 1
        assert data["retained"] is False
        assert data["broker_id"] == 2
