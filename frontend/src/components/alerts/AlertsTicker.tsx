"use client";

import React, { useState } from "react";
import { Alert } from "@/lib/types";
import { AlertTriangle, ShieldAlert, CheckCircle2, Eye } from "lucide-react";

interface AlertsTickerProps {
  alerts: Alert[];
  onAcknowledge: (alert: Alert) => void;
  onInspectAlert?: (alert: Alert) => void;
}

export const AlertsTicker: React.FC<AlertsTickerProps> = ({
  alerts,
  onAcknowledge,
  onInspectAlert,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [filterUnacked, setFilterUnacked] = useState<boolean>(false);

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity !== "ALL" && a.severity !== filterSeverity) return false;
    if (filterUnacked && a.is_acknowledged) return false;
    return true;
  });

  return (
    <div
      className="tactical-card"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        maxHeight: "calc(100vh - 120px)",
      }}
    >
      {/* Ticker Header & Filter Controls */}
      <div
        style={{
          padding: "0.75rem 0.9rem",
          borderBottom: "1px solid var(--border-color)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.5rem",
          backgroundColor: "var(--bg-card)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <AlertTriangle size={16} style={{ color: "var(--primary)" }} />
          <h3 className="font-display" style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.06em" }}>
            PERIMETER INCIDENT STREAM ({filteredAlerts.length})
          </h3>
          <span className="beacon-dot beacon-online" title="Live WebSocket feed armed" />
        </div>

        {/* Filter Badges */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          {["ALL", "CRITICAL", "WARNING"].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilterSeverity(lvl)}
              className="tactical-btn"
              style={{
                background: filterSeverity === lvl ? "var(--primary)" : "var(--bg-surface)",
                color: filterSeverity === lvl ? "#111315" : "var(--text-muted)",
                borderColor: filterSeverity === lvl ? "var(--secondary)" : "var(--border-color)",
                padding: "0.2rem 0.5rem",
                fontSize: "0.675rem",
              }}
            >
              {lvl}
            </button>
          ))}

          <button
            onClick={() => setFilterUnacked(!filterUnacked)}
            className="tactical-btn"
            style={{
              background: filterUnacked ? "var(--alert-critical)" : "var(--bg-surface)",
              color: filterUnacked ? "#ffffff" : "var(--text-muted)",
              borderColor: filterUnacked ? "var(--alert-critical)" : "var(--border-color)",
              padding: "0.2rem 0.5rem",
              fontSize: "0.675rem",
            }}
          >
            UNRESOLVED
          </button>
        </div>
      </div>

      {/* Alert Feed List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "0.65rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
        }}
      >
        {filteredAlerts.length === 0 ? (
          <div
            style={{
              padding: "3rem 1rem",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.8rem",
            }}
          >
            <ShieldAlert size={28} style={{ margin: "0 auto 0.5rem", opacity: 0.4 }} />
            <div className="font-display" style={{ fontSize: "0.85rem", fontWeight: 700 }}>NO ACTIVE SECURITY INCIDENTS</div>
            <div style={{ fontSize: "0.7rem", marginTop: "0.2rem" }}>
              Perimeter sector surveillance is clear. Real-time alerts will stream automatically.
            </div>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const isCrit = alert.severity === "CRITICAL";

            return (
              <div
                key={alert.id}
                style={{
                  backgroundColor: alert.is_acknowledged ? "var(--bg-surface)" : "var(--bg-card)",
                  border: "1px solid",
                  borderColor: alert.is_acknowledged
                    ? "var(--border-color)"
                    : isCrit
                    ? "var(--alert-critical)"
                    : "var(--primary)",
                  borderRadius: "2px",
                  padding: "0.65rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.35rem",
                  boxShadow: !alert.is_acknowledged && isCrit ? "0 0 10px var(--critical-glow)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                {/* Alert Top Line */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                    <span className={`beacon-dot ${isCrit ? "beacon-critical" : "beacon-warning"}`} />
                    <span
                      className={`tactical-badge ${isCrit ? "badge-critical" : "badge-warning"}`}
                    >
                      {alert.alert_type}
                    </span>
                    <span className="font-mono" style={{ fontSize: "0.725rem", color: "var(--primary)", fontWeight: 700 }}>
                      [{alert.camera_id}]
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                    <span className="font-mono" style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
                      {alert.timestamp || alert.created_at?.slice(11, 19) || "NOW"}
                    </span>
                    <span
                      className="tactical-badge font-mono"
                      style={{
                        backgroundColor: "rgba(17, 19, 21, 0.9)",
                        border: "1px solid var(--border-color)",
                        color: isCrit ? "var(--alert-critical)" : "var(--primary)",
                      }}
                    >
                      {alert.threat_score}%
                    </span>
                  </div>
                </div>

                {/* Details & Target Identification */}
                <div className="font-display" style={{ fontSize: "0.85rem", color: "var(--text-main)", fontWeight: 700, letterSpacing: "0.03em" }}>
                  {alert.label || "Unidentified Target"}
                </div>
                {alert.details && (
                  <div style={{ fontSize: "0.725rem", color: "var(--text-muted)", lineHeight: 1.35 }}>
                    {alert.details}
                  </div>
                )}

                {/* Footer Controls */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingTop: "0.3rem",
                    borderTop: "1px solid rgba(52, 56, 59, 0.4)",
                    marginTop: "0.15rem",
                  }}
                >
                  <div className="font-mono" style={{ fontSize: "0.675rem" }}>
                    {alert.is_acknowledged ? (
                      <span style={{ color: "var(--alert-success)", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <CheckCircle2 size={11} /> ACKNOWLEDGED ({alert.acknowledged_by || "SENTRY"})
                      </span>
                    ) : (
                      <span style={{ color: "var(--alert-critical)", fontWeight: 700 }}>
                        ACTION_REQUIRED
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "0.4rem" }}>
                    {onInspectAlert && (
                      <button
                        onClick={() => onInspectAlert(alert)}
                        className="tactical-btn tactical-btn-secondary"
                        style={{ padding: "0.2rem 0.5rem", fontSize: "0.675rem" }}
                      >
                        <Eye size={11} />
                        <span>INSPECT</span>
                      </button>
                    )}

                    {!alert.is_acknowledged && (
                      <button
                        onClick={() => onAcknowledge(alert)}
                        className="tactical-btn tactical-btn-primary"
                        style={{ padding: "0.2rem 0.55rem", fontSize: "0.675rem" }}
                      >
                        <CheckCircle2 size={11} />
                        <span>ACKNOWLEDGE</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
