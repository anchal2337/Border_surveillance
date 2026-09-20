"use client";

import React, { useState, useRef } from "react";
import { Camera } from "@/lib/types";
import { uploadVideo, createCamera, connectCamera } from "@/lib/api";
import { PlusCircle, Upload, Video, X, Radio, FileVideo, HardDrive } from "lucide-react";

interface InjectVideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCameraInjected: (cam: Camera) => void;
}

export const InjectVideoModal: React.FC<InjectVideoModalProps> = ({
  isOpen,
  onClose,
  onCameraInjected,
}) => {
  const [activeTab, setActiveTab] = useState<"file" | "stream">("file");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // File Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileCamId, setFileCamId] = useState(`CAM-DRONE-${Math.floor(1000 + Math.random() * 9000)}`);
  const [fileCamName, setFileCamName] = useState("Tactical Sector Replay");
  const [fileSector, setFileSector] = useState("Sector 4");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stream URL Form State
  const [streamId, setStreamId] = useState(`CAM-RTSP-${Math.floor(100 + Math.random() * 900)}`);
  const [streamName, setStreamName] = useState("External RTSP Perimeter");
  const [streamSector, setStreamSector] = useState("Sector 1");
  const [streamSourceType, setStreamSourceType] = useState<"RTSP" | "FILE" | "WEBCAM" | "HTTP">("RTSP");
  const [streamUrl, setStreamUrl] = useState("rtsp://admin:pass@192.168.1.105:554/stream1");

  if (!isOpen) return null;

  const handleFileUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a valid CCTV video file (.mp4, .avi, .mkv, .mov).");
      return;
    }
    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("camera_id", fileCamId.trim());
      formData.append("camera_name", fileCamName.trim());
      formData.append("sector_zone", fileSector.trim());

      const newCam = await uploadVideo(formData);
      // Ensure camera is connected
      await connectCamera(newCam.id).catch(() => {});
      onCameraInjected(newCam);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to upload and inject video file.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStreamSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const newCam = await createCamera({
        id: streamId.trim(),
        name: streamName.trim(),
        sector_zone: streamSector.trim(),
        source_type: streamSourceType,
        stream_url: streamUrl.trim(),
        fps: 30.0,
        resolution: "1080x720",
        ai_pipeline: "ByteTrack + FRS + ANPR + DQN",
      });

      // Start ingestion worker
      await connectCamera(newCam.id).catch(() => {});
      onCameraInjected(newCam);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to register video stream source.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div className="tactical-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
        {/* Header */}
        <div
          style={{
            padding: "0.85rem 1.25rem",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <PlusCircle size={17} style={{ color: "var(--primary)" }} />
            <h3
              className="font-display"
              style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}
            >
              INJECT VIDEO SOURCE // PROVISION SENSOR
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={17} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border-color)" }}>
          <button
            onClick={() => { setActiveTab("file"); setError(null); }}
            style={{
              flex: 1,
              padding: "0.6rem",
              background: activeTab === "file" ? "rgba(214, 168, 79, 0.1)" : "transparent",
              border: "none",
              borderBottom: activeTab === "file" ? "2px solid var(--primary)" : "none",
              color: activeTab === "file" ? "var(--primary)" : "var(--text-muted)",
              fontFamily: "var(--font-display-var)",
              fontSize: "0.825rem",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.4rem",
            }}
          >
            <Upload size={14} />
            UPLOAD VIDEO FILE (.MP4 / .AVI)
          </button>
          <button
            onClick={() => { setActiveTab("stream"); setError(null); }}
            style={{
              flex: 1,
              padding: "0.6rem",
              background: activeTab === "stream" ? "rgba(214, 168, 79, 0.1)" : "transparent",
              border: "none",
              borderBottom: activeTab === "stream" ? "2px solid var(--primary)" : "none",
              color: activeTab === "stream" ? "var(--primary)" : "var(--text-muted)",
              fontFamily: "var(--font-display-var)",
              fontSize: "0.825rem",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.4rem",
            }}
          >
            <Radio size={14} />
            RTSP / WEBCAM / NETWORK STREAM
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              margin: "1rem 1.25rem 0",
              backgroundColor: "rgba(217, 92, 92, 0.15)",
              border: "1px solid var(--alert-critical)",
              padding: "0.5rem 0.75rem",
              fontSize: "0.775rem",
              color: "var(--alert-critical)",
              borderRadius: "2px",
            }}
          >
            {error}
          </div>
        )}

        {/* 1. FILE UPLOAD FORM */}
        {activeTab === "file" && (
          <form onSubmit={handleFileUploadSubmit} style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                SELECT CCTV / SURVEILLANCE VIDEO
              </label>
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed var(--border-color)",
                  padding: "1.5rem",
                  textAlign: "center",
                  cursor: "pointer",
                  backgroundColor: "var(--bg-card)",
                  borderRadius: "2px",
                  transition: "border-color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-color)")}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/avi,video/mkv,video/quicktime"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setSelectedFile(f);
                      if (!fileCamName || fileCamName === "Tactical Sector Replay") {
                        setFileCamName(f.name.replace(/\.[^/.]+$/, ""));
                      }
                    }
                  }}
                  style={{ display: "none" }}
                />

                {selectedFile ? (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.3rem" }}>
                    <FileVideo size={28} style={{ color: "var(--primary)" }} />
                    <span className="font-mono" style={{ fontSize: "0.8rem", color: "var(--text-main)", fontWeight: 700 }}>
                      {selectedFile.name}
                    </span>
                    <span className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.35rem" }}>
                    <Upload size={24} style={{ color: "var(--secondary)" }} />
                    <div className="font-display" style={{ fontSize: "0.825rem", fontWeight: 700, color: "var(--text-main)" }}>
                      CLICK OR DROP VIDEO FILE HERE
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      Supported formats: .MP4, .AVI, .MKV, .MOV (Auto-loops for continuous testing)
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  CAMERA CALLSIGN / ID
                </label>
                <input
                  type="text"
                  value={fileCamId}
                  onChange={(e) => setFileCamId(e.target.value)}
                  className="tactical-input font-mono"
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  SECTOR ZONE
                </label>
                <input
                  type="text"
                  value={fileSector}
                  onChange={(e) => setFileSector(e.target.value)}
                  className="tactical-input"
                  required
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                CHANNEL NAME / DESCRIPTION
              </label>
              <input
                type="text"
                value={fileCamName}
                onChange={(e) => setFileCamName(e.target.value)}
                className="tactical-input"
                required
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.6rem", marginTop: "0.5rem" }}>
              <button type="button" onClick={onClose} className="tactical-btn tactical-btn-secondary">
                CANCEL
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !selectedFile}
                className="tactical-btn tactical-btn-primary"
              >
                {isSubmitting ? "UPLOADING & INGESTING..." : "INJECT & START INFERENCE"}
              </button>
            </div>
          </form>
        )}

        {/* 2. STREAM URL FORM */}
        {activeTab === "stream" && (
          <form onSubmit={handleStreamSubmit} style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  SOURCE PROTOCOL
                </label>
                <select
                  value={streamSourceType}
                  onChange={(e) => setStreamSourceType(e.target.value as any)}
                  className="tactical-input font-mono"
                >
                  <option value="RTSP">RTSP (H.264 / ONVIF)</option>
                  <option value="FILE">LOCAL FILE PATH</option>
                  <option value="WEBCAM">WEBCAM (DEVICE 0/1)</option>
                  <option value="HTTP">HTTP MJPEG STREAM</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  CAMERA ID
                </label>
                <input
                  type="text"
                  value={streamId}
                  onChange={(e) => setStreamId(e.target.value)}
                  className="tactical-input font-mono"
                  required
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                STREAM URI / DEVICE INDEX / FILE PATH
              </label>
              <input
                type="text"
                value={streamUrl}
                onChange={(e) => setStreamUrl(e.target.value)}
                placeholder="rtsp://admin:pass@ip:554/stream or 0 for USB Webcam or data/uploads/video.mp4"
                className="tactical-input font-mono"
                required
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  CHANNEL NAME
                </label>
                <input
                  type="text"
                  value={streamName}
                  onChange={(e) => setStreamName(e.target.value)}
                  className="tactical-input"
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                  SECTOR ZONE
                </label>
                <input
                  type="text"
                  value={streamSector}
                  onChange={(e) => setStreamSector(e.target.value)}
                  className="tactical-input"
                  required
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.6rem", marginTop: "0.5rem" }}>
              <button type="button" onClick={onClose} className="tactical-btn tactical-btn-secondary">
                CANCEL
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="tactical-btn tactical-btn-primary"
              >
                {isSubmitting ? "PROVISIONING..." : "CONNECT SENSOR"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
