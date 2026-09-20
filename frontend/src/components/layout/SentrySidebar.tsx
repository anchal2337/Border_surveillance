"use client";

import React from "react";
import {
  Radio,
  Sliders,
  AlertTriangle,
  FolderLock,
  UserCheck,
  Server,
  Cpu,
  Car,
} from "lucide-react";

export type NavTab = "operations" | "zones" | "alerts" | "evidence" | "crossings" | "whitelist" | "system";

interface SentrySidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  unreadAlertCount: number;
}

export const SentrySidebar: React.FC<SentrySidebarProps> = ({
  activeTab,
  onSelectTab,
  unreadAlertCount,
}) => {
  const navItems = [
    {
      id: "operations" as NavTab,
      index: "01",
      label: "LIVE OPERATIONS",
      subtext: "Real-Time Video HUD",
      icon: Radio,
    },
    {
      id: "zones" as NavTab,
      index: "02",
      label: "ZONE STUDIO",
      subtext: "Geofences & Tripwires",
      icon: Sliders,
    },
    {
      id: "alerts" as NavTab,
      index: "03",
      label: "PERIMETER ALERTS",
      subtext: "Incident Ticker Stream",
      icon: AlertTriangle,
      badge: unreadAlertCount > 0 ? unreadAlertCount : undefined,
    },
    {
      id: "evidence" as NavTab,
      index: "04",
      label: "EVIDENCE LOCKER",
      subtext: "Forensic SHA-256 Cases",
      icon: FolderLock,
    },
    {
      id: "crossings" as NavTab,
      index: "05",
      label: "VEHICLE CROSSINGS",
      subtext: "ANPR Checkpoint & Fence",
      icon: Car,
    },
    {
      id: "whitelist" as NavTab,
      index: "06",
      label: "FRS & ANPR REGISTRY",
      subtext: "Personnel & Plates",
      icon: UserCheck,
    },
    {
      id: "system" as NavTab,
      index: "07",
      label: "STATION HEALTH",
      subtext: "Storage & Audit Logs",
      icon: Server,
    },
  ];

  return (
    <aside
      style={{
        width: "250px",
        backgroundColor: "var(--bg-surface)",
        borderRight: "1px solid var(--border-color)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        height: "calc(100vh - 54px)",
        padding: "0.75rem 0.5rem",
      }}
    >
      {/* Navigation Buttons */}
      <nav style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
        <div
          className="section-id"
          style={{
            padding: "0.3rem 0.75rem",
            marginBottom: "0.2rem",
          }}
        >
          [CONSOLE_MODULES // V1.0.4]
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.55rem 0.75rem",
                borderRadius: "2px",
                border: "1px solid",
                borderColor: isActive ? "var(--primary)" : "transparent",
                backgroundColor: isActive ? "rgba(214, 168, 79, 0.1)" : "transparent",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "var(--bg-card)";
                  e.currentTarget.style.borderColor = "var(--border-color)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.borderColor = "transparent";
                }
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <span
                  className="font-mono"
                  style={{
                    fontSize: "0.65rem",
                    color: isActive ? "var(--primary)" : "var(--text-muted)",
                    fontWeight: 700,
                  }}
                >
                  {item.index}
                </span>

                <Icon
                  size={16}
                  style={{
                    color: isActive ? "var(--primary)" : "var(--text-muted)",
                    flexShrink: 0,
                  }}
                />
                <div>
                  <div
                    className="font-display"
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: isActive ? "var(--text-main)" : "var(--text-muted)",
                      letterSpacing: "0.04em",
                    }}
                  >
                    {item.label}
                  </div>
                  <div
                    style={{
                      fontSize: "0.675rem",
                      color: isActive ? "var(--secondary)" : "rgba(146, 151, 155, 0.65)",
                    }}
                  >
                    {item.subtext}
                  </div>
                </div>
              </div>

              {item.badge !== undefined && (
                <span
                  className="tactical-badge badge-critical font-mono"
                  style={{ fontSize: "0.675rem", padding: "0.1rem 0.4rem" }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Sentry Station Telemetry Footer */}
      <div
        className="tactical-card"
        style={{
          padding: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", marginBottom: "0.45rem" }}>
          <Cpu size={13} style={{ color: "var(--secondary)" }} />
          <span
            className="font-display"
            style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}
          >
            TACTICAL ARCHITECTURE
          </span>
        </div>

        <div className="font-mono" style={{ fontSize: "0.675rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>INGEST:</span>
            <span style={{ color: "var(--alert-success)", fontWeight: 600 }}>RTSP / ONVIF / FILE</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>DB_ENGINE:</span>
            <span style={{ color: "var(--text-main)" }}>SQLite (WAL)</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>INFERENCE:</span>
            <span style={{ color: "var(--primary)", fontWeight: 600 }}>100% On-Premise</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
