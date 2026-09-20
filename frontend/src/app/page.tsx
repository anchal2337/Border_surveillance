"use client";

import React, { useState, useEffect, useCallback } from "react";
import { SentryNavbar } from "@/components/layout/SentryNavbar";
import { SentrySidebar, NavTab } from "@/components/layout/SentrySidebar";
import { AuthModal } from "@/components/layout/AuthModal";

import { LiveVideoPlayer } from "@/components/operations/LiveVideoPlayer";
import { CameraSelector } from "@/components/operations/CameraSelector";
import { ThreatMeter } from "@/components/operations/ThreatMeter";
import { TelemetryHud } from "@/components/operations/TelemetryHud";
import { InjectVideoModal } from "@/components/operations/InjectVideoModal";

import { ZoneCalibratorCanvas } from "@/components/zones/ZoneCalibratorCanvas";
import { AlertsTicker } from "@/components/alerts/AlertsTicker";
import { AlertAckModal } from "@/components/alerts/AlertAckModal";

import { EvidenceGrid } from "@/components/evidence/EvidenceGrid";
import { EvidenceModal } from "@/components/evidence/EvidenceModal";

import { PersonnelRegistry } from "@/components/whitelist/PersonnelRegistry";
import { FaceEnrollModal } from "@/components/whitelist/FaceEnrollModal";
import { VehicleRegistry } from "@/components/whitelist/VehicleRegistry";
import { VehicleCrossingsLog } from "@/components/whitelist/VehicleCrossingsLog";

import { StorageHealthCard } from "@/components/system/StorageHealthCard";
import { AuditTrailTable } from "@/components/system/AuditTrailTable";

import {
  Camera,
  Alert,
  EvidenceItem,
  Personnel,
  Vehicle,
  VehicleCrossing,
  TelemetryData,
  StorageHealth,
  AuditLogItem,
} from "@/lib/types";

import {
  getCameras,
  getAlerts,
  acknowledgeAlert,
  getEvidence,
  getPersonnel,
  deletePersonnel,
  getVehicles,
  registerVehicle,
  deleteVehicle,
  getCrossings,
  getStorageHealth,
  getAuditLogs,
  updateCameraZones,
} from "@/lib/api";

import { sentrySocket } from "@/lib/socket";

