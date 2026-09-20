"use client";

import React from "react";
import { AuditLogItem } from "@/lib/types";
import { ShieldCheck, User, Clock, Terminal } from "lucide-react";

interface AuditTrailTableProps {
  logs: AuditLogItem[];
}

export const AuditTrailTable: React.FC<AuditTrailTableProps> = ({ logs }) => {
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
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Terminal size={17} style={{ color: "var(--primary)" }} />
          <h3 style={{ fontSize: "0.9rem", fontWeight: 800, color: "var(--text-main)", letterSpacing: "0.04em" }}>
            MILITARY NON-REPUDIATION SENTRY AUDIT TRAIL ({logs.length} EVENTS)
          </h3>
        </div>
        <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
          CHAIN-OF-CUSTODY IMMUTABLE
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.775rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)" }}>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>LOG ID</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>TIMESTAMP</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>OPERATOR ACTION</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>ENTITY</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>TARGET ID</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>IP ADDRESS</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  No operator audit events logged yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr
                  key={log.id}
                  style={{
                    borderBottom: "1px solid rgba(52, 56, 59, 0.4)",
                    backgroundColor: "transparent",
                  }}
                >
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--secondary)" }}>
                    #{log.id}
                  </td>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {log.created_at?.slice(0, 19).replace("T", " ") || "—"}
                  </td>
                  <td style={{ padding: "0.5rem", fontWeight: 700, color: "var(--text-main)" }}>
                    <span
                      style={{
                        backgroundColor: "rgba(214, 168, 79, 0.12)",
                        border: "1px solid rgba(214, 168, 79, 0.3)",
                        padding: "0.15rem 0.45rem",
                        borderRadius: "3px",
                        color: "var(--primary)",
                        fontSize: "0.7rem",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem", color: "var(--text-muted)", textTransform: "capitalize" }}>
                    {log.entity_type}
                  </td>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--text-main)" }}>
                    {log.entity_id || "—"}
                  </td>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {log.ip_address || "127.0.0.1"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
