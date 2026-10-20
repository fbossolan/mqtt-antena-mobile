📡  MQTT Antena Mobile

MQTT Antena Mobile is a lightweight Flet client for inspecting and testing MQTT traffic from Android or a development desktop. It is designed for the common field-debugging loop: save a broker connection, monitor its topics, and publish a test message without leaving the app.


## Features

- Save, edit, and delete multiple MQTT broker profiles.
- Connect to more than one broker at a time, with visible connection status.
- Support username/password authentication and TLS/SSL connections.
- Subscribe to a specific topic or leave the filter blank to listen on `#`.
- View a live, terminal-style message console with a 500-message buffer.
- Publish text or JSON payloads with QoS `0`, `1`, or `2`, and an optional retain flag.
- Keep broker profiles in a local SQLite database; no account or cloud service is required.

## Prerequisites

- Python **3.11.14**. The Makefile uses `pyenv` when that version is available and otherwise falls back to `python3`.
- `make`.
- For local desktop development, the platform requirements needed by Flet.
- For Android builds, Flet's required Flutter SDK and the Android build toolchain. Flet prompts to install its required Flutter SDK if it is not already available.
- Network access to the MQTT broker you intend to use.

## Installation

Clone the repository, then create the project virtual environment and install the dependencies:

```bash
make setup
```

All development commands below use `.venv`; do not install or run the project's dependencies with a global Python interpreter.

## Development commands

| Command | Purpose |
| --- | --- |
| `make run` | Run the app in a desktop window. |
| `make dev` | Run the desktop app with Flet hot reload. |
| `make test` | Run the complete pytest suite. |
| `make build-apk` | Build the Android APK. |
| `make clean` | Remove generated build output and local Python/test caches. |

Run `make help` to display the same command reference.

### Testing

The unit and view tests run without an MQTT server:

```bash
.venv/bin/pytest tests/ -v -k 'not e2e'
```

`make test` also runs the end-to-end MQTT tests. Those tests make a real network connection to the test broker configured in `tests/test_e2e.py`, so run them only when that broker is reachable and safe to use.

## Using the app

### 1. Add and connect a broker

1. Open the **Brokers** tab and choose **Add broker**.
2. Enter a connection name, host, and port. MQTT normally uses port `1883`; use the broker's TLS port (often `8883`) and enable **Use SSL / TLS** when appropriate.
3. Enter optional credentials and save the profile.
4. Select **Connect**. A green **Connected** badge confirms that the session is ready.

Profiles are stored only on the device in a local SQLite database. Treat an exported device backup accordingly, because broker credentials may be stored with the profile.

### 2. Monitor topics

1. Open **Subscribe** and select a connected broker.
2. Enter a topic filter such as `sensors/kitchen/#`, or leave it blank to subscribe to `#`.
3. Choose **Start listening**.
4. Incoming entries show their timestamp, topic, QoS, retained state, and payload in the terminal console.

Choose **Stop listening** to unsubscribe, or **Clear console** to remove the currently displayed messages. The in-memory console retains only the newest 500 messages and is cleared when the app closes.

### 3. Publish a message

1. Open **Publish** and select a connected broker.
2. Enter a destination topic, for example `sensors/kitchen/command`.
3. Choose QoS `0`, `1`, or `2`, optionally enable **Retain message**, and enter the payload.
4. Choose **Publish**.

Publish topics cannot be blank or contain MQTT wildcards (`+` or `#`). To verify a message end-to-end, subscribe to the same topic (or `#`) before publishing.

## Build and install for Android

Create an APK with:

```bash
make build-apk
```

The APK is written to `build/apk/mqtt-antena-mobile.apk`. To install it from a development machine with Android Debug Bridge enabled:

```bash
adb install -r build/apk/mqtt-antena-mobile.apk
```

Alternatively, copy the APK to the device and install it through Android's package installer after allowing installs from that source.

### Packaging note

Flet packages the configured `src/` directory as the Python application root. App modules therefore import sibling modules such as `models`, `mqtt_client`, and `views` directly; they must not use a `src.*` prefix. If Android reports `ModuleNotFoundError: No module named 'src'`, rebuild the APK from this repository revision rather than reinstalling an older artifact.

## Data and security

- Broker profiles are created locally on first use in `data/antena.db` for desktop development; generated data and build output are ignored by Git.
- TLS/SSL encrypts the connection between the app and a broker when enabled. It does not replace the need to verify the broker host, credentials, and network you are connecting to.
- Messages and the subscription console are transient; they are not persisted as message history.

## Project layout

```text
src/
├── main.py          # Flet app shell, dark theme, and navigation
├── models.py        # Broker, message, and connection-state models
├── mqtt_client.py   # MQTT connection, subscription, and publish lifecycle
├── storage.py       # SQLite broker-profile persistence
├── assets/          # Application icon assets
└── views/           # Brokers, Subscribe, and Publish screens
```

