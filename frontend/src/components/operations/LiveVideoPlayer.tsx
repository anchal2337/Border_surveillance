"use client";

import React, { useState, useEffect } from "react";
import { Camera } from "@/lib/types";
import { getLiveFeedUrl } from "@/lib/api";
import { Maximize2, RefreshCw, Radio, AlertCircle } from "lucide-react";

interface LiveVideoPlayerProps {
  camera: Camera | null;
  fps: number;
  activeTracks: number;
  maxThreat: number;
}

export const LiveVideoPlayer: React.FC<LiveVideoPlayerProps> = ({
  camera,
  fps,
  activeTracks,
  maxThreat,
}) => {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [hasError, setHasError] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  useEffect(() => {
    if (camera?.id) {
      setHasError(false);
      setStreamUrl(`${getLiveFeedUrl(camera.id)}?t=${Date.now()}`);
    } else {
      setStreamUrl(null);
    }
  }, [camera?.id]);

  const handleRefresh = () => {
    if (!camera?.id) return;
    setIsRefreshing(true);
    setHasError(false);
    setStreamUrl(`${getLiveFeedUrl(camera.id)}?t=${Date.now()}`);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  const handleFullScreen = () => {
    const el = document.getElementById("sentry-video-container");
    if (el) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        el.requestFullscreen();
      }
    }
  };

  if (!camera) {
    return (
      <div
        className="tactical-card"
        style={{
          width: "100%",
          height: "460px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.85rem",
          color: "var(--text-muted)",
        }}
      >
        <Radio size={32} style={{ color: "var(--secondary)", opacity: 0.7 }} />
        <div className="font-display" style={{ fontSize: "1rem", fontWeight: 700, letterSpacing: "0.06em" }}>
          NO SENSOR CHANNEL SELECTED
        </div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Select a surveillance stream from the tactical sensor array below.
        </div>
      </div>
    );
  }

  const isCritical = maxThreat >= 85;

  return (
    <div
      id="sentry-video-container"
      style={{
        position: "relative",
        width: "100%",
        backgroundColor: "#080a0c",
        border: `1px solid ${isCritical ? "var(--alert-critical)" : "var(--border-color)"}`,
        boxShadow: isCritical ? "0 0 20px var(--critical-glow)" : "0 8px 30px rgba(0,0,0,0.6)",
        transition: "border-color 0.25s ease, box-shadow 0.25s ease",
        borderRadius: "2px",
        overflow: "hidden",
      }}
    >
      {/* Precision Reticle Corner Markers */}
      <div style={{ position: "absolute", top: "6px", left: "6px", width: "12px", height: "12px", borderTop: "2px solid var(--primary)", borderLeft: "2px solid var(--primary)", zIndex: 15, pointerEvents: "none" }} />
      <div style={{ position: "absolute", top: "6px", right: "6px", width: "12px", height: "12px", borderTop: "2px solid var(--primary)", borderRight: "2px solid var(--primary)", zIndex: 15, pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "6px", left: "6px", width: "12px", height: "12px", borderBottom: "2px solid var(--primary)", borderLeft: "2px solid var(--primary)", zIndex: 15, pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "6px", right: "6px", width: "12px", height: "12px", borderBottom: "2px solid var(--primary)", borderRight: "2px solid var(--primary)", zIndex: 15, pointerEvents: "none" }} />

      {/* Top HUD Telemetry Bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          padding: "0.45rem 0.85rem",
          background: "linear-gradient(to bottom, rgba(17, 19, 21, 0.95), rgba(17, 19, 21, 0))",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 10,
          pointerEvents: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span className={`beacon-dot ${camera.status === "ONLINE" ? "beacon-online" : "beacon-warning"}`} />
          <span
            className="font-mono"
            style={{ fontSize: "0.85rem", fontWeight: 800, color: "var(--primary)", letterSpacing: "0.06em" }}
          >
            [{camera.id}]
          </span>
          <span
            className="font-display"
            style={{ fontSize: "0.85rem", color: "var(--text-main)", fontWeight: 700, letterSpacing: "0.05em" }}
          >
            {camera.name.toUpperCase()}
          </span>
          <span style={{ color: "var(--border-color)" }}>/</span>
          <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
            {camera.sector_zone}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", pointerEvents: "auto" }}>
          <div
            className="font-mono tactical-badge"
            style={{
              backgroundColor: "rgba(17, 19, 21, 0.85)",
              border: "1px solid var(--border-color)",
              color: "var(--text-main)",
            }}
          >
            FPS: <span style={{ color: "var(--alert-success)", fontWeight: 700 }}>{fps > 0 ? fps.toFixed(1) : "30.0"}</span>
          </div>

          <div
            className="font-mono tactical-badge"
            style={{
              backgroundColor: "rgba(17, 19, 21, 0.85)",
              border: "1px solid var(--border-color)",
              color: "var(--text-main)",
            }}
          >
            TARGETS: <span style={{ color: "var(--primary)", fontWeight: 700 }}>{activeTracks}</span>
          </div>

          <button
            onClick={handleRefresh}
            className="tactical-btn tactical-btn-secondary"
            style={{ padding: "0.2rem 0.45rem" }}
            title="Refresh Ingestion Stream"
          >
            <RefreshCw size={12} className={isRefreshing ? "animate-spin" : ""} />
          </button>

          <button
            onClick={handleFullScreen}
            className="tactical-btn tactical-btn-secondary"
            style={{ padding: "0.2rem 0.45rem" }}
            title="Full Screen Tactical View"
          >
            <Maximize2 size={12} />
          </button>
        </div>
      </div>

      {/* Main Video Stream Frame */}
      <div style={{ position: "relative", minHeight: "440px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {streamUrl && !hasError ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={streamUrl}
            alt={`Live Video Stream ${camera.id}`}
            style={{
              width: "100%",
              height: "auto",
              maxHeight: "68vh",
              objectFit: "contain",
              display: "block",
            }}
            onError={() => setHasError(true)}
          />
        ) : (
          <div
            style={{
              padding: "3rem",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "1rem",
              color: "var(--text-muted)",
              textAlign: "center",
            }}
          >
            <AlertCircle size={36} style={{ color: "var(--alert-critical)" }} />
            <div className="font-display" style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}>
              STREAM CARRIER HANDSHAKE PENDING
            </div>
            <div style={{ fontSize: "0.775rem", maxWidth: "420px" }}>
              The camera ingestion thread is synchronizing frame buffers. Click reconnect to refresh.
            </div>
            <button onClick={handleRefresh} className="tactical-btn tactical-btn-primary">
              <RefreshCw size={13} /> RECONNECT STREAM
            </button>
          </div>
        )}
      </div>

      {/* Bottom HUD Overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "0.35rem 0.85rem",
          background: "linear-gradient(to top, rgba(17, 19, 21, 0.95), rgba(17, 19, 21, 0))",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "0.7rem",
          pointerEvents: "none",
        }}
      >
        <div className="font-mono" style={{ color: "var(--text-muted)" }}>
          AI_MODEL: <span style={{ color: "var(--text-main)" }}>{camera.ai_pipeline}</span>
        </div>
        <div className="font-mono" style={{ color: "var(--text-muted)" }}>
          RES: <span style={{ color: "var(--text-main)" }}>{camera.resolution}</span> • PROTOCOL:{" "}
          <span style={{ color: "var(--secondary)", fontWeight: 700 }}>{camera.source_type}</span>
        </div>
      </div>
    </div>
  );
};
