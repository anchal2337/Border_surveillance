import {
  Camera,
  Alert,
  EvidenceItem,
  EvidenceVerifyResult,
  Personnel,
  Vehicle,
  VehicleCrossing,
  CameraZone,
  UserProfile,
  AuthResponse,
  StorageHealth,
  AuditLogItem,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";

const TOKEN_KEY = "ibvap_token";
const USER_KEY = "ibvap_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

export function getStoredUser(): AuthResponse | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredUser(user: AuthResponse) {
  if (typeof window !== "undefined") {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set Content-Type if sending FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

// -----------------------------------------------------------------------------
// Authentication
// -----------------------------------------------------------------------------
export async function login(username: string, password: string): Promise<AuthResponse> {
  const data = await request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  setStoredUser(data);
  return data;
}

export async function getCurrentUser(): Promise<UserProfile> {
  return request<UserProfile>("/api/v1/auth/me");
}

// -----------------------------------------------------------------------------
// Cameras & Ingestion
// -----------------------------------------------------------------------------
export async function getCameras(): Promise<Camera[]> {
  return request<Camera[]>("/api/v1/cameras");
}

export async function connectCamera(cameraId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/api/v1/cameras/${cameraId}/connect`, {
    method: "POST",
  });
}

export async function disconnectCamera(cameraId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/api/v1/cameras/${cameraId}/disconnect`, {
    method: "POST",
  });
}

export async function uploadVideo(formData: FormData): Promise<Camera> {
  return request<Camera>("/api/v1/cameras/upload-video", {
    method: "POST",
    body: formData,
  });
}

export async function createCamera(payload: {
  id: string;
  name: string;
  sector_zone: string;
  source_type: string;
  stream_url: string;
  fps?: number;
  resolution?: string;
  ai_pipeline?: string;
}): Promise<Camera> {
  return request<Camera>("/api/v1/cameras", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// -----------------------------------------------------------------------------
// Streams & Telemetry
// -----------------------------------------------------------------------------
export function getLiveFeedUrl(cameraId: string): string {
  return `${API_BASE_URL}/api/v1/streams/${cameraId}/feed`;
}

export function getSnapshotUrl(cameraId: string): string {
  return `${API_BASE_URL}/api/v1/streams/${cameraId}/snapshot?t=${Date.now()}`;
}

export function getMediaUrl(relativePath?: string): string {
  if (!relativePath) return "/placeholder-tactical.png";
  if (relativePath.startsWith("http://") || relativePath.startsWith("https://")) {
    return relativePath;
  }
  const clean = relativePath.startsWith("/") ? relativePath : `/${relativePath}`;
  return `${API_BASE_URL}${clean}`;
}

// -----------------------------------------------------------------------------
// Dynamic Zones
// -----------------------------------------------------------------------------
export async function getCameraZones(cameraId: string): Promise<CameraZone[]> {
  return request<CameraZone[]>(`/api/v1/zones/${cameraId}`);
}

export async function updateCameraZones(
  cameraId: string,
  geofence?: number[][],
  tripwire?: number[][]
): Promise<{ status: string; camera_id: string; updated_zones: string[] }> {
  return request<{ status: string; camera_id: string; updated_zones: string[] }>(`/api/v1/zones/${cameraId}`, {
    method: "POST",
    body: JSON.stringify({
      camera_id: cameraId,
      geofence: geofence ?? null,
      tripwire: tripwire ?? null,
    }),
  });
}

// -----------------------------------------------------------------------------
// Real-Time Alerts
// -----------------------------------------------------------------------------
export async function getAlerts(limit: number = 50, severity?: string): Promise<Alert[]> {
  const query = new URLSearchParams({ limit: limit.toString() });
  if (severity) query.set("severity", severity);
  return request<Alert[]>(`/api/v1/alerts?${query.toString()}`);
}

export async function getAlertsSummary(): Promise<{
  total_alerts: number;
  unacknowledged: number;
  critical_threats: number;
  last_alert_time?: string;
}> {
  return request<{
    total_alerts: number;
    unacknowledged: number;
    critical_threats: number;
    last_alert_time?: string;
  }>("/api/v1/alerts/summary");
}

export async function acknowledgeAlert(alertId: string, notes?: string): Promise<Alert> {
  return request<Alert>(`/api/v1/alerts/${alertId}/acknowledge`, {
    method: "POST",
    body: JSON.stringify({ resolution_notes: notes || "Acknowledged by Sentry Console" }),
  });
}

// -----------------------------------------------------------------------------
// Forensic Evidence Locker
// -----------------------------------------------------------------------------
export async function getEvidence(limit: number = 50, status?: string, cameraId?: string): Promise<EvidenceItem[]> {
  const query = new URLSearchParams({ limit: limit.toString() });
  if (status) query.set("status", status);
  if (cameraId) query.set("camera_id", cameraId);
  return request<EvidenceItem[]>(`/api/v1/evidence?${query.toString()}`);
}

export async function getEvidenceById(evidenceId: string): Promise<EvidenceItem> {
  return request<EvidenceItem>(`/api/v1/evidence/${evidenceId}`);
}

export async function verifyEvidenceHash(evidenceId: string): Promise<EvidenceVerifyResult> {
  return request<EvidenceVerifyResult>(`/api/v1/evidence/${evidenceId}/verify`, {
    method: "POST",
  });
}

export async function updateEvidenceStatus(
  evidenceId: string,
  status: string,
  resolutionNotes?: string
): Promise<EvidenceItem> {
  return request<EvidenceItem>(`/api/v1/evidence/${evidenceId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, resolution_notes: resolutionNotes }),
  });
}

// -----------------------------------------------------------------------------
// Whitelist: Personnel (FRS) & Vehicles (ANPR)
// -----------------------------------------------------------------------------
export async function getPersonnel(): Promise<Personnel[]> {
  return request<Personnel[]>("/api/v1/whitelist/personnel");
}

export async function uploadPersonnelPhoto(formData: FormData): Promise<Personnel> {
  return request<Personnel>("/api/v1/whitelist/personnel/upload-photo", {
    method: "POST",
    body: formData,
  });
}

export async function deletePersonnel(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/v1/whitelist/personnel/${id}`, {
    method: "DELETE",
  });
}

export async function getVehicles(): Promise<Vehicle[]> {
  return request<Vehicle[]>("/api/v1/whitelist/vehicles");
}

export async function registerVehicle(payload: {
  license_plate: string;
  vehicle_type?: string;
  owner_name?: string;
  department?: string;
  notes?: string;
}): Promise<Vehicle> {
  return request<Vehicle>("/api/v1/whitelist/vehicles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteVehicle(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/v1/whitelist/vehicles/${id}`, {
    method: "DELETE",
  });
}

export async function getCrossings(limit: number = 50): Promise<VehicleCrossing[]> {
  return request<VehicleCrossing[]>(`/api/v1/crossings?limit=${limit}`);
}

// -----------------------------------------------------------------------------
// System, Storage & Audit
// -----------------------------------------------------------------------------
export async function getStorageHealth(): Promise<StorageHealth> {
  return request<StorageHealth>("/api/v1/system/disk-metrics");
}

export async function getAuditLogs(limit: number = 100): Promise<AuditLogItem[]> {
  return request<AuditLogItem[]>(`/api/v1/audit-logs?limit=${limit}`);
}

export async function pruneEvidence(maxAgeDays: number = 30): Promise<{
  status: string;
  files_removed: number;
  mb_reclaimed: number;
}> {
  return request<{ status: string; files_removed: number; mb_reclaimed: number }>("/api/v1/system/prune-evidence", {
    method: "POST",
    body: JSON.stringify({ max_age_days: maxAgeDays }),
  });
}
