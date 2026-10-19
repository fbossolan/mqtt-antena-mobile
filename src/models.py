"""Shared data models for MQTT Antena Mobile.

This module defines shared dataclasses and enums representing broker profiles,
MQTT messages, and connection states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ConnectionStatus(str, Enum):
    """Represents the connection state of an MQTT broker session."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

    @property
    def display_name(self) -> str:
        """User-friendly display string for UI badges and labels."""
        return self.value.capitalize()

    @classmethod
    def _missing_(cls, value: object) -> Optional[ConnectionStatus]:
        """Case-insensitive member lookup by name or value."""
        if isinstance(value, str):
            for member in cls:
                if (
                    member.value.lower() == value.lower()
                    or member.name.lower() == value.lower()
                ):
                    return member
        return None


@dataclass
class BrokerProfile:
    """Represents an MQTT broker configuration profile.

    Attributes:
        id: Unique database primary key (None for unsaved/new profiles).
        name: User-defined friendly profile label (e.g. 'Home Broker').
        host: Broker hostname or IP address.
        port: Network port (default 1883, or 8883 for TLS/SSL).
        use_ssl: Boolean flag indicating whether TLS/SSL is enabled.
        username: Optional authentication username.
        password: Optional authentication password.
        created_at: Profile creation timestamp.
        updated_at: Profile last update timestamp.
    """

    id: Optional[int] = None
    name: str = ""
    host: str = ""
    port: int = 1883
    use_ssl: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Normalize and coerce field types if necessary."""
        self.use_ssl = bool(self.use_ssl)

        if isinstance(self.port, str):
            try:
                self.port = int(self.port)
            except ValueError:
                pass

        if isinstance(self.created_at, str):
            try:
                self.created_at = datetime.fromisoformat(self.created_at)
            except ValueError:
                pass

        if isinstance(self.updated_at, str):
            try:
                self.updated_at = datetime.fromisoformat(self.updated_at)
            except ValueError:
                pass

    @property
    def display_address(self) -> str:
        """Formatted host:port string."""
        return f"{self.host}:{self.port}"

    def validate(self) -> list[str]:
        """Validates the broker profile and returns a list of error messages.

        An empty list signifies a valid profile.
        """
        errors: list[str] = []
        if not self.name or not self.name.strip():
            errors.append("Broker name is required.")
        if not self.host or not self.host.strip():
            errors.append("Broker host is required.")
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            errors.append("Port must be an integer between 1 and 65535.")
        return errors

    @property
    def is_valid(self) -> bool:
        """True if the profile contains no validation errors."""
        return len(self.validate()) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to a dictionary suitable for storage or serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "username": self.username,
            "password": self.password,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrokerProfile:
        """Instantiate a BrokerProfile from a dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            host=data.get("host", ""),
            port=data.get("port", 1883),
            use_ssl=data.get("use_ssl", False),
            username=data.get("username"),
            password=data.get("password"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MQTTMessage:
    """Represents a received or published MQTT message.

    Attributes:
        timestamp: Time the message was received or created.
        topic: Destination or source MQTT topic string.
        payload: Message payload decoded as string.
        qos: Quality of Service level (0, 1, or 2).
        retained: Flag indicating if message is retained by broker.
        broker_id: Identifier of the broker associated with the message.
    """

    timestamp: Optional[datetime] = None
    topic: str = ""
    payload: str = ""
    qos: int = 0
    retained: bool = False
    broker_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Coerce timestamp and parameters."""
        if (
            isinstance(self.timestamp, str)
            and not any(c in self.timestamp for c in "-:T")
            and not self.timestamp[0:1].isdigit()
        ):
            # Positional arguments were likely (topic, payload) instead of (timestamp, topic, payload)
            temp_topic = self.timestamp
            temp_payload = self.topic
            self.timestamp = datetime.now()
            self.topic = temp_topic
            self.payload = temp_payload

        if self.timestamp is None:
            self.timestamp = datetime.now()
        elif isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.fromtimestamp(self.timestamp)
        elif isinstance(self.timestamp, str):
            try:
                self.timestamp = datetime.fromisoformat(self.timestamp)
            except ValueError:
                pass

        if isinstance(self.qos, str):
            try:
                self.qos = int(self.qos)
            except ValueError:
                self.qos = 0

        self.retained = bool(self.retained)

    @property
    def formatted_time(self) -> str:
        """Formats timestamp as HH:MM:SS.mmm for the terminal console."""
        if isinstance(self.timestamp, datetime):
            return self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        return str(self.timestamp)

    @property
    def summary(self) -> str:
        """Formatted terminal header line matching specs: e.g. [18:24:02.105] sensors/kitchen/temp (QoS 0)."""
        retained_tag = " | Retained" if self.retained else ""
        return f"[{self.formatted_time}] {self.topic} (QoS {self.qos}{retained_tag})"

    def to_dict(self) -> dict[str, Any]:
        """Convert message to a dictionary representation."""
        return {
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else str(self.timestamp)
            ),
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "retained": self.retained,
            "broker_id": self.broker_id,
        }