export default function SentryCommandConsole() {
  // Navigation & Modals
  const [activeTab, setActiveTab] = useState<NavTab>("operations");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [ackAlert, setAckAlert] = useState<Alert | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [enrollModalOpen, setEnrollModalOpen] = useState(false);
  const [injectModalOpen, setInjectModalOpen] = useState(false);

  // Core Data
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [crossings, setCrossings] = useState<VehicleCrossing[]>([]);
  const [storageHealth, setStorageHealth] = useState<StorageHealth | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);

  // Initial Data Fetch
  const loadData = useCallback(async () => {
    try {
      const [cams, alts, evs, pers, vehs, cross, health, logs] = await Promise.all([
        getCameras().catch(() => []),
        getAlerts(50).catch(() => []),
        getEvidence(50).catch(() => []),
        getPersonnel().catch(() => []),
        getVehicles().catch(() => []),
        getCrossings(50).catch(() => []),
        getStorageHealth().catch(() => null),
        getAuditLogs(50).catch(() => []),
      ]);

      setCameras(cams);
      if (cams.length > 0 && !selectedCamera) {
        // Default to CAM-04 (BOP-04 North Road) or first
        const cam04 = cams.find((c) => c.id === "CAM-04") || cams[0];
        setSelectedCamera(cam04);
      }

      setAlerts(alts);
      setEvidence(evs);
      setPersonnel(pers);
      setVehicles(vehs);
      setCrossings(cross);
      setStorageHealth(health);
      setAuditLogs(logs);
    } catch {
      // ignore
    }
  }, [selectedCamera]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // WebSocket Live Real-Time Subscriptions
  useEffect(() => {
    // 1. Initial alerts buffer from WebSocket
    const unsubInit = sentrySocket.onInitialBuffer((bufferedAlerts) => {
      setAlerts((prev) => {
        const ids = new Set(prev.map((a) => a.id));
        const newOnes = bufferedAlerts.filter((a) => !ids.has(a.id));
        return [...newOnes, ...prev];
      });
    });

    // 2. Incoming real-time alerts
    const unsubAlert = sentrySocket.onAlert((newAlert) => {
      setAlerts((prev) => [newAlert, ...prev.filter((a) => a.id !== newAlert.id)]);
      // Refresh evidence if alert had evidence
      getEvidence(50).then(setEvidence).catch(() => {});
    });

    // 3. Live stream telemetry (FPS, Threat score, Active tracks)
    const unsubTelem = sentrySocket.onTelemetry((telemData) => {
      setTelemetry(telemData);
    });

    return () => {
      unsubInit();
      unsubAlert();
      unsubTelem();
    };
  }, []);

  // Handlers
  const handleAcknowledgeAlert = async (alertId: string, notes: string) => {
    try {
      const updated = await acknowledgeAlert(alertId, notes);
      setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    } catch {
      // ignore
    }
  };

  const handleDeployZones = async (geofence: number[][], tripwire: number[][]) => {
    if (!selectedCamera) return;
    await updateCameraZones(selectedCamera.id, geofence, tripwire);
  };

  const handleDeletePersonnel = async (id: string) => {
    await deletePersonnel(id);
    setPersonnel((prev) => prev.filter((p) => p.id !== id));
  };

  const handleRegisterVehicle = async (payload: {
    license_plate: string;
    vehicle_type?: string;
    owner_name?: string;
    department?: string;
  }) => {
    const v = await registerVehicle(payload);
    setVehicles((prev) => [v, ...prev]);
  };

  const handleDeleteVehicle = async (id: string) => {
    await deleteVehicle(id);
    setVehicles((prev) => prev.filter((v) => v.id !== id));
  };

  const handleCameraInjected = (newCam: Camera) => {
    setCameras((prev) => {
      const exists = prev.some((c) => c.id === newCam.id);
      return exists ? prev.map((c) => (c.id === newCam.id ? newCam : c)) : [newCam, ...prev];
    });
    setSelectedCamera(newCam);
  };

  const unreadAlertCount = alerts.filter((a) => !a.is_acknowledged).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", backgroundColor: "var(--bg-base)" }}>
      {/* Top Tactical Sentry Navbar */}
      <SentryNavbar onOpenAuth={() => setAuthModalOpen(true)} unreadAlertCount={unreadAlertCount} />

      {/* Main Console Grid */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sentry Module Sidebar */}
        <SentrySidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          unreadAlertCount={unreadAlertCount}
        />

        {/* Content Area */}
        <main style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
          {/* 1. LIVE OPERATIONS WALL */}
          {activeTab === "operations" && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1.8fr 1fr",
                gap: "1rem",
                height: "100%",
              }}
            >
              {/* Left: Video Player & Camera Grid */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <LiveVideoPlayer
                  camera={selectedCamera}
                  fps={telemetry?.fps || selectedCamera?.fps || 30.0}
                  activeTracks={telemetry?.active_tracks || 0}
                  maxThreat={telemetry?.max_threat || 0}
                />
                <CameraSelector
                  cameras={cameras}
                  selectedCameraId={selectedCamera?.id || null}
                  onSelectCamera={setSelectedCamera}
                  onOpenInjectModal={() => setInjectModalOpen(true)}
                />
              </div>

              {/* Right: Threat Meter, Telemetry HUD & Incident Stream */}
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <ThreatMeter
                  threatScore={telemetry?.max_threat || 0}
                  activeTracks={telemetry?.active_tracks || 0}
                  dominantBehavior={telemetry?.max_threat && telemetry.max_threat >= 85 ? "Perimeter Breach" : "Normal Patrol"}
                />

                <TelemetryHud telemetry={telemetry} />

                <div style={{ flex: 1, minHeight: "340px" }}>
                  <AlertsTicker
                    alerts={alerts.slice(0, 15)}
                    onAcknowledge={(a) => setAckAlert(a)}
                    onInspectAlert={(a) => {
                      const ev = evidence.find((e) => e.id.includes(a.id) || e.track_id.toString() === a.label.replace(/\D/g, ""));
                      if (ev) setSelectedEvidence(ev);
                      else setActiveTab("alerts");
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* 2. ZONE STUDIO */}
          {activeTab === "zones" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ maxWidth: "340px" }}>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  SELECT SENSOR CHANNEL TO CALIBRATE
                </label>
                <select
                  value={selectedCamera?.id || ""}
                  onChange={(e) => {
                    const cam = cameras.find((c) => c.id === e.target.value);
                    if (cam) setSelectedCamera(cam);
                  }}
                  className="tactical-input font-mono"
                >
                  {cameras.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.id} - {c.name} ({c.sector_zone})
                    </option>
                  ))}
                </select>
              </div>

              <ZoneCalibratorCanvas
                camera={selectedCamera}
                onDeployZones={handleDeployZones}
              />
            </div>
          )}

          {/* 3. REAL-TIME ALERTS */}
          {activeTab === "alerts" && (
            <div style={{ height: "100%" }}>
              <AlertsTicker
                alerts={alerts}
                onAcknowledge={(a) => setAckAlert(a)}
                onInspectAlert={(a) => {
                  const ev = evidence.find((e) => e.id.includes(a.id));
                  if (ev) setSelectedEvidence(ev);
                }}
              />
            </div>
          )}

          {/* 4. EVIDENCE LOCKER */}
          {activeTab === "evidence" && (
            <EvidenceGrid
              evidence={evidence}
              onSelectCase={(item) => setSelectedEvidence(item)}
            />
          )}

          {/* 5. WHITELIST REGISTRY */}
          {activeTab === "whitelist" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <PersonnelRegistry
                personnel={personnel}
                onOpenEnroll={() => setEnrollModalOpen(true)}
                onDeletePersonnel={handleDeletePersonnel}
              />

              <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "1.25rem" }}>
                <VehicleRegistry
                  vehicles={vehicles}
                  onRegisterVehicle={handleRegisterVehicle}
                  onDeleteVehicle={handleDeleteVehicle}
                />
                <VehicleCrossingsLog crossings={crossings} />
              </div>
            </div>
          )}

          {/* 6. STATION HEALTH & AUDIT */}
          {activeTab === "system" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <StorageHealthCard health={storageHealth} onRefresh={() => getStorageHealth().then(setStorageHealth)} />
              <AuditTrailTable logs={auditLogs} />
            </div>
          )}
        </main>
      </div>

      {/* Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={() => loadData()}
      />

      <InjectVideoModal
        isOpen={injectModalOpen}
        onClose={() => setInjectModalOpen(false)}
        onCameraInjected={handleCameraInjected}
      />

      <AlertAckModal
        alert={ackAlert}
        isOpen={!!ackAlert}
        onClose={() => setAckAlert(null)}
        onSubmitAck={handleAcknowledgeAlert}
      />

      <EvidenceModal
        item={selectedEvidence}
        isOpen={!!selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
        onStatusUpdated={(updated) => {
          setEvidence((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        }}
      />

      <FaceEnrollModal
        isOpen={enrollModalOpen}
        onClose={() => setEnrollModalOpen(false)}
        onEnrolled={(newPerson) => setPersonnel((prev) => [newPerson, ...prev])}
      />
    </div>
  );
}
