"use client";

import React, { useRef, useState, useEffect } from "react";
import { Camera } from "@/lib/types";
import { getSnapshotUrl } from "@/lib/api";
import { Sliders, RotateCcw, Check, Crosshair } from "lucide-react";

interface ZoneCalibratorCanvasProps {
  camera: Camera | null;
  initialGeofence?: number[][];
  initialTripwire?: number[][];
  onDeployZones: (geofence: number[][], tripwire: number[][]) => Promise<void>;
}

export const ZoneCalibratorCanvas: React.FC<ZoneCalibratorCanvasProps> = ({
  camera,
  initialGeofence,
  initialTripwire,
  onDeployZones,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [snapshotImg, setSnapshotImg] = useState<HTMLImageElement | null>(null);
  const [geofencePts, setGeofencePts] = useState<number[][]>(initialGeofence || []);
  const [tripwirePts, setTripwirePts] = useState<number[][]>(initialTripwire || []);
  const [mode, setMode] = useState<"GEOFENCE" | "TRIPWIRE">("GEOFENCE");
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDeploying, setIsDeploying] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!camera) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = getSnapshotUrl(camera.id);
    img.onload = () => {
      setSnapshotImg(img);
    };
    img.onerror = () => {
      setSnapshotImg(null);
    };
  }, [camera?.id]);

  useEffect(() => {
    if (initialGeofence) setGeofencePts(initialGeofence);
    if (initialTripwire) setTripwirePts(initialTripwire);
  }, [initialGeofence, initialTripwire]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (snapshotImg) {
      ctx.drawImage(snapshotImg, 0, 0, canvas.width, canvas.height);
    } else {
      ctx.fillStyle = "#121417";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = "rgba(52, 56, 59, 0.4)";
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }
      ctx.fillStyle = "var(--text-muted)";
      ctx.font = "12px monospace";
      ctx.fillText("[SENTRY SNAPSHOT CALIBRATION GRID]", 20, 30);
    }

    // 1. Draw Geofence Polygon
    if (geofencePts.length > 0) {
      ctx.beginPath();
      ctx.moveTo(geofencePts[0][0], geofencePts[0][1]);
      for (let i = 1; i < geofencePts.length; i++) {
        ctx.lineTo(geofencePts[i][0], geofencePts[i][1]);
      }
      if (geofencePts.length >= 3) {
        ctx.closePath();
        ctx.fillStyle = "rgba(214, 168, 79, 0.18)";
        ctx.fill();
      }
      ctx.strokeStyle = "var(--primary)";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      geofencePts.forEach((pt, idx) => {
        ctx.beginPath();
        ctx.arc(pt[0], pt[1], 5, 0, Math.PI * 2);
        ctx.fillStyle = "var(--primary)";
        ctx.fill();
        ctx.strokeStyle = "#111315";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "var(--text-main)";
        ctx.font = "11px monospace";
        ctx.fillText(`P${idx + 1}`, pt[0] + 8, pt[1] - 4);
      });
    }

    // 2. Draw Virtual Tripwire
    if (tripwirePts.length > 0) {
      ctx.beginPath();
      ctx.moveTo(tripwirePts[0][0], tripwirePts[0][1]);
      for (let i = 1; i < tripwirePts.length; i++) {
        ctx.lineTo(tripwirePts[i][0], tripwirePts[i][1]);
      }
      ctx.strokeStyle = "var(--alert-critical)";
      ctx.lineWidth = 3;
      ctx.stroke();

      tripwirePts.forEach((pt, idx) => {
        ctx.beginPath();
        ctx.arc(pt[0], pt[1], 6, 0, Math.PI * 2);
        ctx.fillStyle = "var(--alert-critical)";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "var(--alert-critical)";
        ctx.font = "11px monospace";
        ctx.fillText(idx === 0 ? "WIRE_A" : "WIRE_B", pt[0] + 8, pt[1] - 4);
      });
    }

    // Crosshair reticle cursor
    ctx.strokeStyle = "rgba(214, 168, 79, 0.6)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(mousePos.x - 12, mousePos.y);
    ctx.lineTo(mousePos.x + 12, mousePos.y);
    ctx.moveTo(mousePos.x, mousePos.y - 12);
    ctx.lineTo(mousePos.x, mousePos.y + 12);
    ctx.stroke();
  }, [snapshotImg, geofencePts, tripwirePts, mousePos]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = Math.round((e.clientX - rect.left) * scaleX);
    const y = Math.round((e.clientY - rect.top) * scaleY);

    if (mode === "GEOFENCE") {
      setGeofencePts((prev) => [...prev, [x, y]]);
    } else {
      if (tripwirePts.length >= 2) {
        setTripwirePts([[x, y]]);
      } else {
        setTripwirePts((prev) => [...prev, [x, y]]);
      }
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = Math.round((e.clientX - rect.left) * scaleX);
    const y = Math.round((e.clientY - rect.top) * scaleY);
    setMousePos({ x, y });
  };

  const handleReset = () => {
    if (mode === "GEOFENCE") setGeofencePts([]);
    else setTripwirePts([]);
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    setFeedbackMsg(null);
    try {
      await onDeployZones(geofencePts, tripwirePts);
      setFeedbackMsg("PERIMETER CALIBRATION DEPLOYED TO EDGE INFERENCE ENGINE");
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (err: unknown) {
      setFeedbackMsg(err instanceof Error ? err.message : "Deployment failed");
    } finally {
      setIsDeploying(false);
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
      {/* Studio Header & Toolset */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Crosshair size={18} style={{ color: "var(--primary)" }} />
          <div>
            <h3 className="font-display" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}>
              INTERACTIVE ZONE & TRIPWIRE STUDIO
            </h3>
            <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
              Calibrate spatial detection geometry over frozen camera snapshot frame.
            </div>
          </div>
        </div>

        {/* Mode Toggles */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <button
            onClick={() => setMode("GEOFENCE")}
            className="tactical-btn"
            style={{
              backgroundColor: mode === "GEOFENCE" ? "var(--primary)" : "var(--bg-card)",
              color: mode === "GEOFENCE" ? "#111315" : "var(--text-main)",
              borderColor: mode === "GEOFENCE" ? "var(--secondary)" : "var(--border-color)",
            }}
          >
            GEOFENCE POLYGON ({geofencePts.length} PTS)
          </button>

          <button
            onClick={() => setMode("TRIPWIRE")}
            className="tactical-btn"
            style={{
              backgroundColor: mode === "TRIPWIRE" ? "var(--alert-critical)" : "var(--bg-card)",
              color: mode === "TRIPWIRE" ? "#ffffff" : "var(--text-main)",
              borderColor: mode === "TRIPWIRE" ? "var(--alert-critical)" : "var(--border-color)",
            }}
          >
            VIRTUAL TRIPWIRE ({tripwirePts.length}/2 PTS)
          </button>

          <button
            onClick={handleReset}
            className="tactical-btn tactical-btn-secondary"
            title="Clear Current Mode Points"
          >
            <RotateCcw size={12} />
            <span>RESET</span>
          </button>

          <button
            onClick={handleDeploy}
            disabled={isDeploying || (geofencePts.length < 3 && tripwirePts.length < 2)}
            className="tactical-btn tactical-btn-primary"
          >
            <Check size={13} />
            <span>{isDeploying ? "DEPLOYING..." : "DEPLOY TO EDGE"}</span>
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className="font-mono"
          style={{
            backgroundColor: "rgba(114, 168, 121, 0.12)",
            border: "1px solid var(--alert-success)",
            color: "var(--alert-success)",
            padding: "0.45rem 0.75rem",
            borderRadius: "2px",
            fontSize: "0.75rem",
            fontWeight: 700,
          }}
        >
          {feedbackMsg}
        </div>
      )}

      {/* Canvas Viewport */}
      <div
        style={{
          position: "relative",
          backgroundColor: "#000000",
          border: "1px solid var(--border-color)",
          borderRadius: "2px",
          overflow: "hidden",
          cursor: "crosshair",
        }}
      >
        <canvas
          ref={canvasRef}
          width={1080}
          height={720}
          onClick={handleCanvasClick}
          onMouseMove={handleMouseMove}
          style={{
            width: "100%",
            height: "auto",
            display: "block",
          }}
        />

        {/* Live Coordinate Overlay */}
        <div
          className="font-mono"
          style={{
            position: "absolute",
            bottom: "8px",
            right: "8px",
            backgroundColor: "rgba(17, 19, 21, 0.9)",
            border: "1px solid var(--border-color)",
            padding: "0.25rem 0.6rem",
            borderRadius: "2px",
            fontSize: "0.7rem",
            color: "var(--primary)",
            pointerEvents: "none",
          }}
        >
          X: {mousePos.x} | Y: {mousePos.y}
        </div>
      </div>

      {/* Helper Legend */}
      <div
        className="font-mono"
        style={{
          fontSize: "0.7rem",
          color: "var(--text-muted)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <span style={{ color: "var(--primary)", fontWeight: 700 }}>GEOFENCE:</span> Click corners to draw perimeter polygon (min 3 pts).
        </div>
        <div>
          <span style={{ color: "var(--alert-critical)", fontWeight: 700 }}>TRIPWIRE:</span> Click start &amp; end points to set breach line.
        </div>
      </div>
    </div>
  );
};
