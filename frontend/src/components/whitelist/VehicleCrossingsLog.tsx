"use client";

import React from "react";
import { VehicleCrossing } from "@/lib/types";
import { getMediaUrl } from "@/lib/api";
import { ShieldCheck, ShieldAlert, Clock, Camera } from "lucide-react";

interface VehicleCrossingsLogProps {
  crossings: VehicleCrossing[];
}

export const VehicleCrossingsLog: React.FC<VehicleCrossingsLogProps> = ({ crossings }) => {
  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-color)",
        borderRadius: "6px",
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.85rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h3 style={{ fontSize: "0.9rem", fontWeight: 800, color: "var(--text-main)", letterSpacing: "0.04em" }}>
          ANPR CHECKPOINT CROSSINGS LOG ({crossings.length} EVENTS)
        </h3>
        <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
          OCR THRESHOLD: 35.0%
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.775rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)" }}>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>TIMESTAMP</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>SNAPSHOT</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>DETECTED PLATE</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>OCR CONFIDENCE</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>TYPE</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {crossings.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  No vehicle crossings recorded in the active session.
                </td>
              </tr>
            ) : (
              crossings.map((c) => {
                const confPct = Math.round(c.ocr_confidence * 100);
                return (
                  <tr
                    key={c.id}
                    style={{
                      borderBottom: "1px solid rgba(52, 56, 59, 0.4)",
                      backgroundColor: "transparent",
                    }}
                  >
                    <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      {c.crossed_at?.slice(11, 19) || "—"}
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      <div
                        style={{
                          width: "48px",
                          height: "30px",
                          backgroundColor: "#000000",
                          borderRadius: "3px",
                          overflow: "hidden",
                        }}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={getMediaUrl(c.image_path)}
                          alt="Crossing"
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          onError={(e) => {
                            e.currentTarget.src = "/placeholder-tactical.png";
                          }}
                        />
                      </div>
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      <span
                        className="font-mono"
                        style={{
                          backgroundColor: "#000000",
                          border: `1px solid ${c.is_whitelisted ? "var(--alert-success)" : "var(--alert-critical)"}`,
                          color: c.is_whitelisted ? "var(--alert-success)" : "var(--alert-critical)",
                          padding: "0.15rem 0.45rem",
                          borderRadius: "3px",
                          fontWeight: 800,
                        }}
                      >
                        {c.license_plate || "UNREADABLE"}
                      </span>
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      <span className="font-mono" style={{ color: "var(--text-main)", fontWeight: 700 }}>
                        {confPct}%
                      </span>
                    </td>
                    <td style={{ padding: "0.5rem", color: "var(--text-muted)" }}>
                      {c.crossing_type}
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      {c.is_whitelisted ? (
                        <span className="tactical-badge badge-success" style={{ fontSize: "0.65rem" }}>
                          AUTHORIZED
                        </span>
                      ) : (
                        <span className="tactical-badge badge-critical" style={{ fontSize: "0.65rem" }}>
                          SUSPICIOUS / UNKNOWN
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
