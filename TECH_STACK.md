# IBVAP // INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM
## Technical Stack & Architectural Specification

---

### Executive Overview
**IBVAP** is an air-gapped, on-premise, defense-grade video analytics and perimeter surveillance command system. It provides real-time multi-camera video streaming, zone calibration, instant alert distribution, biometric/vehicle registries, and forensic evidence tracking.

```
+-----------------------------------------------------------------------------------+
|                           EDGE SENSORS & CAMERAS                                  |
|   (RTSP Streams / ONVIF / Night Vision Thermal / Local MP4 Video Feeds)           |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                           BACKEND CORE SYSTEM ENGINE                              |
|   - OpenCV Video Capture Thread (Ring-Buffer Frame Queue & MJPEG Generator)       |
|   - Cryptographic Evidence Sealing (SHA-256 Checksums & Image Storage)            |
|   - Storage Lifecycle Manager (Automated FIFO Evidence Purging)                  |
+--------------------+-------------------------------------+------------------------+
                     |                                     |
                     v                                     v
+----------------------------------+     +------------------------------------------+
|     PERSISTENCE & AUDIT LOG      |     |           FASTAPI ASYNC GATEWAY          |
|  - SQLite (WAL Mode)             |     |  - High-Speed REST Endpoints             |
|  - SQLAlchemy 2.0 (Thread-Safe)  |     |  - Dual WebSockets (/ws/alerts, /ws/tele)|
|  - Append-Only Audit Trail       |     |  - MJPEG Multipart Video Streamer        |
+----------------------------------+     +--------------------+---------------------+
                                                              |
                                                              v
+-----------------------------------------------------------------------------------+
|                     FRONTEND SENTRY COMMAND CONSOLE (NEXT.JS)                     |
|  - Real-Time Tactical HUD (Live MJPEG Stream & Telemetry HUD)                     |
|  - Interactive Zone Studio (HTML5 Canvas Polygon & Tripwire Editor)              |
|  - WebSocket Alerts Stream & Procedural Web Audio Perimeter Siren                 |
|  - Forensic Evidence Locker (Dual Crop/Snapshot Viewer & SHA-256 Verifier)        |
|  - Whitelist Registries (Biometric FRS Personnel & ANPR Authorized Plates)        |
|  - Station Health, Storage FIFO & Tamper-Evident Audit Trail                      |
+-----------------------------------------------------------------------------------+
```

---

## 1. Backend Technology Stack

| Layer / Subsystem | Technology / Library | Version / Standard | Technical Rationale & Role |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | **Python** | `3.10+` | Core execution environment supporting high-performance asynchronous I/O, multi-threading, and system integrations. |
| **Web Framework** | **FastAPI** | `>= 0.110.0` | Ultra-fast ASGI web framework with automatic OpenAPI documentation, dependency injection, and Pydantic validation. |
| **ASGI Web Server** | **Uvicorn** | `>= 0.28.0` | High-throughput asynchronous HTTP/1.1 and WebSocket server built on `uvloop` and `httptools`. |
| **Database & ORM** | **SQLite (WAL)**<br>**SQLAlchemy** | `v3.x (WAL Mode)`<br>`>= 2.0.28` | Zero-external-dependency on-premise persistence. Configured in Write-Ahead Logging (WAL) mode with connection pooling for concurrent thread-safe read/write operations. |
| **Real-Time WebSockets** | **WebSockets** (Starlette) | `>= 12.0` | Bidirectional real-time notification bus for instant perimeter alerts (`/ws/alerts`) and hardware telemetry streaming (`/ws/telemetry`). |
| **Video Ingestion & Streaming** | **OpenCV** (`opencv-python-headless`) | `>= 4.9.0` | Multi-threaded frame grabber from RTSP/ONVIF/file sources and low-latency MJPEG multipart HTTP broadcasting. |
| **Data Serialization** | **Pydantic** & **Pydantic-Settings** | `>= 2.6.4` | Strict type validation, environment variable loading, and request/response schema parsing. |
| **Security & Auth** | **python-jose**<br>**passlib[bcrypt]** | `>= 3.3.0`<br>`>= 1.7.4` | Stateless JWT token issuance and verification with salted bcrypt password hashing. Enforces RBAC permissions (`Commander`, `Operator`, `Viewer`, `Auditor`). |
| **Evidence Forensics** | **Python `hashlib`** | Native Standard Lib | Generates immutable SHA-256 cryptographic hashes for scene snapshots and target crops to ensure chain-of-custody evidentiary integrity. |
| **Asynchronous File I/O** | **aiofiles** | `>= 23.2.1` | Non-blocking asynchronous filesystem access for snapshot storage, media serving, and file uploads. |
| **Testing Suite** | **pytest** & **pytest-asyncio** | `>= 8.0.0` | Comprehensive integration and unit test suite verifying REST endpoints, WebSocket broadcasts, and auth flows. |

---

## 2. Frontend Technology Stack

