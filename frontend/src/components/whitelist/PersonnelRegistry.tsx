"use client";

import React, { useState } from "react";
import { Personnel } from "@/lib/types";
import { getMediaUrl } from "@/lib/api";
import { UserCheck, UserPlus, Trash2, Image as ImageIcon } from "lucide-react";

interface PersonnelRegistryProps {
  personnel: Personnel[];
  onOpenEnroll: () => void;
  onDeletePersonnel: (id: string) => Promise<void>;
}

export const PersonnelRegistry: React.FC<PersonnelRegistryProps> = ({
  personnel,
  onOpenEnroll,
  onDeletePersonnel,
}) => {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to revoke perimeter access for this personnel?")) return;
    setDeletingId(id);
    try {
      await onDeletePersonnel(id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div
      className="tactical-card"
      style={{
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.85rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <UserCheck size={18} style={{ color: "var(--primary)" }} />
          <div>
            <h3 className="font-display" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}>
              BIOMETRIC PERSONNEL WHITELIST (FRS)
            </h3>
            <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
              512-dimensional facial recognition vectors for automated checkpoint verification.
            </div>
          </div>
        </div>

        <button onClick={onOpenEnroll} className="tactical-btn tactical-btn-primary">
          <UserPlus size={13} />
          <span>ENROLL AUTHORIZED PERSONNEL</span>
        </button>
      </div>

      {/* Personnel Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.775rem" }}>
          <thead>
            <tr className="font-display" style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)", fontSize: "0.8rem", letterSpacing: "0.04em" }}>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>PORTRAIT</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>OFFICER NAME</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>RANK / DESIGNATION</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>BADGE #</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>DEPARTMENT</th>
              <th style={{ padding: "0.5rem", fontWeight: 700 }}>STATUS</th>
              <th style={{ padding: "0.5rem", fontWeight: 700, textAlign: "right" }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {personnel.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  No authorized personnel enrolled yet. Click Enroll to add officers.
                </td>
              </tr>
            ) : (
              personnel.map((p) => (
                <tr
                  key={p.id}
                  style={{
                    borderBottom: "1px solid rgba(52, 56, 59, 0.4)",
                    backgroundColor: "transparent",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-card)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "0.45rem 0.5rem" }}>
                    <div
                      style={{
                        width: "34px",
                        height: "34px",
                        borderRadius: "2px",
                        backgroundColor: "#000000",
                        border: "1px solid var(--border-color)",
                        overflow: "hidden",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {p.photo_path ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={getMediaUrl(p.photo_path)}
                          alt={p.full_name}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          onError={(e) => {
                            e.currentTarget.src = "/placeholder-tactical.png";
                          }}
                        />
                      ) : (
                        <ImageIcon size={15} style={{ color: "var(--text-muted)" }} />
                      )}
                    </div>
                  </td>
                  <td style={{ padding: "0.5rem", fontWeight: 700, color: "var(--text-main)" }}>
                    {p.full_name}
                  </td>
                  <td style={{ padding: "0.5rem", color: "var(--secondary)", fontWeight: 600 }}>
                    {p.designation}
                  </td>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", color: "var(--text-main)" }}>
                    {p.badge_number || "—"}
                  </td>
                  <td style={{ padding: "0.5rem", color: "var(--text-muted)" }}>
                    {p.department}
                  </td>
                  <td style={{ padding: "0.5rem" }}>
                    <span className="tactical-badge badge-success" style={{ fontSize: "0.625rem" }}>
                      AUTHORIZED
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>
                    <button
                      onClick={() => handleDelete(p.id)}
                      disabled={deletingId === p.id}
                      className="tactical-btn tactical-btn-secondary"
                      style={{ padding: "0.2rem 0.45rem", color: "var(--alert-critical)" }}
                      title="Revoke Personnel Clearance"
                    >
                      <Trash2 size={12} />
                    </button>
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
