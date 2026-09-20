"use client";

import React, { useState, useRef } from "react";
import { X, Upload, Camera, Check, ShieldCheck, Sun } from "lucide-react";
import { uploadPersonnelPhoto } from "@/lib/api";
import { Personnel } from "@/lib/types";

interface FaceEnrollModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEnrolled: (personnel: Personnel) => void;
}

export const FaceEnrollModal: React.FC<FaceEnrollModalProps> = ({
  isOpen,
  onClose,
  onEnrolled,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fullName, setFullName] = useState("");
  const [designation, setDesignation] = useState("Border Patrol Guard");
  const [badgeNumber, setBadgeNumber] = useState("");
  const [department, setDepartment] = useState("Perimeter Security");
  const [enhance, setEnhance] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPhotoFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!photoFile) {
      setError("Please select or capture an officer portrait photo.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("photo", photoFile);
    formData.append("full_name", fullName);
    formData.append("designation", designation);
    if (badgeNumber) formData.append("badge_number", badgeNumber);
    formData.append("department", department);
    formData.append("enhance", enhance ? "true" : "false");

    try {
      const res = await uploadPersonnelPhoto(formData);
      onEnrolled(res);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to enroll personnel.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div className="tactical-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "540px" }}>
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Camera size={18} style={{ color: "var(--primary)" }} />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.04em" }}>
              BIOMETRIC FACE ENROLLMENT (FRS)
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          {error && (
            <div
              style={{
                backgroundColor: "rgba(217, 92, 92, 0.15)",
                border: "1px solid var(--alert-critical)",
                borderRadius: "4px",
                padding: "0.6rem 0.8rem",
                color: "var(--alert-critical)",
                fontSize: "0.775rem",
              }}
            >
              {error}
            </div>
          )}

          {/* Photo Dropzone / Preview */}
          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              OFFICER PORTRAIT PHOTO
            </label>

            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: "2px dashed var(--border-color)",
                borderRadius: "6px",
                padding: "1.25rem",
                textAlign: "center",
                cursor: "pointer",
                backgroundColor: "var(--bg-card)",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-color)")}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />

              {previewUrl ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={previewUrl}
                    alt="Preview"
                    style={{ width: "110px", height: "110px", objectFit: "cover", borderRadius: "6px", border: "1px solid var(--primary)" }}
                  />
                  <span style={{ fontSize: "0.725rem", color: "var(--primary)", fontWeight: 600 }}>
                    Click to change photo
                  </span>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.4rem" }}>
                  <Upload size={28} style={{ color: "var(--secondary)" }} />
                  <div style={{ fontSize: "0.825rem", fontWeight: 700, color: "var(--text-main)" }}>
                    Click to browse or drop officer photo
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    JPEG / PNG format • MTCNN will detect face and generate 512-D vector
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Auto-CLAHE Toggle */}
          <div
            onClick={() => setEnhance(!enhance)}
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: "4px",
              padding: "0.6rem 0.75rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Sun size={16} style={{ color: enhance ? "var(--primary)" : "var(--text-muted)" }} />
              <div>
                <div style={{ fontSize: "0.775rem", fontWeight: 700, color: "var(--text-main)" }}>
                  Auto-CLAHE Illumination Normalization
                </div>
                <div style={{ fontSize: "0.675rem", color: "var(--text-muted)" }}>
                  Enhances low-light or harsh border sun portraits before neural embedding
                </div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={enhance}
              onChange={() => {}}
              style={{ accentColor: "var(--primary)", width: "16px", height: "16px" }}
            />
          </div>

          {/* Form Fields */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                FULL NAME *
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Major Vikram Singh"
                className="tactical-input"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                RANK / DESIGNATION *
              </label>
              <input
                type="text"
                required
                value={designation}
                onChange={(e) => setDesignation(e.target.value)}
                placeholder="e.g. Commanding Officer"
                className="tactical-input"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                BADGE NUMBER
              </label>
              <input
                type="text"
                value={badgeNumber}
                onChange={(e) => setBadgeNumber(e.target.value)}
                placeholder="e.g. BOP-13JAK"
                className="tactical-input font-mono"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.725rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.3rem" }}>
                ASSIGNED UNIT / DEPARTMENT
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Quick Reaction Team"
                className="tactical-input"
              />
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
            <button type="button" onClick={onClose} className="tactical-btn tactical-btn-secondary">
              CANCEL
            </button>
            <button type="submit" disabled={submitting} className="tactical-btn tactical-btn-primary">
              <ShieldCheck size={14} />
              <span>{submitting ? "ENROLLING BIOMETRICS..." : "ENROLL IN WHITELIST"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