| Layer / Subsystem | Technology / Library | Version / Standard | Technical Rationale & Role |
| :--- | :--- | :--- | :--- |
| **Framework** | **Next.js (App Router)** | `16.3.5` (Next 15+) | React enterprise framework utilizing Server Components, client-side hydration, optimized routing, and zero client-side waterfall latency. |
| **UI Library** | **React** & **React DOM** | `19.2.8` | Component-driven declarative UI architecture with concurrent rendering and high-frequency state updates. |
| **Language** | **TypeScript** | `5.x` | Strict compile-time type safety across all API payloads, WebSocket packets, camera streams, and calibration coordinates. |
| **Styling Engine** | **Tailwind CSS v4** & **Vanilla CSS** | `^4.0` | Utility-first styling combined with custom `@theme` tokens and zero runtime overhead for defense terminal UI. |
| **Iconography** | **Lucide React** | `^1.47.0` | Clean, crisp, lightweight SVG tactical icons matching defense instrumentation aesthetics. |

### Tactical UI Architecture & Humanized Design Tokens

Unlike generic SaaS templates that rely on standard rounded cards and purple/cyan glow effects, IBVAP implements a human-crafted military defense aesthetic:

1. **Strict Defense Palette**:
   - **Base Background**: `#111315` (Deep tactical charcoal)
   - **Surface**: `#191C1F` (Console module container)
   - **Card / Inset**: `#22262A` (Data wells and telemetry slots)
   - **Primary Accent**: `#D6A84F` (Command gold / perimeter active highlight)
   - **Secondary Accent**: `#A98A4F` (Telemetry labels and section badges)
   - **Text High-Contrast**: `#F2F1EC` (Mil-spec off-white readout)
   - **Muted Label**: `#92979B` (Metadata and parameter keys)
   - **Border Grid**: `#34383B` (1px precision mechanical demarcation)
   - **Alert Critical**: `#D95C5C` (DEFCON 1 perimeter breach strobe)
   - **Alert Success / Secure**: `#72A879` (DEFCON 5 sensor online beacon)

2. **Custom Typography System**:
   - **Command Headers & Callouts**: `Rajdhani` (geometric, sharp condensed military display font).
   - **Telemetry, GPS & Hashes**: `IBM Plex Mono` (true monospace tabular figures `font-variant-numeric: tabular-nums`).
   - **Interface Body & Logs**: `Plus Jakarta Sans` (high-density crisp legibility).

3. **Interactive HTML5 Canvas Zone Studio**:
   - Built with the native HTML5 2D Canvas API.
   - Allows interactive drawing and real-time vertex editing of multi-point polygon geofences and 2-point directional tripwires.
   - Automatically maps normalized coordinates `[0.0, 1.0]` to active camera sensor aspect ratios with instant 0ms edge deployment.

4. **Procedural Web Audio API Alert Synthesizer**:
   - 100% offline, procedural sound generation running directly in the browser.
   - Generates dual-frequency 880Hz sonar radar pings and modulated DEFCON-1 perimeter sirens with operator mute toggle.

---

## 3. Communication Protocols & Data Contracts

```
+------------------+-----------------------------+----------------------------------------------+
| Protocol         | Endpoint / Channel          | Purpose & Payload                            |
+------------------+-----------------------------+----------------------------------------------+
| HTTP / REST      | /api/v1/cameras             | Camera configuration, RTSP URLs, Zone setup  |
| HTTP / REST      | /api/v1/alerts              | Alert query, filter, and operator ACK        |
| HTTP / REST      | /api/v1/evidence            | Forensic snapshot cases & SHA-256 hashes     |
| HTTP / REST      | /api/v1/whitelist/personnel | FRS facial biometric vector enrollment       |
| HTTP / REST      | /api/v1/whitelist/vehicles  | ANPR license plate registry & crossing logs  |
| HTTP / REST      | /api/v1/system/health       | Storage FIFO usage, disk metrics, purge      |
| HTTP / REST      | /api/v1/system/audit-logs   | Tamper-evident operator activity audit trail |
| HTTP / Streaming | /api/v1/cameras/{id}/stream | Multi-client MJPEG video frame broadcast     |
| WebSocket        | /ws/alerts                  | Live push notifications for security events  |
| WebSocket        | /ws/telemetry               | Live FPS, track counts, and threat scores    |
+------------------+-----------------------------+----------------------------------------------+
```

---

## 4. Deployment & System Requirements

- **Operational Environment**: 100% Air-Gapped, On-Premise Local Area Network (LAN) or Edge Compute Box.
- **Minimum Hardware Specifications**:
  - **CPU**: Intel Core i5 / AMD Ryzen 5 (4+ Cores) or ARM64 (NVIDIA Jetson / x86_64).
  - **RAM**: 8 GB minimum (16 GB recommended for multi-camera streams).
  - **Storage**: SSD with minimum 64 GB dedicated to FIFO evidence ring-buffer storage.
- **Operating System**: Linux (Ubuntu 22.04 LTS / Debian 12) or Windows 10/11 64-bit.
