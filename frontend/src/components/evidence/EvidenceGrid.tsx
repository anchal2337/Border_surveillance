"use client";

import React, { useState } from "react";
import { EvidenceItem } from "@/lib/types";
import { getMediaUrl } from "@/lib/api";
import { FolderLock, Hash } from "lucide-react";

interface EvidenceGridProps {
  evidence: EvidenceItem[];
  onSelectCase: (item: EvidenceItem) => void;
}

export const EvidenceGrid: React.FC<EvidenceGridProps> = ({ evidence, onSelectCase }) => {
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  const filtered = evidence.filter((item) => {
    if (filterStatus !== "ALL" && item.status !== filterStatus) return false;
    return true;
  });

  return (
    <div
      className="tactical-card"
      style={{
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      {/* Header & Status Filter */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <FolderLock size={18} style={{ color: "var(--primary)" }} />
          <div>
            <h3 className="font-display" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}>
              FORENSIC EVIDENCE LOCKER ({filtered.length} INCIDENT DOSSIERS)
            </h3>
            <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
              Court-admissible tamper-evident media with cryptographic SHA-256 checksums.
            </div>
          </div>
        </div>

        {/* Status Filters */}
        <div style={{ display: "flex", gap: "0.3rem" }}>
          {["ALL", "NEW", "INVESTIGATING", "RESOLVED"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className="tactical-btn"
              style={{
                background: filterStatus === st ? "var(--primary)" : "var(--bg-card)",
                color: filterStatus === st ? "#111315" : "var(--text-muted)",
                borderColor: filterStatus === st ? "var(--secondary)" : "var(--border-color)",
                padding: "0.25rem 0.55rem",
                fontSize: "0.7rem",
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Evidence Dossiers */}
      {filtered.length === 0 ? (
        <div
          style={{
            padding: "3rem 1rem",
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "0.85rem",
          }}
        >
          <FolderLock size={32} style={{ margin: "0 auto 0.5rem", opacity: 0.4 }} />
          <div className="font-display" style={{ fontSize: "0.9rem", fontWeight: 700 }}>NO EVIDENCE DOSSIERS FOUND</div>
          <div style={{ fontSize: "0.725rem", marginTop: "0.2rem" }}>
            Forensic snapshots will appear automatically when perimeter intrusions occur.
          </div>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "0.75rem",
          }}
        >
          {filtered.map((item) => {
            const isCrit = item.severity === "CRITICAL";

            return (
              <div
                key={item.id}
                onClick={() => onSelectCase(item)}
                style={{
                  backgroundColor: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "2px",
                  overflow: "hidden",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--primary)";
                  e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-color)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                {/* Thumbnail Preview */}
                <div
                  style={{
                    position: "relative",
                    width: "100%",
                    height: "150px",
                    backgroundColor: "#000000",
                    overflow: "hidden",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={getMediaUrl(item.crop_image || item.scene_image)}
                    alt={item.id}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                    onError={(e) => {
                      e.currentTarget.src = "/placeholder-tactical.png";
                    }}
                  />

                  {/* Threat Badge Overlay */}
                  <div
                    className="font-mono"
                    style={{
                      position: "absolute",
                      top: "6px",
                      right: "6px",
                      backgroundColor: "rgba(17, 19, 21, 0.9)",
                      border: `1px solid ${isCrit ? "var(--alert-critical)" : "var(--primary)"}`,
                      padding: "0.15rem 0.4rem",
                      borderRadius: "2px",
                      fontSize: "0.65rem",
                      fontWeight: 800,
                      color: isCrit ? "var(--alert-critical)" : "var(--primary)",
                    }}
                  >
                    {item.threat_score}% THREAT
                  </div>

                  <div
                    className="font-mono"
                    style={{
                      position: "absolute",
                      bottom: "6px",
                      left: "6px",
                      backgroundColor: "rgba(17, 19, 21, 0.9)",
                      border: "1px solid var(--border-color)",
                      padding: "0.15rem 0.4rem",
                      borderRadius: "2px",
                      fontSize: "0.65rem",
                      color: "var(--text-main)",
                    }}
                  >
                    {item.id}
                  </div>
                </div>

                {/* Dossier Meta */}
                <div style={{ padding: "0.65rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span className="font-display" style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-main)" }}>
                      {item.event}
                    </span>
                    <span
                      className="tactical-badge font-mono"
                      style={{
                        fontSize: "0.625rem",
                        backgroundColor:
                          item.status === "RESOLVED"
                            ? "rgba(114, 168, 121, 0.12)"
                            : item.status === "INVESTIGATING"
                            ? "rgba(214, 168, 79, 0.12)"
                            : "rgba(146, 151, 155, 0.1)",
                        color:
                          item.status === "RESOLVED"
                            ? "var(--alert-success)"
                            : item.status === "INVESTIGATING"
                            ? "var(--primary)"
                            : "var(--text-muted)",
                        border: "1px solid var(--border-color)",
                      }}
                    >
                      {item.status}
                    </span>
                  </div>

                  <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
                    Target: <span style={{ color: "var(--text-main)", fontWeight: 600 }}>{item.identity || item.object_label}</span> • Track #{item.track_id}
                  </div>

                  <div
                    className="font-mono"
                    style={{
                      fontSize: "0.65rem",
                      color: "var(--secondary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      marginTop: "0.15rem",
                    }}
                  >
                    <Hash size={11} />
                    <span>{item.sha256_hash?.slice(0, 22) || "sha256:pending..."}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
