"use client";

import React, { useState } from "react";
import { X, Lock, User, ShieldAlert, Key } from "lucide-react";
import { login } from "@/lib/api";
import { AuthResponse } from "@/lib/types";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: AuthResponse) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const user = await login(username, password);
      onSuccess(user);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  const setPreset = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="tactical-modal-backdrop" onClick={onClose}>
      <div className="tactical-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "440px" }}>
        {/* Modal Header */}
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
            <Lock size={18} style={{ color: "var(--primary)" }} />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.04em", color: "var(--text-main)" }}>
              SENTRY OPERATOR ACCESS
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          {error && (
            <div
              style={{
                backgroundColor: "rgba(217, 92, 92, 0.15)",
                border: "1px solid var(--alert-critical)",
                borderRadius: "4px",
                padding: "0.6rem 0.8rem",
                display: "flex",
                alignItems: "center",
                gap: "0.6rem",
                color: "var(--alert-critical)",
                fontSize: "0.8rem",
              }}
            >
              <ShieldAlert size={16} />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              OPERATOR IDENTIFIER / USERNAME
            </label>
            <div style={{ position: "relative" }}>
              <User size={15} style={{ position: "absolute", left: "10px", top: "11px", color: "var(--text-muted)" }} />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="tactical-input"
                style={{ paddingLeft: "32px" }}
                placeholder="e.g. admin"
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              SECURITY PASSCODE
            </label>
            <div style={{ position: "relative" }}>
              <Key size={15} style={{ position: "absolute", left: "10px", top: "11px", color: "var(--text-muted)" }} />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="tactical-input"
                style={{ paddingLeft: "32px" }}
                placeholder="••••••••"
              />
            </div>
          </div>

          {/* Quick Presets */}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
            <button
              type="button"
              onClick={() => setPreset("admin", "admin123")}
              className="tactical-btn tactical-btn-secondary"
              style={{ fontSize: "0.7rem", padding: "0.3rem 0.5rem" }}
            >
              Admin (Commander)
            </button>
            <button
              type="button"
              onClick={() => setPreset("operator", "operator123")}
              className="tactical-btn tactical-btn-secondary"
              style={{ fontSize: "0.7rem", padding: "0.3rem 0.5rem" }}
            >
              Operator 1
            </button>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
            <button type="button" onClick={onClose} className="tactical-btn tactical-btn-secondary">
              CANCEL
            </button>
            <button type="submit" disabled={loading} className="tactical-btn tactical-btn-primary">
              {loading ? "AUTHENTICATING..." : "VERIFY & ENTER"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
