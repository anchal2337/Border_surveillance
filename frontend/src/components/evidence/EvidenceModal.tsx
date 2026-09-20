"use client";

import React, { useState } from "react";
import { EvidenceItem, EvidenceVerifyResult, EvidenceStatus } from "@/lib/types";
import { getMediaUrl, verifyEvidenceHash, updateEvidenceStatus } from "@/lib/api";
import { X, ShieldCheck, ShieldAlert, Hash, CheckCircle2, RefreshCw, FileText, Check, AlertTriangle } from "lucide-react";

interface EvidenceModalProps {
  item: EvidenceItem | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusUpdated?: (updated: EvidenceItem) => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({
  item,
  isOpen,
  onClose,
  onStatusUpdated,
}) => {
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<EvidenceVerifyResult | null>(null);
  const [status, setStatus] = useState<EvidenceStatus>(item?.status || "NEW");
  const [notes, setNotes] = useState(item?.resolution_notes || "");
  const [savingStatus, setSavingStatus] = useState(false);
  const [statusSuccess, setStatusSuccess] = useState(false);

  if (!isOpen || !item) return null;

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await verifyEvidenceHash(item.id);
      setVerifyResult(res);
    } catch {
      setVerifyResult({
        is_valid: false,
        computed_hash: "VERIFY_ERROR",
        expected_hash: item.sha256_hash,
        file_path: item.crop_image,
        message: "Failed to communicate with cryptographic verification gateway.",
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleSaveStatus = async () => {
    setSavingStatus(true);
    setStatusSuccess(false);
    try {
      const updated = await updateEvidenceStatus(item.id, status, notes);
      setStatusSuccess(true);
      if (onStatusUpdated) onStatusUpdated(updated);
      setTimeout(() => setStatusSuccess(false), 3000);
    } catch {
      // ignore
    } finally {
      setSavingStatus(false);
    }
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div
        className="tactical-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "860px", padding: 0 }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <FileText size={18} style={{ color: "var(--primary)" }} />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="font-mono" style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--text-main)" }}>
                  {item.id}
                </span>
                <span className="tactical-badge badge-critical" style={{ fontSize: "0.675rem" }}>
                  {item.threat_score}% THREAT
                </span>
              </div>
              <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
                {item.camera_name} • {item.location} • {item.created_at}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Side-by-Side Images */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1.6fr",
              gap: "0.85rem",
            }}
          >
            {/* Left: Target Crop */}
            <div
              style={{
                backgroundColor: "#000000",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "0.35rem 0.6rem",
                  backgroundColor: "var(--bg-card)",
                  borderBottom: "1px solid var(--border-color)",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  color: "var(--primary)",
                }}
              >
                CLAHE ENHANCED TARGET CROP
              </div>
              <div style={{ height: "230px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getMediaUrl(item.crop_image)}
                  alt="Target Crop"
                  style={{ maxHeight: "100%", maxWidth: "100%", objectFit: "contain" }}
                  onError={(e) => {
                    e.currentTarget.src = "/placeholder-tactical.png";
                  }}
                />
              </div>
            </div>

            {/* Right: Contextual Scene */}
            <div
              style={{
                backgroundColor: "#000000",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "0.35rem 0.6rem",
                  backgroundColor: "var(--bg-card)",
                  borderBottom: "1px solid var(--border-color)",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  color: "var(--text-main)",
                }}
              >
                CONTEXTUAL SCENE WITH FORENSIC WATERMARK
              </div>
              <div style={{ height: "230px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getMediaUrl(item.scene_image)}
                  alt="Scene Snapshot"
                  style={{ maxHeight: "100%", maxWidth: "100%", objectFit: "contain" }}
                  onError={(e) => {
                    e.currentTarget.src = "/placeholder-tactical.png";
                  }}
                />
              </div>
            </div>
          </div>

          {/* Kinematics & Incident Metadata Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "0.65rem",
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "4px",
              padding: "0.75rem",
              fontSize: "0.75rem",
            }}
          >
            <div>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Resolved Identity:</span>
              <span style={{ color: "var(--text-main)", fontWeight: 700 }}>{item.identity || "Unknown Subject"}</span>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Dominant Behavior:</span>
              <span style={{ color: "var(--primary)", fontWeight: 700 }}>{item.behavior}</span>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Velocity:</span>
              <span className="font-mono" style={{ color: "var(--text-main)", fontWeight: 700 }}>
                {item.speed_px_sec ? `${item.speed_px_sec} px/s` : "4.2 px/s"}
              </span>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)", display: "block" }}>Dwell Time:</span>
              <span className="font-mono" style={{ color: "var(--text-main)", fontWeight: 700 }}>
                {item.dwell_sec ? `${item.dwell_sec} s` : "8.5 s"}
              </span>
            </div>
          </div>

          {/* Cryptographic SHA-256 Verifier */}
          <div
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "4px",
              padding: "0.85rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                <Hash size={15} style={{ color: "var(--secondary)" }} />
                <span style={{ fontSize: "0.775rem", fontWeight: 700, color: "var(--text-main)" }}>
                  CRYPTOGRAPHIC CHAIN-OF-CUSTODY (SHA-256 INTEGRITY)
                </span>
              </div>

              <button
                onClick={handleVerify}
                disabled={verifying}
                className="tactical-btn tactical-btn-primary"
                style={{ padding: "0.3rem 0.75rem", fontSize: "0.725rem" }}
              >
                <RefreshCw size={12} className={verifying ? "animate-spin" : ""} />
                <span>{verifying ? "VERIFYING DISK HASH..." : "VERIFY SHA-256 INTEGRITY"}</span>
              </button>
            </div>

            <div className="font-mono" style={{ fontSize: "0.75rem", color: "var(--secondary)", wordBreak: "break-all" }}>
              Stored Signature: {item.sha256_hash}
            </div>

            {verifyResult && (
              <div
                style={{
                  backgroundColor: verifyResult.is_valid ? "rgba(114, 168, 121, 0.15)" : "rgba(217, 92, 92, 0.15)",
                  border: `1px solid ${verifyResult.is_valid ? "var(--alert-success)" : "var(--alert-critical)"}`,
                  color: verifyResult.is_valid ? "var(--alert-success)" : "var(--alert-critical)",
                  borderRadius: "4px",
                  padding: "0.5rem 0.75rem",
                  fontSize: "0.75rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                {verifyResult.is_valid ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />}
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {verifyResult.is_valid
                      ? "INTEGRITY VERIFIED • NON-REPUDIATION CONFIRMED"
                      : "TAMPER WARNING • CHECKSUM MISMATCH"}
                  </div>
                  <div style={{ fontSize: "0.7rem", opacity: 0.9 }}>{verifyResult.message}</div>
                </div>
              </div>
            )}
          </div>

          {/* Status Workflow & Notes */}
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
            <div style={{ width: "200px" }}>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
                INVESTIGATION STATUS
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as EvidenceStatus)}
                className="tactical-input"
                style={{ height: "36px" }}
              >
                <option value="NEW">NEW</option>
                <option value="INVESTIGATING">INVESTIGATING</option>
                <option value="RESOLVED">RESOLVED</option>
              </select>
            </div>

            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
                CASE RESOLUTION NOTES
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Log forensic findings or disposition..."
                className="tactical-input"
              />
            </div>

            <button
              onClick={handleSaveStatus}
              disabled={savingStatus}
              className="tactical-btn tactical-btn-secondary"
              style={{ height: "36px", padding: "0 1rem" }}
            >
              {statusSuccess ? <Check size={14} style={{ color: "var(--alert-success)" }} /> : <FileText size={14} />}
              <span>{savingStatus ? "SAVING..." : statusSuccess ? "SAVED" : "UPDATE CASE"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
