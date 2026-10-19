"""Unit tests for src/storage.py."""

from datetime import datetime
import os
import pytest

from src.models import BrokerProfile
from src.storage import (
    StorageEngine,
    create_broker,
    delete_broker,
    get_all_brokers,
    get_broker_by_id,
    set_default_db_path,
    update_broker,
)


@pytest.fixture
def storage(tmp_path):
    """Provides a fresh StorageEngine with a temporary database file."""
    db_file = tmp_path / "test_antena.db"
    return StorageEngine(db_path=db_file)


class TestStorageInitialization:
    """Tests for database initialization and schema setup."""

    def test_in_memory_initialization(self):
        engine = StorageEngine(db_path=":memory:")
        assert engine.get_all_brokers() == []

    def test_idempotent_init(self, tmp_path):
        db_file = tmp_path / "idempotent.db"
        engine = StorageEngine(db_path=db_file)
        # Calling init_db again should not throw errors or wipe existing schema
        engine.init_db()
        assert engine.get_all_brokers() == []

    def test_directory_creation_and_file_permissions(self, tmp_path):
        sub_dir = tmp_path / "deep" / "nested" / "dir"
        db_file = sub_dir / "antena.db"
        engine = StorageEngine(db_path=db_file)

        assert sub_dir.exists()
        assert db_file.exists()
        # Verify file permissions (0600) on POSIX
        if os.name == "posix":
            file_mode = os.stat(db_file).st_mode & 0o777
            assert file_mode == 0o600


class TestBrokerCRUD:
    """Tests for broker CRUD operations."""

    def test_create_broker_success(self, storage):
        broker = BrokerProfile(
            name="Home Assistant",
            host="192.168.1.10",
            port=1883,
            use_ssl=False,
            username="home_user",
            password="secret_password",
        )
        created = storage.create_broker(broker)

        assert created.id is not None
        assert created.id >= 1
        assert created.name == "Home Assistant"
        assert created.host == "192.168.1.10"
        assert created.port == 1883
        assert created.use_ssl is False
        assert created.username == "home_user"
        assert created.password == "secret_password"
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_create_broker_validation_failure(self, storage):
        invalid_broker = BrokerProfile(name="", host="192.168.1.10")
        with pytest.raises(ValueError, match="Broker name is required"):
            storage.create_broker(invalid_broker)

        invalid_port_broker = BrokerProfile(name="Test", host="localhost", port=99999)
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            storage.create_broker(invalid_port_broker)

    def test_get_all_brokers(self, storage):
        assert storage.get_all_brokers() == []

        b1 = storage.create_broker(BrokerProfile(name="Broker 1", host="host1"))
        b2 = storage.create_broker(BrokerProfile(name="Broker 2", host="host2", port=8883, use_ssl=True))

        all_brokers = storage.get_all_brokers()
        assert len(all_brokers) == 2
        assert all_brokers[0].id == b1.id
        assert all_brokers[0].name == "Broker 1"
        assert all_brokers[1].id == b2.id
        assert all_brokers[1].name == "Broker 2"
        assert all_brokers[1].use_ssl is True

    def test_get_broker_by_id(self, storage):
        created = storage.create_broker(BrokerProfile(name="Cloud", host="broker.emqx.io"))
        fetched = storage.get_broker_by_id(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Cloud"
        assert fetched.host == "broker.emqx.io"

        non_existent = storage.get_broker_by_id(9999)
        assert non_existent is None

    def test_update_broker_success(self, storage):
        created = storage.create_broker(BrokerProfile(name="Initial Name", host="10.0.0.1", port=1883))

        created.name = "Updated Name"
        created.port = 8883
        created.use_ssl = True
        created.username = "new_user"

        success = storage.update_broker(created)
        assert success is True

        updated = storage.get_broker_by_id(created.id)
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.port == 8883
        assert updated.use_ssl is True
        assert updated.username == "new_user"

    def test_update_broker_missing_id(self, storage):
        broker = BrokerProfile(name="No ID", host="localhost")
        with pytest.raises(ValueError, match="Cannot update broker profile without an id"):
            storage.update_broker(broker)

    def test_update_broker_validation_failure(self, storage):
        created = storage.create_broker(BrokerProfile(name="Valid", host="localhost"))
        created.host = ""
        with pytest.raises(ValueError, match="Broker host is required"):
            storage.update_broker(created)

    def test_update_broker_not_found(self, storage):
        ghost_broker = BrokerProfile(id=9999, name="Ghost", host="ghost.host")
        success = storage.update_broker(ghost_broker)
        assert success is False

    def test_delete_broker(self, storage):
        b1 = storage.create_broker(BrokerProfile(name="To Delete", host="localhost"))
        b2 = storage.create_broker(BrokerProfile(name="To Keep", host="localhost"))

        assert storage.delete_broker(b1.id) is True
        assert storage.get_broker_by_id(b1.id) is None

        # Deleting again returns False
        assert storage.delete_broker(b1.id) is False

        # Remaining broker is untouched
        remaining = storage.get_all_brokers()
        assert len(remaining) == 1
        assert remaining[0].id == b2.id


class TestModuleLevelConvenienceFunctions:
    """Tests for module-level storage helper functions."""

    def test_module_wrappers(self, tmp_path):
        db_file = tmp_path / "convenience.db"
        set_default_db_path(db_file)

        created = create_broker(BrokerProfile(name="Global Broker", host="global.host"))
        assert created.id is not None

        all_b = get_all_brokers()
        assert len(all_b) == 1
        assert all_b[0].name == "Global Broker"

        by_id = get_broker_by_id(created.id)
        assert by_id is not None
        assert by_id.name == "Global Broker"

        created.name = "Global Broker Updated"
        assert update_broker(created) is True
        assert get_broker_by_id(created.id).name == "Global Broker Updated"

        assert delete_broker(created.id) is True
        assert get_all_brokers() == []
