# IBVAP Backend API Reference Manual

> **Base URL**: `http://127.0.0.1:8000`  
> **Interactive Documentation**: `http://127.0.0.1:8000/docs` (Swagger UI) or `http://127.0.0.1:8000/redoc` (ReDoc)  
> **Protocol**: HTTP/1.1 (REST JSON) & WebSockets (`ws://`)  
> **Authentication Scheme**: JWT Bearer Token (`Authorization: Bearer <access_token>`)

---

## Quick Postman Workflow

1. **Import Collection**: Import [`backend/IBVAP_Postman_Collection.json`](./IBVAP_Postman_Collection.json) into Postman.
2. **Authenticate**: Call `POST /api/v1/auth/login` under folder `01. Authentication` using default credentials (`admin` / `admin123`). The test script automatically captures `access_token` and populates the `{{token}}` collection variable.
3. **Live Surveillance Feed**: Open `http://127.0.0.1:8000/api/v1/streams/CAM-01/feed` directly in Chrome, Edge, or an HTML `<img>` tag to watch the live 30 FPS dynamic sentry stream with sweeping radar vectors and real-time moving targets.
4. **WebSocket Radar HUD**: Connect to `ws://127.0.0.1:8000/ws/alerts` and `ws://127.0.0.1:8000/ws/telemetry` for sub-second incident push notifications and 4-model confidence telemetry.

---

## Master Table of Endpoints

| Category | Method | Endpoint Path | Clearance Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/` | Public | System status and database engine metadata |
| | `GET` | `/health` | Public | Node vitality and air-gapped readiness probe |
| | `GET` | `/api/v1/system/storage` | `COMMANDER`+ | Air-gapped disk allocation, evidence counts, DB size |
| | `POST` | `/api/v1/system/prune` | `SUPER_ADMIN` | Triggers FIFO retention purge on transient CCTV media |
| **Auth & RBAC** | `POST` | `/api/v1/auth/login` | Public | Authenticates credentials & returns JWT with role claim |
| | `GET` | `/api/v1/auth/me` | Any Authenticated | Current operator profile and assigned role |
| | `POST` | `/api/v1/auth/users` | `SUPER_ADMIN` | Registers a new sentry user (Operator, Commander, Auditor) |
| | `GET` | `/api/v1/auth/users` | `COMMANDER`+ | Lists all registered border security personnel |
| | `PATCH`| `/api/v1/auth/users/{user_id}/role` | `SUPER_ADMIN` | Updates / promotes an operator's clearance tier |
| **Cameras** | `GET` | `/api/v1/cameras` | `OPERATOR`+ | Lists all provisioned border cameras and statuses |
| | `POST` | `/api/v1/cameras` | `COMMANDER`+ | Provisions a new RTSP, Webcam, or Video stream |
| | `POST` | `/api/v1/cameras/{camera_id}/connect` | `OPERATOR`+ | Starts background ingestion and AI inference thread |
| | `POST` | `/api/v1/cameras/{camera_id}/disconnect` | `OPERATOR`+ | Halts ingestion thread and releases resources |
| | `POST` | `/api/v1/cameras/upload-video` | `OPERATOR`+ | Uploads local MP4/AVI for automated looping surveillance |
| **Streaming & Telemetry**| `GET` | `/api/v1/streams/{camera_id}/feed` | Public / App | Multi-client multipart/x-mixed-replace MJPEG video stream |
| | `GET` | `/api/v1/streams/{camera_id}/snapshot` | Public / App | High-resolution annotated single JPEG snapshot |
| | `GET` | `/api/v1/streams/{camera_id}/telemetry` | `OPERATOR`+ | Live stream FPS, active tracks, threat, and AI confidence matrix |
| **Dynamic Calibration** | `GET` | `/api/v1/zones/{camera_id}` | `OPERATOR`+ | Retrieves active geofence and tripwire coordinates |
| | `POST` | `/api/v1/zones/{camera_id}` | `COMMANDER`+ | Dynamically updates AI spatial zones without restart |
| **Alerts & Incidents** | `GET` | `/api/v1/alerts` | `OPERATOR`+ | Lists security alerts with multi-criteria filtering |
| | `GET` | `/api/v1/alerts/summary` | `OPERATOR`+ | Aggregated 24h threat and alert metrics |
| | `GET` | `/api/v1/alerts/{alert_id}` | `OPERATOR`+ | Detailed alert case report |
| | `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | `OPERATOR`+ | Operator logs resolution notes and resolves alert |
| **Forensic Evidence** | `GET` | `/api/v1/evidence` | `OPERATOR`+ | Lists forensic chain-of-custody incident records |
| | `GET` | `/api/v1/evidence/{evidence_id}` | `OPERATOR`+ | Complete forensic case file with image paths |
| | `POST` | `/api/v1/evidence/{evidence_id}/verify` | `OPERATOR`+ | Cryptographically validates SHA-256 file checksum |
| | `PATCH`| `/api/v1/evidence/{evidence_id}/status` | `COMMANDER`+ | Promotes investigation status (NEW -> INVESTIGATING -> CLOSED) |
| **ANPR Crossings** | `GET` | `/api/v1/crossings` | `OPERATOR`+ | Lists vehicle checkpoint crossings (filterable) |
| | `GET` | `/api/v1/crossings/summary` | `OPERATOR`+ | Aggregated checkpoint crossing counts & stats |
| | `GET` | `/api/v1/crossings/{id}` | `OPERATOR`+ | Single checkpoint crossing record with high-res photo |
| **Whitelist Registry** | `GET` | `/api/v1/whitelist/personnel` | `OPERATOR`+ | Lists whitelisted personnel (FRS biometric database) |
| | `POST` | `/api/v1/whitelist/personnel` | `COMMANDER`+ | Enrolls authorized person with raw 512-float vector |
| | `POST` | `/api/v1/whitelist/personnel/upload-photo` | `COMMANDER`+ | Enrolls personnel via portrait photo (CLAHE + auto 512-D embedding) |
| | `DELETE`| `/api/v1/whitelist/personnel/{id}` | `COMMANDER`+ | Revokes authorized personnel biometric record |
| | `GET` | `/api/v1/whitelist/vehicles` | `OPERATOR`+ | Lists whitelisted vehicle license plates (ANPR) |
| | `POST` | `/api/v1/whitelist/vehicles` | `COMMANDER`+ | Registers authorized vehicle plate and department |
| | `DELETE`| `/api/v1/whitelist/vehicles/{id}` | `COMMANDER`+ | Revokes authorized vehicle plate |
| | `POST` | `/api/v1/whitelist/sync` | `COMMANDER`+ | Forces two-way SQLite $\leftrightarrow$ AI JSON synchronization |
| **Tracking & Kinematics** | `GET` | `/api/v1/tracks/active` | `OPERATOR`+ | Live active target kinematics across all cameras |
| | `GET` | `/api/v1/tracks/{camera_id}/history` | `OPERATOR`+ | Historical track sessions & trajectories for a post |
| | `GET` | `/api/v1/tracks/sessions/{session_id}` | `OPERATOR`+ | Individual track session detail & coordinate array |
| **Audit Logs** | `GET` | `/api/v1/audit-logs` | `AUDITOR`+ | System-wide immutable non-repudiation audit trail |
| | `GET` | `/api/v1/audit-logs/{id}` | `AUDITOR`+ | Specific sequential audit log entry |
| **Dashboard**| `GET` | `/api/v1/dashboard/summary` | `OPERATOR`+ | Tactical C2 overview (fleet, alerts, active streams) |
| **WebSockets**| `WS` | `/ws/alerts` | Any Client | Sub-second real-time perimeter alert push broadcast |
| | `WS` | `/ws/telemetry` | Any Client | 1Hz real-time stream FPS and AI confidence matrix |

