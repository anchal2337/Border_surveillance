"use client";

import React, { useEffect, useState } from "react";
import { Shield, Volume2, VolumeX, LogIn, LogOut, Radio, User, Clock, Terminal } from "lucide-react";
import { getStoredUser, clearToken } from "@/lib/api";
import { AuthResponse } from "@/lib/types";
import { isMuted, setMuted } from "@/lib/audio";

interface SentryNavbarProps {
  onOpenAuth: () => void;
  unreadAlertCount: number;
}

export const SentryNavbar: React.FC<SentryNavbarProps> = ({ onOpenAuth, unreadAlertCount }) => {
  const [user, setUser] = useState<AuthResponse | null>(null);
  const [muted, setMutedState] = useState<boolean>(false);
  const [timeUtc, setTimeUtc] = useState<string>("");
  const [timeLocal, setTimeLocal] = useState<string>("");

  useEffect(() => {
    setUser(getStoredUser());
    setMutedState(isMuted());

    const updateClocks = () => {
      const now = new Date();
      setTimeUtc(now.toUTCString().slice(17, 25) + " UTC");
      setTimeLocal(now.toTimeString().slice(0, 8) + " LOC");
    };
    updateClocks();
    const interval = setInterval(updateClocks, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleMute = () => {
    const next = !muted;
    setMuted(next);
    setMutedState(next);
  };

  const handleLogout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <header
      style={{
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-color)",
        padding: "0.55rem 1.25rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand & Sector Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
        <div
          style={{
            width: "34px",
            height: "34px",
            borderRadius: "2px",
            backgroundColor: "rgba(214, 168, 79, 0.12)",
            border: "1px solid var(--primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--primary)",
          }}
        >
          <Shield size={19} />
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              className="font-display"
              style={{
                fontWeight: 800,
                fontSize: "1.1rem",
                letterSpacing: "0.08em",
                color: "var(--text-main)",
              }}
            >
              IBVAP
            </span>
            <span style={{ color: "var(--border-color)" }}>/</span>
            <span
              className="font-display"
              style={{
                color: "var(--primary)",
                fontWeight: 700,
                fontSize: "0.925rem",
                letterSpacing: "0.06em",
              }}
            >
              SENTRY COMMAND CONSOLE
            </span>
            <span className="beacon-dot beacon-online" title="Gateway Live" />
          </div>
          <div
            className="font-mono"
            style={{ fontSize: "0.675rem", color: "var(--text-muted)", letterSpacing: "0.04em" }}
          >
            STN.CALLSIGN: BOP-04 • SECTOR: NORTH PERIMETER • 100% ON-PREMISE AIR-GAPPED
          </div>
        </div>
      </div>

      {/* Military Clocks & Telemetry Hub */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
        <div
          className="font-mono"
          style={{
            backgroundColor: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            padding: "0.3rem 0.65rem",
            borderRadius: "2px",
            display: "flex",
            alignItems: "center",
            gap: "0.65rem",
            fontSize: "0.75rem",
          }}
        >
          <Clock size={13} style={{ color: "var(--secondary)" }} />
          <span style={{ color: "var(--text-main)", fontWeight: 600 }}>{timeUtc}</span>
          <span style={{ color: "var(--border-color)" }}>|</span>
          <span style={{ color: "var(--text-muted)" }}>{timeLocal}</span>
        </div>

        {/* Audio Siren Chime Toggle */}
        <button
          onClick={handleToggleMute}
          title={muted ? "Audio Alerts Muted (Click to Unmute)" : "Audio Siren Armed (Click to Mute)"}
          className="tactical-btn"
          style={{
            padding: "0.3rem 0.6rem",
            fontSize: "0.725rem",
            backgroundColor: muted ? "transparent" : "rgba(214, 168, 79, 0.08)",
            color: muted ? "var(--text-muted)" : "var(--primary)",
            borderColor: muted ? "var(--border-color)" : "var(--secondary)",
          }}
        >
          {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          <span className="font-mono" style={{ fontSize: "0.675rem" }}>
            {muted ? "AUDIO: OFF" : "AUDIO: ARMED"}
          </span>
        </button>

        {/* Operator Badge / Auth Controls */}
        {user ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                padding: "0.25rem 0.6rem",
                borderRadius: "2px",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <User size={13} style={{ color: "var(--primary)" }} />
              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-main)", lineHeight: 1.1 }}>
                  {user.full_name || user.username}
                </div>
                <div
                  className="font-mono"
                  style={{ fontSize: "0.65rem", color: "var(--secondary)", fontWeight: 600, textTransform: "uppercase" }}
                >
                  [{user.role}] {user.badge_number ? `• ${user.badge_number}` : ""}
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="tactical-btn tactical-btn-secondary"
              style={{ padding: "0.3rem 0.5rem" }}
              title="Logout Operator"
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="tactical-btn tactical-btn-primary"
            style={{ padding: "0.35rem 0.75rem" }}
          >
            <LogIn size={13} />
            <span>OPERATOR SIGN IN</span>
          </button>
        )}
      </div>
    </header>
  );
};
