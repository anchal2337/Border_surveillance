"use client";

import React, { useState } from "react";
import { Vehicle } from "@/lib/types";
import { Truck, Plus, Trash2 } from "lucide-react";

interface VehicleRegistryProps {
  vehicles: Vehicle[];
  onRegisterVehicle: (payload: {
    license_plate: string;
    vehicle_type?: string;
    owner_name?: string;
    department?: string;
  }) => Promise<void>;
  onDeleteVehicle: (id: string) => Promise<void>;
}

export const VehicleRegistry: React.FC<VehicleRegistryProps> = ({
  vehicles,
  onRegisterVehicle,
  onDeleteVehicle,
}) => {
  const [plate, setPlate] = useState("");
  const [vehicleType, setVehicleType] = useState("car");
  const [ownerName, setOwnerName] = useState("Official Border Convoy");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanPlate = plate.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
    if (!cleanPlate) {
      setError("Please enter a valid alphanumeric license plate.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onRegisterVehicle({
        license_plate: cleanPlate,
        vehicle_type: vehicleType,
        owner_name: ownerName,
        department: "Border Patrol Command",
      });
      setPlate("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to register plate.");
    } finally {
      setSubmitting(false);
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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Truck size={18} style={{ color: "var(--primary)" }} />
          <div>
            <h3 className="font-display" style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "0.05em" }}>
              ANPR VEHICLE CHECKPOINT WHITELIST ({vehicles.length} REGISTERED PLATES)
            </h3>
            <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
              Authorized patrol convoys and official supply transports bypassing tripwire alerts.
            </div>
          </div>
        </div>
      </div>

      {/* Quick Add Form */}
      <form
        onSubmit={handleRegister}
        style={{
          backgroundColor: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          borderRadius: "2px",
          padding: "0.65rem",
          display: "flex",
          gap: "0.65rem",
          alignItems: "flex-end",
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1, minWidth: "150px" }}>
          <label style={{ display: "block", fontSize: "0.675rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.2rem" }} className="font-display">
            LICENSE PLATE
          </label>
          <input
            type="text"
            required
            value={plate}
            onChange={(e) => setPlate(e.target.value.toUpperCase())}
            placeholder="e.g. DL01AB1234"
            className="tactical-input font-mono"
            style={{ textTransform: "uppercase", fontSize: "0.85rem", fontWeight: 700 }}
          />
        </div>

        <div style={{ width: "130px" }}>
          <label style={{ display: "block", fontSize: "0.675rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.2rem" }} className="font-display">
            VEHICLE TYPE
          </label>
          <select
            value={vehicleType}
            onChange={(e) => setVehicleType(e.target.value)}
            className="tactical-input"
            style={{ height: "32px" }}
          >
            <option value="car">Car / Jeep</option>
            <option value="truck">Convoy Truck</option>
            <option value="motorcycle">Motorcycle</option>
            <option value="bus">Troop Carrier</option>
          </select>
        </div>

        <div style={{ flex: 1.2, minWidth: "160px" }}>
          <label style={{ display: "block", fontSize: "0.675rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.2rem" }} className="font-display">
            CONVOY / UNIT
          </label>
          <input
            type="text"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            placeholder="e.g. Official Border Convoy"
            className="tactical-input"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="tactical-btn tactical-btn-primary"
          style={{ height: "32px" }}
        >
          <Plus size={13} />
          <span>{submitting ? "ADDING..." : "ADD PLATE"}</span>
        </button>
      </form>

      {error && (
        <div style={{ color: "var(--alert-critical)", fontSize: "0.75rem" }}>
          {error}
        </div>
      )}

      {/* Plates Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.775rem" }}>
          <thead>
            <tr className="font-display" style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left", color: "var(--text-muted)", fontSize: "0.8rem", letterSpacing: "0.04em" }}>
              <th style={{ padding: "0.45rem", fontWeight: 700 }}>LICENSE PLATE</th>
              <th style={{ padding: "0.45rem", fontWeight: 700 }}>TYPE</th>
              <th style={{ padding: "0.45rem", fontWeight: 700 }}>OWNER / UNIT</th>
              <th style={{ padding: "0.45rem", fontWeight: 700 }}>STATUS</th>
              <th style={{ padding: "0.45rem", fontWeight: 700, textAlign: "right" }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}>
                  No authorized vehicle plates registered. Add plates using the form above.
                </td>
              </tr>
            ) : (
              vehicles.map((v) => (
                <tr
                  key={v.id}
                  style={{
                    borderBottom: "1px solid rgba(52, 56, 59, 0.4)",
                    backgroundColor: "transparent",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-card)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "0.45rem" }}>
                    <span
                      className="font-mono"
                      style={{
                        backgroundColor: "#000000",
                        border: "1px solid var(--primary)",
                        color: "var(--primary)",
                        padding: "0.15rem 0.45rem",
                        borderRadius: "2px",
                        fontWeight: 800,
                        fontSize: "0.8rem",
                      }}
                    >
                      {v.license_plate}
                    </span>
                  </td>
                  <td style={{ padding: "0.45rem", textTransform: "capitalize", color: "var(--text-main)" }}>
                    {v.vehicle_type}
                  </td>
                  <td style={{ padding: "0.45rem", color: "var(--text-muted)" }}>
                    {v.owner_name || "Official Transport"}
                  </td>
                  <td style={{ padding: "0.45rem" }}>
                    <span className="tactical-badge badge-success" style={{ fontSize: "0.625rem" }}>
                      AUTHORIZED
                    </span>
                  </td>
                  <td style={{ padding: "0.45rem", textAlign: "right" }}>
                    <button
                      onClick={() => onDeleteVehicle(v.id)}
                      className="tactical-btn tactical-btn-secondary"
                      style={{ padding: "0.2rem 0.45rem", color: "var(--alert-critical)" }}
                      title="Revoke License Plate"
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