---

## Detailed Endpoint Specifications

### 1. Photo-Based Face Biometric Enrollment
- **Route**: `POST /api/v1/whitelist/personnel/upload-photo`
- **Content-Type**: `multipart/form-data`
- **Permissions**: `COMMANDER`, `SUPER_ADMIN`
- **Form Fields**:
  - `photo`: File (JPEG, PNG)
  - `full_name`: string (e.g. `"Major Vikram Batra"`)
  - `designation`: string (e.g. `"Commanding Officer"`)
  - `badge_number`: string (optional, e.g. `"CO-13JAK"`)
  - `department`: string (optional, default `"Perimeter Security"`)
  - `enhance`: boolean (optional, default `false` — applies CLAHE contrast enhancement for harsh sunlight / night operations)
- **Response**: `201 Created`
```json
{
  "id": "c1f73b64-884b-4c22-9fa0-379de3653112",
  "full_name": "Major Vikram Batra",
  "designation": "Commanding Officer",
  "badge_number": "CO-13JAK",
  "department": "Sector 4 Command",
  "photo_path": "/data/evidence/faces/a78b9c_photo.jpg",
  "is_authorized": true,
  "created_at": "2026-09-18T22:50:00Z"
}
```

### 2. ANPR Vehicle Checkpoint Crossings
- **Route**: `GET /api/v1/crossings`
- **Permissions**: `OPERATOR`, `COMMANDER`, `SUPER_ADMIN`
- **Query Parameters**:
  - `camera_id`: string (optional filter)
  - `license_plate`: string (optional partial search)
  - `is_whitelisted`: boolean (optional filter)
  - `crossing_type`: string (optional filter)
  - `limit`: int (default `100`, max `500`)
  - `offset`: int (default `0`)
