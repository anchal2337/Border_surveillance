export type CameraStatus = "ONLINE" | "OFFLINE" | "STANDBY" | "RECONNECTING";

export interface Camera {
  id: string;
  name: string;
  sector_zone: string;
  source_type: "RTSP" | "WEBCAM" | "FILE" | "ONVIF";
  stream_url: string;
  status: CameraStatus;
  fps: number;
  resolution: string;
  ai_pipeline: string;
  is_active: boolean;
  last_heartbeat_at?: string;
  created_at?: string;
}

export type SeverityLevel = "INFO" | "WARNING" | "CRITICAL";

export interface Alert {
  id: string;
  camera_id: string;
  camera_name?: string;
  alert_type: string;
  severity: SeverityLevel;
  threat_score: number;
  behavior: string;
  label: string;
  details?: string;
  snapshot_url?: string;
  is_acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolution_notes?: string;
  created_at: string;
  timestamp?: string;
}

export type EvidenceStatus = "NEW" | "ACKNOWLEDGED" | "INVESTIGATING" | "RESOLVED";

export interface EvidenceItem {
  id: string;
  camera_id?: string;
  event: string;
  camera_name: string;
  location: string;
  track_id: number;
  object_label: string;
  class_name: string;
  severity: SeverityLevel;
  threat_score: number;
  behavior: string;
  identity?: string;
  speed_px_sec?: number;
  dwell_sec?: number;
  crop_image: string;
  scene_image: string;
  sha256_hash: string;
  status: EvidenceStatus;
  details?: string;
  assigned_to?: string;
  resolution_notes?: string;
  created_at: string;
}

export interface EvidenceVerifyResult {
  is_valid: boolean;
  computed_hash: string;
  expected_hash: string;
  file_path: string;
  message: string;
}

export interface Personnel {
  id: string;
  full_name: string;
  designation: string;
  badge_number?: string;
  department: string;
  photo_path?: string;
  is_authorized: boolean;
  created_at: string;
}

export interface Vehicle {
  id: string;
  license_plate: string;
  vehicle_type: string;
  owner_name?: string;
  department: string;
  is_whitelisted: boolean;
  notes?: string;
  created_at: string;
}

export interface VehicleCrossing {
  id: number;
  camera_id?: string;
  track_id: number;
  license_plate?: string;
  ocr_confidence: number;
  vehicle_type: string;
  is_whitelisted: boolean;
  crossing_type: string;
  image_path: string;
  source_file?: string;
  details?: string;
  crossed_at: string;
}

export interface TelemetryData {
  camera_id: string;
  camera_name?: string;
  fps: number;
  total_frames?: number;
  active_tracks: number;
  max_threat: number;
  is_synthetic?: boolean;
  engine_mode?: string;
  model_confidences?: {
    object_detection?: number;
    tactical_threat?: number;
    face_recognition?: number;
    plate_ocr?: number;
    [key: string]: number | undefined;
  };
  timestamp?: string;
}

export interface CameraZone {
  id: string;
  camera_id: string;
  name: string;
  zone_type: "GEOFENCE" | "TRIPWIRE" | "EXCLUSION";
  coordinates: string; // JSON string e.g. "[[100, 150], [500, 150]]"
  alert_on_entry: boolean;
  alert_on_exit: boolean;
  sensitivity: number;
  is_active: boolean;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: "SUPER_ADMIN" | "COMMANDER" | "OPERATOR" | "FORENSIC_AUDITOR";
  badge_number?: string;
  department: string;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: string;
  full_name: string;
  badge_number?: string;
  username: string;
}

export interface StorageHealth {
  total_disk_bytes: number;
  free_disk_bytes: number;
  used_disk_bytes: number;
  evidence_dir_bytes: number;
  crossings_dir_bytes: number;
  database_bytes: number;
  evidence_count: number;
  crossings_count: number;
  alerts_count: number;
  is_healthy: boolean;
  status_message: string;
}

export interface AuditLogItem {
  id: number;
  user_id?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  ip_address?: string;
  metadata_json: string;
  created_at: string;
}
