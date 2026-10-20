# Implementation Tasks: MQTT Antena Mobile

## 1. Overview
This document outlines the actionable, phased task breakdown for developing **MQTT Antena Mobile** in accordance with [functional_spec.md](file:///Users/buzz/code/mqtt-antena-mobile/specs/functional_spec.md) and [technical_spec.md](file:///Users/buzz/code/mqtt-antena-mobile/specs/technical_spec.md).

---

## 2. Mandatory Workflow & Interaction Rules

To ensure strict engineering discipline and alignment, the following rules apply to all tasks:
1. **Branching Prompt:** Prior to starting any new implementation or task, the agent/developer MUST prompt the user asking whether a new Git branch should be created.
2. **Virtual Environment Enforcement:** All development, dependency management, script execution, testing, and builds MUST strictly occur inside the dedicated Python `3.11.14` virtual environment (`.venv`). Never use global Python environments.
3. **Completion Confirmation:** When a task is completed, the agent MUST explicitly ask the user for confirmation before marking the task as done.
4. **Pull Request (PR) Prompt:** Upon task or feature completion, the agent MUST ask the user if they would like to create a Pull Request (PR).

---

## 3. Phase 1: Environment, Git & Scaffolding Setup

- [x] **Task 1.1: Git Versioning, Virtual Environment & Scaffolding**
  - Initialize Git versioning (`git init`).
  - Prompt the user if a new branch should be created for initial implementation.
  - Create `.gitignore` ignoring `.venv/`, `data/`, `*.db`, `build/`, `dist/`, `__pycache__/`, `.pytest_cache/`, and local IDE artifacts.
  - Create Python `3.11.14` virtual environment (`.venv`).
  - Install `flet==1.0.4` and `paho-mqtt` inside `.venv`.
  - Create initial Flet scaffolding using the command `flet create`.
  - Verify that the scaffold runs cleanly inside `.venv`.
  - Ask user for completion confirmation and if a PR should be created.

- [x] **Task 1.2: Project Configuration & Automation Makefile**
  - Create `pyproject.toml` with dependencies (`flet==1.0.4`, `paho-mqtt>=2.0.0`, `pytest`, `pytest-asyncio`) and project metadata.
  - Create root `Makefile` with recipes: `setup`, `run`, `dev`, `test`, `build-apk`, `clean`, ensuring all commands execute within `.venv`.
  - Ask user for completion confirmation and if a PR should be created.

- [x] **Task 1.3: App Assets Setup**
  - Create editable vector artwork `src/assets/icon.svg` (antenna motif matching MQTT Antena).
  - Generate rasterized `src/assets/icon.png`.
  - Ask user for completion confirmation and if a PR should be created.

---

## 4. Phase 2: Data Models & Persistence (`src/models.py` & `src/storage.py`)

- [x] **Task 2.1: Shared Data Models (`src/models.py`)**
  - Define `BrokerProfile` dataclass: `id`, `name`, `host`, `port`, `use_ssl`, `username`, `password`, `created_at`.
  - Define `MQTTMessage` dataclass: `timestamp`, `topic`, `payload`, `qos`, `retained`, `broker_id`.
  - Define `ConnectionStatus` enum (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `ERROR`).
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 2.2: SQLite Database & Storage Engine (`src/storage.py`)**
  - Implement automatic `data/antena.db` and directory initialization on first launch (git-ignored).
  - Implement idempotent schema migration (`CREATE TABLE IF NOT EXISTS brokers ...`).
  - Implement broker CRUD operations:
    - `create_broker(broker: BrokerProfile) -> BrokerProfile`
    - `get_all_brokers() -> list[BrokerProfile]`
    - `get_broker_by_id(broker_id: int) -> Optional[BrokerProfile]`
    - `update_broker(broker: BrokerProfile) -> bool`
    - `delete_broker(broker_id: int) -> bool`
  - Ask user for completion confirmation and if a PR should be created.

- [x] **Task 2.3: Storage Unit Tests (`tests/test_storage.py`)**
  - Write and execute automated tests for SQLite table creation, CRUD operations, and transaction isolation inside `.venv`.
  - Ask user for completion confirmation and if a PR should be created.

---

## 5. Phase 3: Asynchronous MQTT Engine (`src/mqtt_client.py`)

- [X] **Task 3.1: Session Representation & Async Lifecycle**
  - Implement `ActiveSession` state container tracking Paho `Client`, connection status, and active subscriptions.
  - Implement async `connect_broker(broker: BrokerProfile) -> tuple[bool, Optional[str]]` with SSL/TLS context and credentials support.
  - Implement async graceful `disconnect_broker(broker_id: int)`.
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 3.2: Topic Subscription & Message Streaming**
  - Implement `subscribe(broker_id: int, topic: str, callback: Callable)`.
  - Default topic filter to `#` if left blank.
  - Implement `unsubscribe(broker_id: int)`.
  - Feed received messages into an `asyncio.Queue` and notify registered UI callbacks.
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 3.3: Message Publishing**
  - Implement `publish_message(broker_id: int, topic: str, payload: str, qos: int, retain: bool) -> tuple[bool, Optional[str]]`.
  - Enforce wildcard validation (`+` and `#` disallowed in publish topic).
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 3.4: MQTT Client Unit Tests (`tests/test_mqtt_client.py`)**
  - Write and execute unit tests for session registry, topic validation, and callback dispatching using mocks inside `.venv`.
  - Ask user for completion confirmation and if a PR should be created.

---

## 6. Phase 4: App Shell & Catppuccin Dark Theme (`src/main.py`)

- [X] **Task 4.1: Catppuccin Mocha Styling & Theme Config**
  - Configure Catppuccin Mocha palette: Base `#1e1e2e`, Mantle `#181825`, Surface `#313244`, Lavender `#b4befe`, Green `#a6e3a1`, Red `#f38ba8`, Crust `#11111b`.
  - Apply custom `ft.Theme` with dark mode and typography.
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 4.2: App Header & Persistent Navigation**
  - Implement header with 📡 **MQTT Antena Mobile** title and active connection indicator badge.
  - Implement persistent `ft.NavigationBar` with 3 destinations: **Brokers**, **Subscribe**, **Publish**.
  - Wire up view switching, state persistence across tab switches, and clean shutdown on app exit.
  - Ask user for completion confirmation and if a PR should be created.

---

## 7. Phase 5: UI Views Implementation (`src/views/`)

- [X] **Task 5.1: Brokers View (`src/views/brokers.py`)**
  - Build broker card list displaying name, host, port, SSL tag, and connection status badge.
  - Implement **Connect / Disconnect** toggle buttons with dynamic visual feedback.
  - Implement **Add Broker** modal form dialog with validation.
  - Implement **Edit Broker** and **Delete Broker** confirmation dialogs.
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 5.2: Subscribe View (`src/views/subscribe.py`)**
  - Build active broker dropdown (populated dynamically with currently connected brokers).
  - Handle empty state with guidance and shortcut button to Brokers view.
  - Build topic input field with `#` default placeholder.
  - Build control bar: **Start / Stop Listening** button and **Clear Console** button.
  - Build terminal log console container (`#11111b`) with monospaced stream and 500-message FIFO buffer.
  - Ask user for completion confirmation and if a PR should be created.

- [X] **Task 5.3: Publish View (`src/views/publish.py`)**
  - Build active broker dropdown selector with empty state handling.
  - Build destination topic text field with wildcard validation.
  - Build QoS segmented selector (`0`, `1`, `2`) defaulting to `0`.
  - Build Retain toggle switch / radio defaulting to `False`.
  - Build multiline message payload text field.
  - Build **Publish** button with immediate success toast or error snackbar feedback.
  - Ask user for completion confirmation and if a PR should be created.

---

## 8. Phase 6: Integration, Testing & Packaging

- [ ] **Task 6.1: End-to-End Local Verification**
  - Test end-to-end flow with a local Mosquitto or public test broker (e.g. HiveMQ public broker):
    1. Create broker profile.
    2. Connect and verify status turns green.
    3. Navigate to Subscribe and listen on `#`.
    4. Navigate to Publish, publish a test payload.
    5. Switch back to Subscribe and confirm message rendered in terminal console.
    6. Disconnect broker and ensure active broker dropdowns update accordingly.
  - Ask user for completion confirmation and if a PR should be created.

- [ ] **Task 6.2: Automated Test Suite**
  - Execute full test suite via `make test` within `.venv`.
  - Ask user for completion confirmation and if a PR should be created.

- [ ] **Task 6.3: Android APK Packaging Verification**
  - Run `make build-apk` inside `.venv` to verify Flet packaging pipeline and Android manifests.
  - Ask user for completion confirmation and if a PR should be created.

- [ ] **Task 6.4: Documentation**
  - Complete `README.md` with prerequisites, installation, development commands, and screenshots/usage instructions.
  - Ask user for completion confirmation and if a PR should be created.
