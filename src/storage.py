"""Storage engine and SQLite persistence for MQTT Antena Mobile.

Provides local-first SQLite persistence for broker profiles with automatic
directory initialization, idempotent schema setup, and standard CRUD operations.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Generator, Optional, Union

from src.models import BrokerProfile

DEFAULT_DB_PATH = Path("data/antena.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS brokers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 1883,
    use_ssl INTEGER NOT NULL DEFAULT 0,
    username TEXT,
    password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class StorageEngine:
    """Manages SQLite database connections and broker profile persistence."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
        self.db_path = str(db_path)
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        """Initializes database directory and tables idempotently.

        Applies restricted file permissions (0600) to protect local credentials
        on supported operating systems.
        """
        if self.db_path != ":memory:":
            db_file = Path(self.db_path)
            db_dir = db_file.parent
            if db_dir and not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(db_dir, 0o700)
                except OSError:
                    pass

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(SCHEMA_SQL)
            conn.commit()

        if self.db_path != ":memory:":
            db_file = Path(self.db_path)
            if db_file.exists():
                try:
                    os.chmod(db_file, 0o600)
                except OSError:
                    pass

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a thread-safe SQLite connection context."""
        if self._mem_conn is not None:
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def create_broker(self, broker: BrokerProfile) -> BrokerProfile:
        """Inserts a new broker profile and returns it with its generated id and timestamps."""
        validation_errors = broker.validate()
        if validation_errors:
            raise ValueError(f"Invalid broker profile: {', '.join(validation_errors)}")

        now = datetime.now()
        created_at = broker.created_at or now
        updated_at = broker.updated_at or now

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO brokers (name, host, port, use_ssl, username, password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    broker.name.strip(),
                    broker.host.strip(),
                    broker.port,
                    1 if broker.use_ssl else 0,
                    broker.username,
                    broker.password,
                    created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
                    updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at),
                ),
            )
            conn.commit()
            broker_id = cursor.lastrowid

        return BrokerProfile(
            id=broker_id,
            name=broker.name.strip(),
            host=broker.host.strip(),
            port=broker.port,
            use_ssl=broker.use_ssl,
            username=broker.username,
            password=broker.password,
            created_at=created_at,
            updated_at=updated_at,
        )

    def get_all_brokers(self) -> list[BrokerProfile]:
        """Retrieves all broker profiles ordered by id ascending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, host, port, use_ssl, username, password, created_at, updated_at
                FROM brokers
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall()

        return [
            BrokerProfile(
                id=row["id"],
                name=row["name"],
                host=row["host"],
                port=row["port"],
                use_ssl=bool(row["use_ssl"]),
                username=row["username"],
                password=row["password"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_broker_by_id(self, broker_id: int) -> Optional[BrokerProfile]:
        """Retrieves a broker profile by id, or None if not found."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, host, port, use_ssl, username, password, created_at, updated_at
                FROM brokers
                WHERE id = ?
                """,
                (broker_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return BrokerProfile(
            id=row["id"],
            name=row["name"],
            host=row["host"],
            port=row["port"],
            use_ssl=bool(row["use_ssl"]),
            username=row["username"],
            password=row["password"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_broker(self, broker: BrokerProfile) -> bool:
        """Updates an existing broker profile. Returns True if updated, False if not found."""
        if broker.id is None:
            raise ValueError("Cannot update broker profile without an id.")

        validation_errors = broker.validate()
        if validation_errors:
            raise ValueError(f"Invalid broker profile: {', '.join(validation_errors)}")

        now = datetime.now()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE brokers
                SET name = ?, host = ?, port = ?, use_ssl = ?, username = ?, password = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    broker.name.strip(),
                    broker.host.strip(),
                    broker.port,
                    1 if broker.use_ssl else 0,
                    broker.username,
                    broker.password,
                    now.isoformat(),
                    broker.id,
                ),
            )
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            broker.updated_at = now
        return updated

    def delete_broker(self, broker_id: int) -> bool:
        """Deletes a broker profile by id. Returns True if deleted, False if not found."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM brokers WHERE id = ?", (broker_id,))
            conn.commit()
            return cursor.rowcount > 0


_default_engine: Optional[StorageEngine] = None


def get_storage_engine() -> StorageEngine:
    """Returns the default singleton StorageEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = StorageEngine()
    return _default_engine


def set_default_db_path(db_path: Union[str, Path]) -> StorageEngine:
    """Sets a custom database path for the default StorageEngine."""
    global _default_engine
    _default_engine = StorageEngine(db_path=db_path)
    return _default_engine


def create_broker(broker: BrokerProfile) -> BrokerProfile:
    """Module-level convenience wrapper for create_broker."""
    return get_storage_engine().create_broker(broker)


def get_all_brokers() -> list[BrokerProfile]:
    """Module-level convenience wrapper for get_all_brokers."""
    return get_storage_engine().get_all_brokers()


def get_broker_by_id(broker_id: int) -> Optional[BrokerProfile]:
    """Module-level convenience wrapper for get_broker_by_id."""
    return get_storage_engine().get_broker_by_id(broker_id)


def update_broker(broker: BrokerProfile) -> bool:
    """Module-level convenience wrapper for update_broker."""
    return get_storage_engine().update_broker(broker)


def delete_broker(broker_id: int) -> bool:
    """Module-level convenience wrapper for delete_broker."""
    return get_storage_engine().delete_broker(broker_id)
