"use client";

import React, { useState } from "react";
import { Alert } from "@/lib/types";
import { X, CheckCircle2, AlertTriangle } from "lucide-react";

interface AlertAckModalProps {
  alert: Alert | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmitAck: (alertId: string, notes: string) => Promise<void>;
}

export const AlertAckModal: React.FC<AlertAckModalProps> = ({
  alert,
  isOpen,
  onClose,
  onSubmitAck,
}) => {
  const [notes, setNotes] = useState("Target verified by visual sentry check. Sector secure.");
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !alert) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmitAck(alert.id, notes);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div className="tactical-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "520px" }}>
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <AlertTriangle size={18} style={{ color: "var(--primary)" }} />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.04em" }}>
              ACKNOWLEDGE PERIMETER INCIDENT
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "4px",
              padding: "0.75rem",
              fontSize: "0.8rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Incident ID:</span>
              <span className="font-mono" style={{ color: "var(--text-main)", fontWeight: 700 }}>
                {alert.id}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Type:</span>
              <span style={{ color: "var(--primary)", fontWeight: 700 }}>
                {alert.alert_type}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Threat Score:</span>
              <span style={{ color: alert.threat_score >= 85 ? "var(--alert-critical)" : "var(--primary)", fontWeight: 700 }}>
                {alert.threat_score}%
              </span>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              RESOLUTION & CHAIN-OF-CUSTODY NOTES
            </label>
            <textarea
              required
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="tactical-input"
              style={{ resize: "vertical", fontFamily: "inherit" }}
              placeholder="Detail response actions taken (e.g. sentry dispatched, authorized convoy)..."
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
            <button type="button" onClick={onClose} className="tactical-btn tactical-btn-secondary">
              CANCEL
            </button>
            <button type="submit" disabled={submitting} className="tactical-btn tactical-btn-primary">
              <CheckCircle2 size={14} />
              <span>{submitting ? "RECORDING..." : "CONFIRM ACKNOWLEDGMENT"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
