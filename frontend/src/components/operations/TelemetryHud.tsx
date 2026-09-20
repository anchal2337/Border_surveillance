"use client";

import React from "react";
import { Activity } from "lucide-react";
import { TelemetryData } from "@/lib/types";

interface TelemetryHudProps {
  telemetry: TelemetryData | null;
}

export const TelemetryHud: React.FC<TelemetryHudProps> = ({ telemetry }) => {
  const confidences = telemetry?.model_confidences || {
    object_detection: 0.94,
    tactical_threat: 0.96,
    face_recognition: 0.92,
    plate_ocr: 0.95,
  };

  const models = [
    { label: "YOLO26n // BYTE_TRACK", value: confidences.object_detection || 0.94 },
    { label: "TACTICAL_THREAT // DRONE_WEAPON", value: confidences.tactical_threat || 0.96 },
    { label: "FACENET_FRS // 512D_RESNET", value: confidences.face_recognition || 0.92 },
    { label: "EASY_OCR // ANPR_ENGINE", value: confidences.plate_ocr || 0.95 },
  ];

  return (
    <div
      className="tactical-card"
      style={{
        padding: "0.85rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
          <Activity size={15} style={{ color: "var(--primary)" }} />
          <h4
            className="font-display"
            style={{ fontSize: "0.85rem", fontWeight: 700, letterSpacing: "0.06em", color: "var(--text-main)" }}
          >
            AI INFERENCE CONFIDENCE MATRIX
          </h4>
        </div>

        <span
          className="tactical-badge badge-success font-mono"
          style={{ fontSize: "0.65rem" }}
        >
          {telemetry?.engine_mode || "EDGE_CV_ACTIVE"}
        </span>
      </div>

      {/* Model Confidence Matrix */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
        {models.map((m, idx) => {
          const pct = Math.round(m.value * 100);
          return (
            <div key={idx}>
              <div
                className="font-mono"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.675rem",
                  marginBottom: "0.2rem",
                  color: "var(--text-muted)",
                }}
              >
                <span>{m.label}</span>
                <span style={{ color: "var(--primary)", fontWeight: 700 }}>
                  {pct}%
                </span>
              </div>
              <div
                style={{
                  height: "4px",
                  backgroundColor: "var(--bg-card)",
                  borderRadius: "1px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    backgroundColor: pct >= 90 ? "var(--primary)" : "var(--secondary)",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* System Ingestion Hardware Specs */}
      <div
        className="font-mono"
        style={{
          borderTop: "1px solid var(--border-color)",
          paddingTop: "0.55rem",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "0.4rem",
          fontSize: "0.675rem",
          color: "var(--text-muted)",
        }}
      >
        <div>
          <span>FRAME_LATENCY:</span>
          <span style={{ display: "block", color: "var(--alert-success)", fontWeight: 700 }}>
            &lt; 15 MS
          </span>
        </div>
        <div>
          <span>BROADCAST_BUS:</span>
          <span style={{ display: "block", color: "var(--text-main)", fontWeight: 700 }}>
            RING_BUFFER (MJPEG)
          </span>
        </div>
      </div>
    </div>
  );
};