- **Response**: `200 OK`
```json
[
  {
    "id": 1,
    "camera_id": "CAM-01",
    "track_id": 8,
    "license_plate": "ARMY-99X01",
    "ocr_confidence": 0.94,
    "vehicle_type": "jeep",
    "is_whitelisted": true,
    "crossing_type": "Checkpoint Tripwire Crossing",
    "image_path": "/data/vehicle_crossings/ARMY-99X01_crossing.jpg",
    "details": "Convoy Vehicle #8 (ARMY-99X01) passed checkpoint. Status: AUTHORIZED",
    "crossed_at": "2026-09-18T22:51:00Z"
  }
]
```

### 3. Checkpoint Crossings Summary
- **Route**: `GET /api/v1/crossings/summary`
- **Permissions**: `OPERATOR`, `COMMANDER`, `SUPER_ADMIN`
- **Response**: `200 OK`
```json
{
  "total_crossings": 45,
  "whitelisted_count": 38,
  "unregistered_count": 7,
  "latest_crossing_time": "2026-09-18T22:52:14Z"
}
```

### 4. Active Target Tracking & Kinematics
- **Route**: `GET /api/v1/tracks/active`
- **Permissions**: `OPERATOR`, `COMMANDER`, `SUPER_ADMIN`
- **Query Parameters**: `camera_id` (optional)
- **Response**: `200 OK`
```json
[
  {
    "track_id": 1,
    "camera_id": "CAM-01",
    "class_name": "person",
    "threat_score": 85,
    "behavior": "Tripwire Breach",
    "identity": "Target #1",
    "is_authorized": false,
    "speed_px_sec": 4.2,
    "dwell_sec": 8.5,
    "last_position": [340, 280]
  }
]
```

### 5. Historical Camera Trajectory Sessions
- **Route**: `GET /api/v1/tracks/{camera_id}/history`
- **Permissions**: `OPERATOR`, `COMMANDER`, `SUPER_ADMIN`
- **Query Parameters**:
  - `threat_min`: int (optional, e.g. `50`)
  - `limit`: int (default `50`)
  - `offset`: int (default `0`)
- **Response**: `200 OK`

### 6. Military Non-Repudiation Audit Logs
- **Route**: `GET /api/v1/audit-logs`
- **Permissions**: `AUDITOR`, `COMMANDER`, `SUPER_ADMIN`
- **Query Parameters**:
  - `action`: string (optional, e.g. `"PERSONNEL_ENROLLED"`, `"SYSTEM_STORAGE_PRUNED"`)
  - `entity_type`: string (optional, e.g. `"personnel"`, `"system"`, `"alert"`)
  - `user_id`: string (optional)
  - `limit`: int (default `50`)
  - `offset`: int (default `0`)
- **Response**: `200 OK`

### 7. Air-Gapped Storage Health & Disk Allocation
- **Route**: `GET /api/v1/system/storage`
- **Permissions**: `COMMANDER`, `SUPER_ADMIN`
- **Response**: `200 OK`
```json
{
  "total_disk_bytes": 510938472448,
  "free_disk_bytes": 185934893056,
  "used_disk_bytes": 325003579392,
  "evidence_dir_bytes": 1450284,
  "crossings_dir_bytes": 892014,
  "database_bytes": 262144,
  "evidence_count": 28,
  "crossings_count": 45,
  "alerts_count": 52,
  "is_healthy": true,
  "status_message": "Storage Optimal"
}
```

### 8. FIFO Storage Retention Purge
- **Route**: `POST /api/v1/system/prune`
- **Permissions**: `SUPER_ADMIN`
- **Body**:
```json
{
  "max_age_days": 30,
  "max_storage_mb": 5000
}
```
- **Response**: `200 OK`
```json
{
  "files_removed": 14,
  "bytes_reclaimed": 2849102,
  "status": "SUCCESS",
  "message": "Successfully reclaimed 2.72 MB (14 files)."
}
```

### 9. Real-Time Telemetry with AI Confidence Matrix
- **Route**: `GET /api/v1/streams/{camera_id}/telemetry`
- **Permissions**: `OPERATOR`, `COMMANDER`, `SUPER_ADMIN`
- **Response**: `200 OK`
```json
{
  "camera_id": "CAM-01",
  "fps": 29.8,
  "active_tracks": 2,
  "max_threat": 85,
  "engine_mode": "SYNTHETIC_SENTRY",
  "model_confidences": {
    "object_detection": 0.94,
    "tactical_threat": 0.96,
    "face_recognition": 0.92,
    "plate_ocr": 0.95
  },
  "timestamp": "2026-09-18T22:55:00Z"
}
```
