"use client";

import React, { useState, useMemo } from "react";
import { VehicleCrossing, Vehicle } from "@/lib/types";
import { getMediaUrl, registerVehicle } from "@/lib/api";
import {
  Car,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  LayoutGrid,
  Table as TableIcon,
  RefreshCw,
  Clock,
  Camera,
  Plus,
  ExternalLink,
  ChevronRight,
  AlertTriangle,
  FileSpreadsheet,
} from "lucide-react";

interface VehicleCrossingsViewProps {
  crossings: VehicleCrossing[];
  onSelectCrossing: (crossing: VehicleCrossing) => void;
  onRefresh: () => void;
  onWhitelisted?: (vehicle: Vehicle) => void;
}

export const VehicleCrossingsView: React.FC<VehicleCrossingsViewProps> = ({
  crossings,
  onSelectCrossing,
  onRefresh,
  onWhitelisted,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "AUTH" | "UNAUTH">("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [viewMode, setViewMode] = useState<"GRID" | "TABLE">("GRID");
  const [refreshing, setRefreshing] = useState(false);
  const [whitelistingId, setWhitelistingId] = useState<number | null>(null);

  const handleManualRefresh = async () => {
    setRefreshing(true);
    await onRefresh();
    setTimeout(() => setRefreshing(false), 600);
  };

  const handleQuickWhitelist = async (e: React.MouseEvent, crossing: VehicleCrossing) => {
    e.stopPropagation();
    if (!crossing.license_plate || crossing.license_plate === "UNREADABLE") return;
    setWhitelistingId(crossing.id);
    try {
      const v = await registerVehicle({
        license_plate: crossing.license_plate,
        vehicle_type: crossing.vehicle_type,
        owner_name: "Enrolled from Crossings Dashboard",
        department: "Checkpoint Sentry",
        notes: `Quick-authorized from crossing event #${crossing.id}`,
      });
      if (onWhitelisted) onWhitelisted(v);
      await onRefresh();
    } catch {
      // ignore
    } finally {
      setWhitelistingId(null);
    }
  };

  // KPI Metrics Calculation
  const totalCount = crossings.length;
  const whitelistedCount = crossings.filter((c) => c.is_whitelisted).length;
  const unauthorizedCount = crossings.filter((c) => !c.is_whitelisted).length;
  const avgConfidence = useMemo(() => {
    if (totalCount === 0) return 0;
    const sum = crossings.reduce((acc, c) => acc + (c.ocr_confidence || 0), 0);
    return Math.round((sum / totalCount) * 100);
  }, [crossings, totalCount]);

  // Filtered List
  const filteredCrossings = useMemo(() => {
    return crossings.filter((c) => {
      // Status Filter
      if (statusFilter === "AUTH" && !c.is_whitelisted) return false;
      if (statusFilter === "UNAUTH" && c.is_whitelisted) return false;

      // Vehicle Type Filter
      if (typeFilter !== "ALL" && c.vehicle_type.toLowerCase() !== typeFilter.toLowerCase()) {
        return false;
      }

      // Search Filter
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const plate = (c.license_plate || "").toLowerCase();
        const trk = c.track_id.toString();
        const cam = (c.camera_id || "").toLowerCase();
        const crType = (c.crossing_type || "").toLowerCase();
        if (!plate.includes(query) && !trk.includes(query) && !cam.includes(query) && !crType.includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [crossings, statusFilter, typeFilter, searchTerm]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
        minHeight: "100%",
      }}
    >
      {/* Top Banner & Title */}
      <div
        className="tactical-card"
        style={{
          padding: "1rem 1.25rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "3px",
              backgroundColor: "rgba(214, 168, 79, 0.12)",
              border: "1px solid var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--primary)",
            }}
          >
            <Car size={22} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <h2
                className="font-display"
                style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-main)", letterSpacing: "0.05em" }}
              >
                VEHICLE CHECKPOINT & PERIMETER CROSSINGS
              </h2>
              <span className="tactical-badge badge-warning" style={{ fontSize: "0.65rem" }}>
                LIVE ANPR
              </span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
              Automated Number Plate Recognition (ANPR), boundary breaches, and checkpoint entry snapshots.
            </div>
          </div>
        </div>

        {/* View Toggle & Refresh Button */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div
            style={{
              display: "flex",
              backgroundColor: "var(--bg-base)",
              border: "1px solid var(--border-color)",
              borderRadius: "3px",
              padding: "2px",
            }}
          >
            <button
              onClick={() => setViewMode("GRID")}
              style={{
                backgroundColor: viewMode === "GRID" ? "var(--primary)" : "transparent",
                color: viewMode === "GRID" ? "#111315" : "var(--text-muted)",
                border: "none",
                borderRadius: "2px",
                padding: "0.3rem 0.55rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
                fontSize: "0.72rem",
                fontWeight: 700,
              }}
            >
              <LayoutGrid size={14} />
              CARDS
            </button>
            <button
              onClick={() => setViewMode("TABLE")}
              style={{
                backgroundColor: viewMode === "TABLE" ? "var(--primary)" : "transparent",
                color: viewMode === "TABLE" ? "#111315" : "var(--text-muted)",
                border: "none",
                borderRadius: "2px",
                padding: "0.3rem 0.55rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
                fontSize: "0.72rem",
                fontWeight: 700,
              }}
            >
              <TableIcon size={14} />
              TABLE
            </button>
          </div>

          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="tactical-btn"
            style={{
              padding: "0.35rem 0.75rem",
              fontSize: "0.725rem",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              cursor: "pointer",
            }}
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "SYNCING..." : "REFRESH"}
          </button>
        </div>
      </div>

      {/* 4 KPI Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
        }}
      >
        {/* Metric 1: Total Crossings */}
        <div
          className="tactical-card"
          style={{
            padding: "0.85rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.3rem",
            borderLeft: "3px solid var(--primary)",
          }}
        >
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 700, letterSpacing: "0.05em" }}>
            TOTAL DETECTED CROSSINGS
          </div>
          <div className="font-mono" style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-main)" }}>
            {totalCount}
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            Cumulative across all active video feeds
          </div>
        </div>

        {/* Metric 2: Authorized Vehicles */}
        <div
          className="tactical-card"
          style={{
            padding: "0.85rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.3rem",
            borderLeft: "3px solid var(--alert-success)",
          }}
        >
          <div style={{ fontSize: "0.7rem", color: "var(--alert-success)", fontWeight: 700, letterSpacing: "0.05em" }}>
            AUTHORIZED WHITELIST PASSES
          </div>
          <div className="font-mono" style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--alert-success)" }}>
            {whitelistedCount}
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            Pre-registered military / staff plates
          </div>
        </div>

        {/* Metric 3: Unauthorized / Breaches */}
        <div
          className="tactical-card"
          style={{
            padding: "0.85rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.3rem",
            borderLeft: "3px solid var(--alert-critical)",
          }}
        >
          <div style={{ fontSize: "0.7rem", color: "var(--alert-critical)", fontWeight: 700, letterSpacing: "0.05em" }}>
            UNREGISTERED / THREAT CROSSINGS
          </div>
          <div className="font-mono" style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--alert-critical)" }}>
            {unauthorizedCount}
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            Require operator verification or alert
          </div>
        </div>

        {/* Metric 4: Average ANPR Confidence */}
        <div
          className="tactical-card"
          style={{
            padding: "0.85rem 1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.3rem",
            borderLeft: "3px solid var(--accent-blue)",
          }}
        >
          <div style={{ fontSize: "0.7rem", color: "var(--accent-blue)", fontWeight: 700, letterSpacing: "0.05em" }}>
            MEAN ANPR OCR CONFIDENCE
          </div>
          <div className="font-mono" style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-main)" }}>
            {avgConfidence}%
          </div>
          <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
            Multi-crop adaptive CLAHE accuracy
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div
        className="tactical-card"
        style={{
          padding: "0.75rem 1rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        {/* Left: Search input */}
        <div style={{ position: "relative", minWidth: "260px", flex: "1 1 280px" }}>
          <Search
            size={14}
            style={{
              position: "absolute",
              left: "10px",
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--text-muted)",
            }}
          />
          <input
            type="text"
            placeholder="Filter by Plate (e.g. DL01, MH12), Track #, or Camera..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="tactical-input font-mono"
            style={{
              paddingLeft: "30px",
              fontSize: "0.775rem",
              width: "100%",
            }}
          />
        </div>

        {/* Right: Quick Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
          {/* Status Buttons */}
          <div style={{ display: "flex", gap: "0.25rem" }}>
            {[
              { id: "ALL", label: "ALL STATUS" },
              { id: "AUTH", label: "AUTHORIZED ONLY" },
              { id: "UNAUTH", label: "THREATS / UNREGISTERED" },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setStatusFilter(st.id as "ALL" | "AUTH" | "UNAUTH")}
                className="tactical-btn"
                style={{
                  backgroundColor: statusFilter === st.id ? "var(--primary)" : "var(--bg-base)",
                  color: statusFilter === st.id ? "#111315" : "var(--text-muted)",
                  borderColor: statusFilter === st.id ? "var(--secondary)" : "var(--border-color)",
                  padding: "0.25rem 0.55rem",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {st.label}
              </button>
            ))}
          </div>

          {/* Vehicle Type Dropdown */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="tactical-input font-mono"
            style={{ padding: "0.25rem 0.5rem", fontSize: "0.7rem", minWidth: "120px" }}
          >
            <option value="ALL">ALL VEHICLES</option>
            <option value="car">CAR</option>
            <option value="truck">TRUCK</option>
            <option value="bus">BUS</option>
            <option value="motorcycle">MOTORCYCLE</option>
            <option value="bicycle">BICYCLE</option>
          </select>
        </div>
      </div>

      {/* Main Content: Card Grid View OR Table View */}
      {filteredCrossings.length === 0 ? (
        <div
          className="tactical-card"
          style={{
            padding: "3.5rem 1rem",
            textAlign: "center",
            color: "var(--text-muted)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <Car size={36} style={{ opacity: 0.3 }} />
          <div className="font-display" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)" }}>
            NO VEHICLE CROSSINGS RECORDED
          </div>
          <div style={{ fontSize: "0.75rem", maxWidth: "450px" }}>
            When vehicles enter the geofence or cross the virtual tripwire, automated snapshots, license plates, and ANPR records will appear here in real-time.
          </div>
        </div>
      ) : viewMode === "GRID" ? (
        /* GRID VIEW */
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))",
            gap: "1rem",
          }}
        >
          {filteredCrossings.map((c) => {
            const isAuth = c.is_whitelisted;
            const confPct = Math.round((c.ocr_confidence || 0) * 100);
            const plateText = c.license_plate || "UNREADABLE";

            return (
              <div
                key={c.id}
                onClick={() => onSelectCrossing(c)}
                className="tactical-card"
                style={{
                  cursor: "pointer",
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                  transition: "all 0.15s ease",
                  border: `1px solid ${isAuth ? "rgba(46, 204, 113, 0.4)" : "var(--border-color)"}`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = isAuth ? "var(--alert-success)" : "var(--primary)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = isAuth ? "rgba(46, 204, 113, 0.4)" : "var(--border-color)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                {/* Snapshot Image Container */}
                <div
                  style={{
                    position: "relative",
                    width: "100%",
                    height: "170px",
                    backgroundColor: "#000000",
                    overflow: "hidden",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={getMediaUrl(c.image_path)}
                    alt={`Crossing #${c.id}`}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                    onError={(e) => {
                      e.currentTarget.src = "/placeholder-tactical.png";
                    }}
                  />

                  {/* Top Badges */}
                  <div
                    style={{
                      position: "absolute",
                      top: "8px",
                      left: "8px",
                      display: "flex",
                      gap: "0.4rem",
                    }}
                  >
                    <span
                      className={`tactical-badge ${isAuth ? "badge-success" : "badge-critical"}`}
                      style={{ fontSize: "0.625rem", padding: "0.15rem 0.4rem" }}
                    >
                      {isAuth ? "AUTHORIZED" : "UNREGISTERED"}
                    </span>
                    <span
                      className="tactical-badge"
                      style={{
                        backgroundColor: "rgba(17, 19, 21, 0.85)",
                        color: "var(--text-main)",
                        fontSize: "0.625rem",
                        padding: "0.15rem 0.4rem",
                      }}
                    >
                      {c.vehicle_type.toUpperCase()}
                    </span>
                  </div>

                  {/* Confidence Pill */}
                  <div
                    className="font-mono"
                    style={{
                      position: "absolute",
                      top: "8px",
                      right: "8px",
                      backgroundColor: "rgba(17, 19, 21, 0.85)",
                      border: "1px solid var(--border-color)",
                      color: confPct >= 70 ? "var(--alert-success)" : "var(--text-main)",
                      fontSize: "0.65rem",
                      fontWeight: 700,
                      padding: "0.15rem 0.35rem",
                      borderRadius: "2px",
                    }}
                  >
                    OCR {confPct}%
                  </div>

                  {/* Bottom Plate Badge */}
                  <div
                    style={{
                      position: "absolute",
                      bottom: "8px",
                      left: "8px",
                      backgroundColor: "rgba(17, 19, 21, 0.92)",
                      border: `1px solid ${isAuth ? "var(--alert-success)" : "var(--alert-critical)"}`,
                      padding: "0.2rem 0.55rem",
                      borderRadius: "2px",
                    }}
                  >
                    <span
                      className="font-mono"
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 800,
                        color: isAuth ? "var(--alert-success)" : "var(--alert-critical)",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {plateText}
                    </span>
                  </div>
                </div>

                {/* Card Content & Details */}
                <div style={{ padding: "0.85rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-main)" }}>
                      {c.crossing_type}
                    </span>
                    <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      Track #{c.track_id}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <Camera size={12} />
                      <span>{c.camera_id || "CAM-01"}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <Clock size={12} />
                      <span className="font-mono">{c.crossed_at?.slice(11, 19) || "—"}</span>
                    </div>
                  </div>

                  {/* Action Bar */}
                  <div
                    style={{
                      marginTop: "0.25rem",
                      borderTop: "1px solid var(--border-color)",
                      paddingTop: "0.6rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.7rem",
                        color: "var(--primary)",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "0.2rem",
                      }}
                    >
                      INSPECT DOSSIER <ChevronRight size={13} />
                    </span>

                    {!isAuth && plateText !== "UNREADABLE" && (
                      <button
                        onClick={(e) => handleQuickWhitelist(e, c)}
                        disabled={whitelistingId === c.id}
                        className="tactical-btn font-mono"
                        style={{
                          fontSize: "0.65rem",
                          padding: "0.2rem 0.45rem",
                          backgroundColor: "rgba(46, 204, 113, 0.15)",
                          borderColor: "var(--alert-success)",
                          color: "var(--alert-success)",
                          display: "flex",
                          alignItems: "center",
                          gap: "0.2rem",
                        }}
                      >
                        <Plus size={11} />
                        {whitelistingId === c.id ? "ADDING..." : "WHITELIST"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* TABLE VIEW */
        <div className="tactical-card" style={{ padding: "0.75rem", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.775rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)" }}>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>TIMESTAMP</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>SNAPSHOT</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>DETECTED PLATE</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>CONFIDENCE</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>VEHICLE TYPE</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>CROSSING TYPE</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>CHANNEL</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700 }}>STATUS</th>
                <th style={{ padding: "0.6rem 0.75rem", fontWeight: 700, textAlign: "right" }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredCrossings.map((c) => {
                const confPct = Math.round((c.ocr_confidence || 0) * 100);
                const isAuth = c.is_whitelisted;
                const plateText = c.license_plate || "UNREADABLE";

                return (
                  <tr
                    key={c.id}
                    onClick={() => onSelectCrossing(c)}
                    style={{
                      borderBottom: "1px solid rgba(52, 56, 59, 0.4)",
                      cursor: "pointer",
                      transition: "background-color 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = "rgba(214, 168, 79, 0.05)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = "transparent";
                    }}
                  >
                    <td style={{ padding: "0.6rem 0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      {c.crossed_at?.slice(11, 19) || "—"}
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem" }}>
                      <div
                        style={{
                          width: "52px",
                          height: "32px",
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

                    <td style={{ padding: "0.6rem 0.75rem" }}>
                      <span
                        className="font-mono"
                        style={{
                          backgroundColor: "#000000",
                          border: `1px solid ${isAuth ? "var(--alert-success)" : "var(--alert-critical)"}`,
                          color: isAuth ? "var(--alert-success)" : "var(--alert-critical)",
                          padding: "0.15rem 0.45rem",
                          borderRadius: "3px",
                          fontWeight: 800,
                        }}
                      >
                        {plateText}
                      </span>
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem" }}>
                      <span
                        className="font-mono"
                        style={{
                          fontWeight: 700,
                          color: confPct >= 70 ? "var(--alert-success)" : confPct >= 40 ? "var(--primary)" : "var(--alert-critical)",
                        }}
                      >
                        {confPct}%
                      </span>
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem", textTransform: "uppercase" }}>
                      {c.vehicle_type}
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem", color: "var(--text-muted)" }}>
                      {c.crossing_type}
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem", fontFamily: "var(--font-mono)" }}>
                      {c.camera_id || "CAM-01"}
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem" }}>
                      <span
                        className={`tactical-badge ${isAuth ? "badge-success" : "badge-critical"}`}
                        style={{ fontSize: "0.65rem" }}
                      >
                        {isAuth ? "AUTHORIZED" : "UNREGISTERED"}
                      </span>
                    </td>

                    <td style={{ padding: "0.6rem 0.75rem", textAlign: "right" }}>
                      <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.4rem" }}>
                        {!isAuth && plateText !== "UNREADABLE" && (
                          <button
                            onClick={(e) => handleQuickWhitelist(e, c)}
                            disabled={whitelistingId === c.id}
                            className="tactical-btn font-mono"
                            style={{
                              fontSize: "0.65rem",
                              padding: "0.2rem 0.45rem",
                              backgroundColor: "rgba(46, 204, 113, 0.15)",
                              borderColor: "var(--alert-success)",
                              color: "var(--alert-success)",
                            }}
                          >
                            <Plus size={11} />
                            {whitelistingId === c.id ? "ADDING..." : "WHITELIST"}
                          </button>
                        )}
                        <button
                          onClick={() => onSelectCrossing(c)}
                          className="tactical-btn font-mono"
                          style={{
                            fontSize: "0.65rem",
                            padding: "0.2rem 0.45rem",
                            borderColor: "var(--primary)",
                            color: "var(--primary)",
                          }}
                        >
                          VIEW
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
