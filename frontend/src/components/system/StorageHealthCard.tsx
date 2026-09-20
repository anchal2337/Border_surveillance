"use client";

import React, { useState } from "react";
import { StorageHealth } from "@/lib/types";
import { pruneEvidence } from "@/lib/api";
import { HardDrive, Trash2, ShieldCheck, AlertCircle, Database, Folder } from "lucide-react";

interface StorageHealthCardProps {
  health: StorageHealth | null;
  onRefresh: () => void;
}

export const StorageHealthCard: React.FC<StorageHealthCardProps> = ({ health, onRefresh }) => {
  const [pruning, setPruning] = useState(false);
  const [pruneResult, setPruneResult] = useState<string | null>(null);

  const handlePrune = async () => {
    if (!confirm("Execute FIFO retention purge on media older than 30 days?")) return;
    setPruning(true);
    setPruneResult(null);
    try {
      const res = await pruneEvidence(30);
      setPruneResult(`Purged ${res.files_removed} files (${res.mb_reclaimed} MB reclaimed).`);
      onRefresh();
    } catch {
      setPruneResult("Pruning operation failed.");
    } finally {
      setPruning(false);
    }
  };

  if (!health) return null;

  const totalGb = (health.total_disk_bytes / (1024 * 1024 * 1024)).toFixed(1);
  const freeGb = (health.free_disk_bytes / (1024 * 1024 * 1024)).toFixed(1);
  const usedGb = (health.used_disk_bytes / (1024 * 1024 * 1024)).toFixed(1);
  const usedPct = Math.round((health.used_disk_bytes / health.total_disk_bytes) * 100);

  const evidenceMb = (health.evidence_dir_bytes / (1024 * 1024)).toFixed(1);
  const crossingsMb = (health.crossings_dir_bytes / (1024 * 1024)).toFixed(1);
  const dbMb = (health.database_bytes / (1024 * 1024)).toFixed(2);

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-color)",
        borderRadius: "6px",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <HardDrive size={18} style={{ color: "var(--primary)" }} />
          <div>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 800, color: "var(--text-main)", letterSpacing: "0.04em" }}>
              AIR-GAPPED STORAGE HEALTH & FIFO RETENTION
            </h3>
            <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
              Continuous 24/7 edge video surveillance quota management.
            </div>
          </div>
        </div>

        <button
          onClick={handlePrune}
          disabled={pruning}
          className="tactical-btn tactical-btn-secondary"
          style={{ fontSize: "0.725rem" }}
        >
          <Trash2 size={13} style={{ color: "var(--alert-critical)" }} />
          <span>{pruning ? "PURGING..." : "EXECUTE FIFO PRUNE"}</span>
        </button>
      </div>

      {pruneResult && (
        <div
          style={{
            backgroundColor: "rgba(114, 168, 121, 0.15)",
            border: "1px solid var(--alert-success)",
            color: "var(--alert-success)",
            padding: "0.5rem 0.75rem",
            borderRadius: "4px",
            fontSize: "0.75rem",
          }}
        >
          {pruneResult}
        </div>
      )}

      {/* Disk Usage Bar */}
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.775rem",
            marginBottom: "0.4rem",
          }}
        >
          <span style={{ color: "var(--text-muted)" }}>
            Local Workstation Drive: <span style={{ color: "var(--text-main)", fontWeight: 700 }}>{usedGb} GB used</span> of {totalGb} GB
          </span>
          <span className="font-mono" style={{ color: usedPct > 80 ? "var(--alert-critical)" : "var(--primary)", fontWeight: 700 }}>
            {usedPct}% CAPACITY
          </span>
        </div>

        <div
          style={{
            height: "8px",
            backgroundColor: "var(--bg-card)",
            borderRadius: "4px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${usedPct}%`,
              height: "100%",
              backgroundColor: usedPct > 80 ? "var(--alert-critical)" : "var(--primary)",
              transition: "width 0.4s ease",
            }}
          />
        </div>
      </div>

      {/* Breakdown Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "0.75rem",
        }}
      >
        <div
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "4px",
            padding: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--text-muted)", fontSize: "0.725rem", marginBottom: "0.25rem" }}>
            <Folder size={14} style={{ color: "var(--primary)" }} />
            <span>Evidence Locker</span>
          </div>
          <div className="font-mono" style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-main)" }}>
            {evidenceMb} MB
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            {health.evidence_count} forensic cases
          </div>
        </div>

        <div
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "4px",
            padding: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--text-muted)", fontSize: "0.725rem", marginBottom: "0.25rem" }}>
            <Folder size={14} style={{ color: "var(--secondary)" }} />
            <span>ANPR Crossings</span>
          </div>
          <div className="font-mono" style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-main)" }}>
            {crossingsMb} MB
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            {health.crossings_count} vehicle crops
          </div>
        </div>

        <div
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: "4px",
            padding: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--text-muted)", fontSize: "0.725rem", marginBottom: "0.25rem" }}>
            <Database size={14} style={{ color: "var(--alert-success)" }} />
            <span>SQLite Database</span>
          </div>
          <div className="font-mono" style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-main)" }}>
            {dbMb} MB
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--alert-success)", fontWeight: 600 }}>
            WAL Mode Active
          </div>
        </div>
      </div>
    </div>
  );
};
