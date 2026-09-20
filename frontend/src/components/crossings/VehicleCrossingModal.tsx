"use client";

import React, { useState } from "react";
import { VehicleCrossing, Vehicle } from "@/lib/types";
import { getMediaUrl, registerVehicle } from "@/lib/api";
import {
  X,
  Car,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Camera,
  Download,
  Plus,
  CheckCircle2,
  ExternalLink,
  Cpu,
} from "lucide-react";

interface VehicleCrossingModalProps {
  crossing: VehicleCrossing | null;
  isOpen: boolean;
  onClose: () => void;
  onWhitelisted?: (vehicle: Vehicle) => void;
}

export const VehicleCrossingModal: React.FC<VehicleCrossingModalProps> = ({
  crossing,
  isOpen,
  onClose,
  onWhitelisted,
}) => {
  const [isWhitelisting, setIsWhitelisting] = useState(false);
  const [whitelistSuccess, setWhitelistSuccess] = useState(false);
  const [whitelistError, setWhitelistError] = useState<string | null>(null);

  if (!isOpen || !crossing) return null;

  const confPct = Math.round((crossing.ocr_confidence || 0) * 100);
  const isAuth = crossing.is_whitelisted;
  const plateText = crossing.license_plate || "UNREADABLE";

  const handleWhitelistPlate = async () => {
    if (!crossing.license_plate || crossing.license_plate === "UNREADABLE" || crossing.license_plate.startsWith("VEH-")) {
      setWhitelistError("Cannot whitelist generated/unreadable plate identifier.");
      return;
    }
    setIsWhitelisting(true);
    setWhitelistError(null);
    try {
      const registered = await registerVehicle({
        license_plate: crossing.license_plate,
        vehicle_type: crossing.vehicle_type,
        owner_name: "Enrolled from Crossing Inspector",
        department: "Border Control",
        notes: `Auto-enrolled from checkpoint crossing event #${crossing.id}`,
      });
      setWhitelistSuccess(true);
      if (onWhitelisted) onWhitelisted(registered);
      setTimeout(() => setWhitelistSuccess(false), 3500);
    } catch (err: unknown) {
      setWhitelistError(err instanceof Error ? err.message : "Failed to register plate to whitelist.");
    } finally {
      setIsWhitelisting(false);
    }
  };

  const handleDownloadImage = () => {
    if (!crossing.image_path) return;
    const url = getMediaUrl(crossing.image_path);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CROSSING_${crossing.track_id}_${crossing.license_plate || "VEHICLE"}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div
        className="tactical-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "780px", padding: 0 }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "var(--bg-surface)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "3px",
                backgroundColor: isAuth ? "rgba(46, 204, 113, 0.15)" : "rgba(231, 76, 60, 0.15)",
                border: `1px solid ${isAuth ? "var(--alert-success)" : "var(--alert-critical)"}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: isAuth ? "var(--alert-success)" : "var(--alert-critical)",
              }}
            >
              <Car size={18} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span className="font-mono" style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-main)" }}>
                  CROSSING EVENT #{crossing.id}
                </span>
                <span
                  className={`tactical-badge ${isAuth ? "badge-success" : "badge-critical"}`}
                  style={{ fontSize: "0.65rem" }}
                >
                  {isAuth ? "AUTHORIZED VEHICLE" : "UNREGISTERED / THREAT"}
                </span>
              </div>
              <div style={{ fontSize: "0.725rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                Track ID #{crossing.track_id} • {crossing.camera_id || "CAM-SURVEILLANCE"} • {crossing.crossed_at}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "0.3rem",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Main Content Grid: Image + Details */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.4fr 1fr",
              gap: "1.25rem",
            }}
          >
            {/* Left: Snapshot Preview */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "260px",
                  backgroundColor: "#000000",
                  borderRadius: "4px",
                  border: "1px solid var(--border-color)",
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getMediaUrl(crossing.image_path)}
                  alt={`Crossing #${crossing.id}`}
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                  onError={(e) => {
                    e.currentTarget.src = "/placeholder-tactical.png";
                  }}
                />

                {/* Overlaid Plate Badge */}
                <div
                  style={{
                    position: "absolute",
                    bottom: "10px",
                    left: "10px",
                    backgroundColor: "rgba(17, 19, 21, 0.92)",
                    border: `1px solid ${isAuth ? "var(--alert-success)" : "var(--alert-critical)"}`,
                    padding: "0.25rem 0.6rem",
                    borderRadius: "3px",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <span
                    className="font-mono"
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 800,
                      color: isAuth ? "var(--alert-success)" : "var(--alert-critical)",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {plateText}
                  </span>
                  <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    {confPct}%
                  </span>
                </div>
              </div>

              {/* Snapshot path info */}
              <div
                className="font-mono"
                style={{
                  fontSize: "0.675rem",
                  color: "var(--text-muted)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                PATH: {crossing.image_path || "N/A"}
              </div>
            </div>

            {/* Right: Forensic Dossier Breakdown */}
            <div
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "0.75rem",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div
                  className="section-id"
                  style={{ fontSize: "0.675rem", color: "var(--primary)", fontWeight: 700 }}
                >
                  [ANPR_TELEMETRY // RECORD #{crossing.id}]
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.78rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>CLASSIFICATION:</span>
                    <span className="font-mono" style={{ fontWeight: 700, textTransform: "uppercase" }}>
                      {crossing.vehicle_type}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>CROSSING TYPE:</span>
                    <span style={{ fontWeight: 600, color: "var(--text-main)" }}>
                      {crossing.crossing_type}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>OCR CONFIDENCE:</span>
                    <span
                      className="font-mono"
                      style={{
                        fontWeight: 700,
                        color: confPct >= 70 ? "var(--alert-success)" : confPct >= 40 ? "var(--primary)" : "var(--alert-critical)",
                      }}
                    >
                      {confPct}%
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>TRACK ID:</span>
                    <span className="font-mono" style={{ fontWeight: 700 }}>
                      #{crossing.track_id}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>SENSOR CHANNEL:</span>
                    <span className="font-mono" style={{ fontWeight: 700 }}>
                      {crossing.camera_id || "CAM-01"}
                    </span>
                  </div>

                  {crossing.details && (
                    <div style={{ marginTop: "0.25rem", borderTop: "1px solid var(--border-color)", paddingTop: "0.5rem" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.7rem", display: "block", marginBottom: "0.2rem" }}>
                        INCIDENT DETAILS:
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-main)" }}>
                        {crossing.details}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Status Alert or Success Box */}
              {whitelistSuccess && (
                <div
                  style={{
                    backgroundColor: "rgba(46, 204, 113, 0.15)",
                    border: "1px solid var(--alert-success)",
                    borderRadius: "3px",
                    padding: "0.5rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    color: "var(--alert-success)",
                    fontSize: "0.75rem",
                  }}
                >
                  <CheckCircle2 size={14} />
                  <span>Plate {plateText} added to whitelist!</span>
                </div>
              )}

              {whitelistError && (
                <div
                  style={{
                    backgroundColor: "rgba(231, 76, 60, 0.15)",
                    border: "1px solid var(--alert-critical)",
                    borderRadius: "3px",
                    padding: "0.5rem",
                    color: "var(--alert-critical)",
                    fontSize: "0.75rem",
                  }}
                >
                  {whitelistError}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                {!isAuth && (
                  <button
                    onClick={handleWhitelistPlate}
                    disabled={isWhitelisting || whitelistSuccess}
                    className="tactical-btn font-mono"
                    style={{
                      backgroundColor: "rgba(46, 204, 113, 0.15)",
                      borderColor: "var(--alert-success)",
                      color: "var(--alert-success)",
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.75rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "0.4rem",
                      cursor: "pointer",
                    }}
                  >
                    <Plus size={14} />
                    {isWhitelisting ? "ENROLLING PLATE..." : `AUTHORIZE PLATE [${plateText}]`}
                  </button>
                )}

                <button
                  onClick={handleDownloadImage}
                  className="tactical-btn font-mono"
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    borderColor: "var(--border-color)",
                    color: "var(--text-main)",
                    padding: "0.5rem 0.75rem",
                    fontSize: "0.75rem",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "0.4rem",
                    cursor: "pointer",
                  }}
                >
                  <Download size={14} />
                  EXPORT EVIDENCE SNAPSHOT
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
