"use client";

import React from "react";
import { Camera } from "@/lib/types";
import { Video, PlusCircle } from "lucide-react";

interface CameraSelectorProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (cam: Camera) => void;
  onOpenInjectModal?: () => void;
}

export const CameraSelector: React.FC<CameraSelectorProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onOpenInjectModal,
}) => {
  return (
    <div
      className="tactical-card"
      style={{
        padding: "0.85rem",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.65rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Video size={15} style={{ color: "var(--primary)" }} />
          <h4
            className="font-display"
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              letterSpacing: "0.06em",
              color: "var(--text-main)",
            }}
          >
            TACTICAL SENSOR ARRAY ({cameras.length} CHANNELS)
          </h4>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {onOpenInjectModal && (
            <button
              onClick={onOpenInjectModal}
              className="tactical-btn tactical-btn-primary"
              style={{ padding: "0.25rem 0.55rem", fontSize: "0.725rem" }}
            >
              <PlusCircle size={12} />
              <span>INJECT VIDEO SOURCE</span>
            </button>
          )}
          <span className="font-mono section-id">[INGEST_BUS // ACTIVE]</span>
        </div>
      </div>

      {/* Grid of Camera Tiles */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: "0.55rem",
        }}
      >
        {cameras.map((cam) => {
          const isSelected = cam.id === selectedCameraId;
          const isOnline = cam.status === "ONLINE";

          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera(cam)}
              style={{
                backgroundColor: isSelected ? "rgba(214, 168, 79, 0.09)" : "var(--bg-card)",
                border: "1px solid",
                borderColor: isSelected ? "var(--primary)" : "var(--border-color)",
                borderRadius: "2px",
                padding: "0.6rem",
                cursor: "pointer",
                transition: "all 0.15s ease",
                position: "relative",
              }}
            >
              {/* Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "0.25rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                  <span
                    className={`beacon-dot ${isOnline ? "beacon-online" : "beacon-standby"}`}
                  />
                  <span
                    className="font-mono"
                    style={{
                      fontSize: "0.8rem",
                      fontWeight: 800,
                      color: isSelected ? "var(--primary)" : "var(--text-main)",
                    }}
                  >
                    [{cam.id}]
                  </span>
                </div>

                <span
                  className="tactical-badge"
                  style={{
                    fontSize: "0.625rem",
                    backgroundColor: "rgba(17, 19, 21, 0.9)",
                    border: "1px solid var(--border-color)",
                    color: "var(--text-muted)",
                  }}
                >
                  {cam.source_type}
                </span>
              </div>

              {/* Camera Name & Sector */}
              <div
                className="font-display"
                style={{
                  fontSize: "0.825rem",
                  fontWeight: 700,
                  color: "var(--text-main)",
                  marginBottom: "0.15rem",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  letterSpacing: "0.03em",
                }}
              >
                {cam.name}
              </div>

              <div
                className="font-mono"
                style={{
                  fontSize: "0.675rem",
                  color: "var(--text-muted)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>{cam.sector_zone}</span>
                <span>{cam.resolution}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
