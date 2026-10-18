# Technical Specification: MQTT Antena Mobile

## 1. Document Overview
- **Project Name:** MQTT Antena Mobile
- **Document Version:** 1.0.0
- **Status:** Approved
- **Target Runtime:** Mobile (Android APK / iOS) & Desktop for Local Testing
- **Companion Document:** [specs/functional_spec.md](file:///Users/buzz/code/mqtt-antena-mobile/specs/functional_spec.md)

---

## 2. Technology Stack & Runtime Environment

### 2.1 Core Technologies
- **Programming Language:** Python `3.11.14` (managed via `pyenv` / system path).
- **Virtual Environment:** Python standard `venv` (`.venv`).
- **Application Framework:** [Flet](https://flet.dev/) `1.0.4` (Flutter-powered Python GUI framework).
- **MQTT Protocol Engine:** `paho-mqtt` (v2.x or v1.6.x compatible async client).
- **Persistence Engine:** Python standard library `sqlite3` (zero third-party binary driver dependencies).
- **Testing Framework:** `pytest` and `pytest-asyncio`.
- **Packaging & Build Tool:** Flet CLI (`flet build apk`).

### 2.2 Development Workflow & Git Guidelines
- **Mandatory Virtual Environment:** All development, testing, script executions, and package installations MUST strictly occur inside the dedicated Python `3.11.14` virtual environment (`.venv`). Never install packages or run commands using global Python environments.
- **Branching Prompt:** Before starting a new implementation or major task, the developer/agent must prompt the user asking whether a new Git branch should be created.
- **Task Completion Confirmation:** When a task is completed, the agent must always ask the user for confirmation before marking the task as completed.
- **Pull Request (PR) Prompt:** Upon task or feature completion, the agent must prompt the user asking whether a Pull Request (PR) should be created.

---

## 3. Project Scaffolding & Directory Structure

The project builds upon the official scaffolding recommended by the [Flet Documentation](https://flet.dev/docs/), generated initially using:
```bash
flet create . --template app
```

### 3.1 Directory Layout
```
mqtt-antena-mobile/
├── .gitignore                     # Git ignore rules (includes .venv, data/, build/, etc.)
├── Makefile                       # Make automation recipes (setup, dev, run, test, build-apk)
├── pyproject.toml                 # Project metadata, dependencies, and Flet configuration
├── README.md                      # Project documentation and quickstart
├── specs/
│   ├── functional_spec.md         # Functional requirements specification
│   ├── technical_spec.md          # Technical architecture specification (this document)
│   └── tasks.md                   # Implementation tasks breakdown
├── data/                          # Local persistent storage (GIT-IGNORED)
│   └── antena.db                  # SQLite database generated on first run
└── src/                           # Application source folder
    ├── main.py                    # App startup, shared state, theme, tab navigation, and workflow handlers
    ├── models.py                  # Shared broker-profile and MQTT message data structures
    ├── mqtt_client.py             # MQTT connection, subscription, publishing, and disconnect logic
    ├── storage.py                 # Local broker-profile persistence; passwords use secure storage
    ├── assets/
    │   ├── icon.svg               # Editable source artwork for the app icon
    │   └── icon.png               # Raster app icon generated from the SVG
    └── views/
        ├── brokers.py             # Broker list, connection status, and add/edit profile form
        ├── subscribe.py           # Topic subscription controls and live message console
        └── publish.py             # Broker selection and message publishing form
```

---

## 4. Design System & Catppuccin Dark Theme

The application user interface adheres to a clean, minimal design inspired by [MQTT Antena Web](https://fbossolan.github.io/mqtt-antena/), styled with the **Catppuccin Mocha** dark palette.

### 4.1 Color Palette
| Token Name | Hex Code | Catppuccin Token | UI Usage |
| :--- | :--- | :--- | :--- |
| **Background** | `#1e1e2e` | `Mocha Base` | Application scaffold and page background |
| **Mantle / Header** | `#181825` | `Mocha Mantle` | Top app bar, navigation bar, and dialog headers |
| **Surface / Card** | `#313244` | `Mocha Surface0` | Broker cards, input container cards, modal panels |
| **Surface Border** | `#45475a` | `Mocha Surface1` | Card outlines, input borders, dividers |
| **Primary Accent** | `#b4befe` | `Mocha Lavender` | Active tabs, primary buttons, highlighted topics |
| **Secondary Accent**| `#89b4fa` | `Mocha Blue` | Secondary actions, links, focus rings |
| **Text Primary** | `#cdd6f4` | `Mocha Text` | Main headers, label text, field values |
| **Text Muted** | `#a6adc8` | `Mocha Subtext0`| Placeholders, subheaders, port/host metadata |
| **Success / Connected**| `#a6e3a1` | `Mocha Green` | "Connected" badges, publish success alerts |
| **Danger / Disconnect**| `#f38ba8` | `Mocha Red` | "Disconnected" badges, delete/disconnect actions |
| **Warning** | `#f9e2af` | `Mocha Yellow` | "Connecting..." state, timeout alerts |
| **Terminal Background**| `#11111b` | `Mocha Crust` | Monospaced live subscription log console |
| **Terminal Text** | `#a6e3a1` / `#cdd6f4` | Green / Text | Monospaced message payloads and timestamps |

### 4.2 Typography & Iconography
- **Body & Headings:** Native platform sans-serif (Roboto / San Francisco) provided via Flet.
- **Terminal Console:** Monospaced font (`monospace` or `Courier New`) with high-contrast text.
- **Icons:** Standard Material icons via `ft.Icons` (`ROUTER`, `PODCAST`, `SEND`, `PLAY_ARROW`, `STOP`, `DELETE`, `ADD`, `CHECK_CIRCLE`).

---

## 5. Persistence Architecture (SQLite)

### 5.1 Lightweight Local Storage
- **Engine:** Python standard library `sqlite3`.
- **Location:** `data/antena.db` relative to app root (or mobile `app_data_dir`).
- **Initialization:** Created automatically on first app execution if the file does not exist.
- **Git Ignored:** The entire `data/` directory and `*.db` files are explicitly included in `.gitignore`.

### 5.2 Database Schema
```sql
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
```

### 5.3 Data Access Layer (`src/storage.py`)
- Standard CRUD methods:
  - `get_all_brokers() -> list[Broker]`
  - `get_broker_by_id(broker_id: int) -> Optional[Broker]`
  - `create_broker(broker: Broker) -> Broker`
  - `update_broker(broker: Broker) -> bool`
  - `delete_broker(broker_id: int) -> bool`

---

## 6. Asynchronous Concurrency & MQTT Client

### 6.1 Concurrency Model
The application leverages Flet's asynchronous programming model:
```python
async def main(page: ft.Page):
    # Asynchronous initialization and event loop
```
- UI operations, navigation transitions, and database queries are non-blocking.
- MQTT protocol interactions use `asyncio` task wrappers around non-blocking network socket operations.

### 6.2 MQTT Client Architecture (`src/mqtt_client.py`)
The `MQTTClientManager` maintains a registry of active broker sessions:
```python
class ActiveSession:
    broker_id: int
    name: str
    client: mqtt.Client
    is_connected: bool
    status: str  # "disconnected", "connecting", "connected", "error"
    error_message: Optional[str]
    current_subscription: Optional[str]
```

#### Key Capabilities:
1. **Async Connect / Disconnect:**
   - Connects to broker with host, port, username, password, and SSL context if enabled.
   - Paho callbacks (`on_connect`, `on_disconnect`, `on_message`) emit events into an internal `asyncio.Queue`.
2. **Active Broker Registry:**
   - Exposes `get_connected_brokers()` returning a list of currently connected broker instances for dropdown selectors on Pages 2 & 3.
3. **Live Subscription Stream:**
   - Supports listening on `#` (default) or a specific topic.
   - Incoming messages are buffered and dispatched to registered UI subscriber callbacks.
4. **Message Publishing:**
   - Non-blocking `publish(broker_id, topic, payload, qos, retain)` method with success verification.

---

## 7. Component & View Implementation

### 7.1 Navigation & App Shell (`src/main.py`)
- Persistent `ft.NavigationBar` with 3 destinations:
  1. `ft.NavigationDestination(icon=ft.Icons.ROUTER_OUTLINED, selected_icon=ft.Icons.ROUTER, label="Brokers")`
  2. `ft.NavigationDestination(icon=ft.Icons.PODCAST_OUTLINED, selected_icon=ft.Icons.PODCAST, label="Subscribe")`
  3. `ft.NavigationDestination(icon=ft.Icons.SEND_OUTLINED, selected_icon=ft.Icons.SEND, label="Publish")`
- App header showing 📡 **MQTT Antena Mobile** and current connection badge.
- Built-in Catppuccin Mocha theme configuration and styling definitions.

### 7.2 Page 1: Brokers View (`src/views/brokers.py`)
- **Profile List:** ListView of cards rendering:
  - Broker name, `host:port`, SSL badge if active.
  - Dynamic status indicator (`Connected` [green], `Connecting` [yellow], `Disconnected` [red]).
  - Primary button: **Connect** or **Disconnect**.
  - Action buttons: **Edit** (pencil modal) and **Delete** (trash icon with confirm dialog).
- **Floating Action Button (FAB):** Opens an `ft.AlertDialog` form to add a new broker with validation.

### 7.3 Page 2: Subscribe View (`src/views/subscribe.py`)
- **Broker Dropdown (`ft.Dropdown`):** Dynamically populated with `mqtt_client.get_connected_brokers()`.
- **Topic Input (`ft.TextField`):** Hint text: *"Topic (leave empty for # to listen to all)"*.
- **Control Bar (`ft.Row`):**
  - **Start / Stop Listening Button (`ft.ElevatedButton`):** Toggles state, updates button color/icon.
  - **Clear Button (`ft.IconButton`):** Clears the terminal log view.
- **Terminal Console (`ft.Container`):**
  - Background: `#11111b`, rounded corners, border `#45475a`.
  - Content: `ft.ListView` with `auto_scroll=True`.
  - Cap: Maximum 500 lines maintained via a FIFO circular buffer (`collections.deque(maxlen=500)`).
  - Log format:
    ```
    [18:24:02.105] sensors/kitchen/temp (QoS 0)
    ↳ {"temperature": 22.4, "humidity": 55}
    ```

### 7.4 Page 3: Publish View (`src/views/publish.py`)
- **Broker Dropdown:** Select target from active connected brokers.
- **Topic Input:** Required single-line text input (wildcard validation check).
- **QoS Selector (`ft.SegmentedButton` or `ft.Dropdown`):** Options: `0` (At most once), `1` (At least once), `2` (Exactly once). Default: `0`.
- **Retain Toggle (`ft.Switch` or `ft.RadioGroup`):** Default: `False`.
- **Payload Field (`ft.TextField`):** Multiline input with expandable height (e.g. `min_lines=4`, `max_lines=10`).
- **Publish Button (`ft.FilledButton`):** Dispatches message via `mqtt_client.publish()`, displays success toast or error snackbar.

---

## 8. Build, Automation & Makefile

The project provides standard automation recipes via a root `Makefile`:

```makefile
# MQTT Antena Mobile - Build & Development Automation
PYTHON_VERSION := 3.11.14
PYENV_PYTHON   := $(shell pyenv prefix $(PYTHON_VERSION) 2>/dev/null)/bin/python
PYTHON         := $(if $(wildcard $(PYENV_PYTHON)),$(PYENV_PYTHON),python3)
VENV           := .venv
VENV_BIN       := $(VENV)/bin

.PHONY: help setup dev run test build-apk clean

help:
	@echo "Available commands:"
	@echo "  make setup      - Create virtualenv and install dependencies"
	@echo "  make run        - Run application locally with Flet"
	@echo "  make dev        - Run application with hot-reload"
	@echo "  make test       - Run unit tests with pytest"
	@echo "  make build-apk  - Build release Android APK using Flet"
	@echo "  make clean      - Clean cache, build outputs, and virtualenv"

setup:
	@echo "Creating virtual environment using Python $(PYTHON_VERSION)..."
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e ".[dev]" || $(VENV_BIN)/pip install flet==1.0.4 paho-mqtt pytest pytest-asyncio
	@echo "Setup complete. Activate with: source $(VENV)/bin/activate"

run:
	$(VENV_BIN)/flet run src/main.py

dev:
	$(VENV_BIN)/flet run -d src/main.py

test:
	$(VENV_BIN)/pytest tests/ -v

build-apk:
	@echo "Building Android APK with Flet..."
	$(VENV_BIN)/flet build apk --project-name "mqtt_antena_mobile" --product-name "MQTT Antena"

clean:
	rm -rf $(VENV) build/ dist/ __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

## 9. Testing Strategy

### 9.1 Unit Testing
- **Database & Storage Tests:** Validate SQLite schema creation, CRUD operations, and transaction integrity (`tests/test_storage.py`).
- **MQTT Client Tests:** Validate topic validation, broker session lifecycle, and message queue dispatch using mocks (`tests/test_mqtt_client.py`).
- **UI State Tests:** Validate active broker filtering, form validation (e.g., publish topic wildcard rejection), and buffer limits (`tests/test_views.py`).

### 9.2 Local Integration & Verification
- Local verification with embedded or local Mosquitto broker:
  ```bash
  mosquitto -p 1883
  ```
- Hot-reload verification via `make dev`.

---

## 10. Security & Edge Considerations

1. **Local Credentials:** Stored locally in `data/antena.db`. File permissions restricted to user-only (`0600`) where supported by OS.
2. **Network Timeouts:** Connection handshake timeout set to 5 seconds to prevent freezing on unreachable hosts.
3. **Buffer Protection:** FIFO message deque bounded to 500 entries to prevent memory exhaustion on mobile devices.
4. **Clean Disconnect on Exit:** Application lifecycle hook (`page.on_close` / `page.on_disconnect`) cleanly terminates all open Paho network loops.
