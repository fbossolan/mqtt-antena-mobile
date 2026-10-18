# Functional Specification: MQTT Antena Mobile

## 1. Document Overview
- **Project Name:** MQTT Antena Mobile
- **Document Version:** 1.0.0
- **Status:** Approved
- **Inspiration Reference:** [MQTT Antena Web](https://fbossolan.github.io/mqtt-antena/)

---

## 2. Product Summary & Problem Statement

### 2.1 Problem Statement
Developers, IoT engineers, and home automation enthusiasts frequently need to test, monitor, and debug MQTT message exchanges between microcontrollers, sensors, gateways, and backend services. Desktop tools and web-based applications (like MQTT Antena Web or desktop clients) are powerful but require a laptop or a workstation on the local network. 

When testing devices in the field, around a smart home, or at an edge installation, developers need a quick, reliable, lightweight mobile application on their smartphones that can connect to local or cloud MQTT brokers, inspect live message streams, and publish payloads on demand without bloat or friction.

### 2.2 Product Vision & Objective
**MQTT Antena Mobile** is a lightweight, mobile-first MQTT debugging and analysis tool inspired by the web application [MQTT Antena](https://fbossolan.github.io/mqtt-antena/). 

The application focuses on three essential workflows:
1. Managing and connecting to MQTT broker profiles.
2. Listening to live topic streams via a clean, terminal-style log.
3. Publishing customizable MQTT messages with configurable QoS and Retain flags.

### 2.3 Core Principles
- **Ultralight & Responsive:** Fast startup, minimal memory footprint, zero telemetry bloat.
- **Local-First & Private:** Single-user utility with no account registration or cloud sign-in required. All credentials remain stored locally on the device.
- **Developer-Centric UX:** Monospaced terminal logging, clear connection statuses, and immediate feedback.

---

## 3. User Personas & Use Cases

| Persona | Core Need | Typical Workflow |
| :--- | :--- | :--- |
| **IoT / Firmware Developer** | Validate sensor telemetry published over MQTT in the lab or field. | Connects to test broker, subscribes to `#`, observes incoming sensor readings in real-time. |
| **Home Automation Enthusiast** | Troubleshoot Home Assistant, Zigbee2MQTT, or ESPHome topics. | Subscribes to specific device topics (`homeassistant/sensor/#`), triggers state changes by publishing test commands. |
| **QA / Field Technician** | Verify MQTT broker connectivity and verify device command responses on-site. | Connects via Wi-Fi/cellular, injects mock commands, and verifies device status payloads. |

---

## 4. Information Architecture & Navigation

The application uses a 3-tab layout (or persistent navigation bar) providing instant access to the three core areas:

```
+-------------------------------------------------------------+
|                     MQTT Antena Mobile                      |
+-------------------------------------------------------------+
|                                                             |
|   [ Tab 1: Brokers ]   [ Tab 2: Subscribe ]   [ Tab 3: Publish ]
|                                                             |
+-------------------------------------------------------------+
```

1. **Brokers (Connections):** Manage broker profiles, initiate connections, and disconnect.
2. **Subscribe (Monitor):** Select an active broker, define a topic filter, and stream messages in a terminal view.
3. **Publish (Send):** Select an active broker, compose a topic, QoS, retain flag, and payload, then dispatch.

---

## 5. Detailed Functional Requirements

### 5.1 Page 1: Broker Management & Connectivity (`/brokers`)

The Brokers page allows users to create, store, edit, and connect to multiple MQTT broker profiles.

#### 5.1.1 Broker Profile Attributes
When adding or editing a broker, the user provides:
- **Connection Name:** A friendly user-defined label (e.g., *"Home Broker"*, *"EMQX Lab"*, *"Mosquitto Test"*).
- **Broker Host / URL:** IP address or hostname (e.g., `192.168.1.100` or `broker.hivemq.com`).
- **Port:** Network port number (Default: `1883` for unencrypted, `8883` for SSL/TLS).
- **SSL / TLS:** Toggle switch (Enabled / Disabled).
- **Username:** Optional string for authenticated brokers.
- **Password:** Optional string (masked input with show/hide toggle).

#### 5.1.2 Profile Management Actions
- **Add / Save Profile:** Form validation ensures required fields (`Name`, `Host`, `Port`) are present.
- **List Profiles:** Display all saved broker profiles showing:
  - Profile name
  - Host and Port (`host:port`)
  - Connection status pill (`Disconnected`, `Connecting`, `Connected`, `Error`)
- **Edit Profile:** Update saved broker configuration.
- **Delete Profile:** Remove a broker profile with a confirmation prompt.

#### 5.1.3 Connection State & Controls
- **Connect Button:** Initiates MQTT handshake with the specified broker.
- **Disconnect Button:** Gracefully closes the active MQTT session while keeping the broker profile and its saved credentials intact.
- **Status Feedback:** Clear visual feedback for:
  - `Disconnected` (default state on app launch)
  - `Connecting...` (in-progress state with activity indicator)
  - `Connected` (active socket, ready to subscribe/publish)
  - `Error` (descriptive error banner/message, e.g., timeout, bad credentials, unreachable host)
- **Multi-Broker Capability:** Multiple broker profiles can be saved, and multiple connections may be maintained concurrently.

---

### 5.2 Page 2: Subscribe & Live Topic Monitoring (`/subscribe`)

The Subscribe page enables live message consumption from an active broker session.

#### 5.2.1 Target Broker Selection
- **Active Broker Dropdown:** Displays a dropdown selector containing **only actively connected brokers**.
- **Empty State:** If no brokers are connected, the dropdown displays a notice: *"No active broker connected. Please connect from the Brokers tab."* with a direct navigation shortcut to the Brokers page.

#### 5.2.2 Subscription Filter
- **Topic Input Field:** Text field allowing the user to specify a topic string (e.g., `sensors/temp`, `device/+/status`).
- **Wildcard Default:** If the topic input field is left empty or blank, the application automatically defaults the subscription to `#` (subscribes to all topics on that broker).

#### 5.2.3 Subscription Controls
- **Start / Stop Listening Button:**
  - When idle: Displays **"Start Listening"** (starts subscription and streams incoming messages).
  - When active: Displays **"Stop Listening"** (unsubscribes / pauses the incoming stream).
- **Clear Console Button:** Clears all accumulated messages from the screen.

#### 5.2.4 Message Log Viewer (Terminal Style)
- **Log Presentation:** A dedicated scrolling terminal console with monospaced typography and dark/high-contrast styling.
- **Message Entry Format:** Each received message displays:
  - Timestamp (e.g., `[14:32:05.120]`)
  - Topic name (highlighted)
  - QoS level and Retained indicator (e.g., `[QoS 1 | Retained]`)
  - Payload text (rendered on a new line or indented)
- **Scroll Behavior:** Automatically scrolls to the bottom on new incoming messages, with manual scroll inspection supported.

---

### 5.3 Page 3: Message Publisher (`/publish`)

The Publish page provides a straightforward form to dispatch MQTT messages to a chosen broker.

#### 5.3.1 Target Broker Selection
- **Broker Dropdown:** Dropdown containing currently active (connected) brokers.
- If no brokers are connected, publishing is disabled and an explanatory prompt is displayed.

#### 5.3.2 Message Parameters
- **Topic Field:** Single-line text input for the destination topic (required). Note: Wildcards (`#`, `+`) are prohibited in publish topics per MQTT specification.
- **Quality of Service (QoS):** Integer selector or segmented control:
  - `0` - At most once (default)
  - `1` - At least once
  - `2` - Exactly once
- **Retain Flag:** Radio button or toggle selector:
  - `Retain: Yes / True`
  - `Retain: No / False` (default)
- **Message Payload Field:** Multiline text field for message content (supports JSON, plain text, numbers, or empty string).

#### 5.3.3 Publish Action & Feedback
- **Publish Button:** Dispatches the message to the broker.
- **Validation:** Ensures a valid topic is entered before sending.
- **Feedback Notification:**
  - Brief visual confirmation (toast / banner) indicating successful publication.
  - Clear error feedback if transmission fails (e.g., broker disconnected during transit).

---

## 6. Non-Functional & Quality Attributes

### 6.1 Performance & Resource Efficiency
- **Lightweight Runtime:** Fast application boot time (<1.5 seconds on standard devices).
- **Memory Management:** In-memory message log capped to a sensible buffer (e.g., 500 latest messages) to prevent memory bloating during heavy message floods.
- **Battery Optimization:** Network sockets managed cleanly when backgrounded or disconnected.

### 6.2 Data Storage & Persistence
- **Local Storage Only:** All broker configs (names, hosts, ports, credentials, SSL settings) are stored locally on the client device.
- **Session Ephemerality:** Message streams in the terminal viewer are transient (in-memory only); they are cleared when the app terminates or when the user clears the log.

### 6.3 Security
- **Credential Storage:** Passwords stored locally using secure on-device storage.
- **Transport Security:** Support for standard SSL/TLS (port 8883) encrypted connections.

---

## 7. Edge Cases & Error Handling

| Scenario | System Behavior |
| :--- | :--- |
| **No brokers connected when navigating to Subscribe / Publish** | Dropdown is disabled or empty with a warning badge and button: *"Go to Brokers"*. |
| **Connection drops mid-session** | Broker status immediately reflects `Disconnected` or `Error`; Subscribe stream pauses; Publish displays an error alert. |
| **Invalid topic format on Publish** | Validation error prevents submission if topic contains wildcards (`+`, `#`) or is blank. |
| **Broker authentication failure** | Connection state moves to `Error` with message: *"Authentication failed. Check username/password."* |
| **High frequency message flood** | Terminal log truncates older entries past buffer limit (e.g., 500 entries) to prevent UI freezing. |

---

## 8. Out of Scope (Version 1.0)
- Multi-user authentication / cloud account sync.
- Graphical charting / time-series metric graphs.
- Custom client SSL certificate file pickers (`.crt`, `.pem`) — basic TLS toggle only for v1.
- Permanent historical database storage of all received messages.
