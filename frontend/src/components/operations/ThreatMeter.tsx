"use client";

import React from "react";
import { AlertTriangle, ShieldCheck, ShieldAlert } from "lucide-react";

interface ThreatMeterProps {
  threatScore: number;
  activeTracks: number;
  dominantBehavior?: string;
}

export const ThreatMeter: React.FC<ThreatMeterProps> = ({
  threatScore = 0,
  activeTracks = 0,
  dominantBehavior = "Patrol Surveillance",
}) => {
  const clamped = Math.max(0, Math.min(100, threatScore));

  let statusColor = "var(--alert-success)";
  let defconText = "DEFCON 5 // SECURE";
  let statusSubtext = "No anomalous kinematics detected in active sector.";
  let Icon = ShieldCheck;

  if (clamped >= 85) {
    statusColor = "var(--alert-critical)";
    defconText = "DEFCON 1 // BREACH CRITICAL";
    statusSubtext = "Perimeter violation or weapon detected. Sentry response armed.";
    Icon = ShieldAlert;
  } else if (clamped >= 40) {
    statusColor = "var(--primary)";
    defconText = "DEFCON 3 // ELEVATED SUSPICION";
    statusSubtext = "Target loitering or approaching restricted geofence boundary.";
    Icon = AlertTriangle;
  }

  const radius = 75;
  const circumference = Math.PI * radius;
  const strokeDashoffset = circumference - (clamped / 100) * circumference;

  return (
    <div
      className="tactical-card"
      style={{
        padding: "0.85rem",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: clamped >= 85 ? "0 0 16px var(--critical-glow)" : "none",
        borderColor: clamped >= 85 ? "var(--alert-critical)" : "var(--border-color)",
      }}
    >
      <div
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.4rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <Icon size={15} style={{ color: statusColor }} />
          <span
            className="font-display"
            style={{
              fontSize: "0.825rem",
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: "var(--text-main)",
            }}
          >
            REAL-TIME THREAT RADAR
          </span>
        </div>

        <span
          className="tactical-badge font-mono"
          style={{
            backgroundColor: "rgba(34, 38, 42, 0.9)",
            border: `1px solid ${statusColor}`,
            color: statusColor,
          }}
        >
          {clamped}% THREAT
        </span>
      </div>

      {/* Semicircle Radial Gauge */}
      <div style={{ position: "relative", width: "190px", height: "100px", margin: "0.4rem 0" }}>
        <svg width="190" height="100" viewBox="0 0 190 100" style={{ overflow: "visible" }}>
          <path
            d="M 15 90 A 80 80 0 0 1 175 90"
            fill="none"
            stroke="var(--bg-card)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M 15 90 A 80 80 0 0 1 175 90"
            fill="none"
            stroke={statusColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: "stroke-dashoffset 0.4s ease, stroke 0.25s ease" }}
          />
        </svg>

        <div
          style={{
            position: "absolute",
            bottom: "0px",
            left: "0",
            right: "0",
            textAlign: "center",
          }}
        >
          <div
            className="font-mono"
            style={{
              fontSize: "1.85rem",
              fontWeight: 800,
              color: "var(--text-main)",
              lineHeight: 1,
            }}
          >
            {clamped}%
          </div>
          <div
            className="font-display"
            style={{
              fontSize: "0.75rem",
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: statusColor,
              marginTop: "0.15rem",
            }}
          >
            {defconText}
          </div>
        </div>
      </div>

      {/* Target & Kinematics Meta */}
      <div
        style={{
          width: "100%",
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          borderRadius: "2px",
          padding: "0.45rem 0.65rem",
          marginTop: "0.4rem",
          fontSize: "0.725rem",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "0.2rem",
            color: "var(--text-muted)",
          }}
        >
          <span className="font-mono">TRACKS_ACTIVE:</span>
          <span className="font-mono" style={{ color: "var(--text-main)", fontWeight: 700 }}>
            {activeTracks} target{activeTracks !== 1 ? "s" : ""}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            color: "var(--text-muted)",
          }}
        >
          <span className="font-mono">DOMINANT_BEHAVIOR:</span>
          <span style={{ color: "var(--primary)", fontWeight: 700 }}>
            {dominantBehavior}
          </span>
        </div>
      </div>
    </div>
  );
};
