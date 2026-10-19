"""Additional unit tests for SQLite transaction isolation in src/storage.py.

These tests verify that uncommitted changes are not persisted when an exception
occurs within a transaction context managed by `StorageEngine.get_connection()`.
"""

import pytest

from src.models import BrokerProfile
from src.storage import StorageEngine


def test_transaction_isolation_on_exception(tmp_path):
    """Ensure that a failed transaction does not leave partial data.

    The test opens a low‑level connection via `get_connection()`, performs an
    INSERT, then deliberately raises an exception before committing. After the
    context exits (which rolls back implicitly because `commit()` was never
    called), the broker should not be present in the database.
    """
    db_file = tmp_path / "isolated.db"
    engine = StorageEngine(db_path=db_file)

    # Begin a transaction manually using the engine's connection helper
    try:
        with engine.get_connection() as conn:
            # SQLite autocommit is disabled when we issue BEGIN
            conn.execute("BEGIN")
            conn.execute(
                "INSERT INTO brokers (name, host, port, use_ssl) VALUES (?, ?, ?, ?)",
                ("TempBroker", "127.0.0.1", 1883, 0),
            )
            # Deliberately raise to abort the transaction
            raise RuntimeError("Simulated failure")
    except RuntimeError:
        # Expected path – the transaction should be rolled back
        pass

    # After the failed transaction, the broker list should be empty
    all_brokers = engine.get_all_brokers()
    assert all_brokers == []


def test_multiple_connections_share_state(tmp_path):
    """Two separate `StorageEngine` instances pointing at the same file share data.

    This validates that the on‑disk SQLite file is correctly used across
    connections and that changes are visible to new connections.
    """
    db_file = tmp_path / "shared.db"
    engine_a = StorageEngine(db_path=db_file)
    engine_b = StorageEngine(db_path=db_file)

    broker = BrokerProfile(name="SharedBroker", host="example.com")
    created = engine_a.create_broker(broker)

    # Retrieve via the second engine instance – should see the same record
    fetched = engine_b.get_broker_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "SharedBroker"
    assert fetched.host == "example.com"
