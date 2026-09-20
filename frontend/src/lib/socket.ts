import { Alert, TelemetryData } from "./types";
import { WS_BASE_URL } from "./api";
import { playBreachAlarm, playSonarPing } from "./audio";

type AlertCallback = (alert: Alert) => void;
type InitialAlertsCallback = (alerts: Alert[]) => void;
type TelemetryCallback = (telemetry: TelemetryData) => void;

class SentrySocketManager {
  private alertSocket: WebSocket | null = null;
  private telemetrySocket: WebSocket | null = null;
  private alertListeners: Set<AlertCallback> = new Set();
  private initialListeners: Set<InitialAlertsCallback> = new Set();
  private telemetryListeners: Set<TelemetryCallback> = new Set();
  private alertPingInterval: NodeJS.Timeout | null = null;
  private telemetryPingInterval: NodeJS.Timeout | null = null;
  private isConnectingAlert = false;
  private isConnectingTelemetry = false;

  public connectAlerts() {
    if (typeof window === "undefined") return;
    if (this.alertSocket && (this.alertSocket.readyState === WebSocket.OPEN || this.alertSocket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (this.isConnectingAlert) return;
    this.isConnectingAlert = true;

    try {
      const url = `${WS_BASE_URL}/ws/alerts`;
      this.alertSocket = new WebSocket(url);

      this.alertSocket.onopen = () => {
        this.isConnectingAlert = false;
        // Start ping loop
        if (this.alertPingInterval) clearInterval(this.alertPingInterval);
        this.alertPingInterval = setInterval(() => {
          if (this.alertSocket?.readyState === WebSocket.OPEN) {
            this.alertSocket.send(JSON.stringify({ action: "PING" }));
          }
        }, 10000);
      };

      this.alertSocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === "INITIAL_ALERT_BUFFER" && Array.isArray(payload.alerts)) {
            this.initialListeners.forEach((cb) => cb(payload.alerts));
          } else if (payload.event === "NEW_ALERT" && payload.data) {
            const alert = payload.data as Alert;
            if (alert.severity === "CRITICAL") {
              playBreachAlarm();
            } else {
              playSonarPing();
            }
            this.alertListeners.forEach((cb) => cb(alert));
          }
        } catch {
          // ignore
        }
      };

      this.alertSocket.onclose = () => {
        this.isConnectingAlert = false;
        if (this.alertPingInterval) clearInterval(this.alertPingInterval);
        setTimeout(() => this.connectAlerts(), 4000);
      };

      this.alertSocket.onerror = () => {
        this.alertSocket?.close();
      };
    } catch {
      this.isConnectingAlert = false;
      setTimeout(() => this.connectAlerts(), 5000);
    }
  }

  public connectTelemetry() {
    if (typeof window === "undefined") return;
    if (this.telemetrySocket && (this.telemetrySocket.readyState === WebSocket.OPEN || this.telemetrySocket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (this.isConnectingTelemetry) return;
    this.isConnectingTelemetry = true;

    try {
      const url = `${WS_BASE_URL}/ws/telemetry`;
      this.telemetrySocket = new WebSocket(url);

      this.telemetrySocket.onopen = () => {
        this.isConnectingTelemetry = false;
        if (this.telemetryPingInterval) clearInterval(this.telemetryPingInterval);
        this.telemetryPingInterval = setInterval(() => {
          if (this.telemetrySocket?.readyState === WebSocket.OPEN) {
            this.telemetrySocket.send(JSON.stringify({ action: "PING" }));
          }
        }, 10000);
      };

      this.telemetrySocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === "STREAM_TELEMETRY" && payload.data) {
            this.telemetryListeners.forEach((cb) => cb(payload.data));
          }
        } catch {
          // ignore
        }
      };

      this.telemetrySocket.onclose = () => {
        this.isConnectingTelemetry = false;
        if (this.telemetryPingInterval) clearInterval(this.telemetryPingInterval);
        setTimeout(() => this.connectTelemetry(), 4000);
      };

      this.telemetrySocket.onerror = () => {
        this.telemetrySocket?.close();
      };
    } catch {
      this.isConnectingTelemetry = false;
      setTimeout(() => this.connectTelemetry(), 5000);
    }
  }

  public onAlert(cb: AlertCallback): () => void {
    this.alertListeners.add(cb);
    this.connectAlerts();
    return () => this.alertListeners.delete(cb);
  }

  public onInitialBuffer(cb: InitialAlertsCallback): () => void {
    this.initialListeners.add(cb);
    this.connectAlerts();
    return () => this.initialListeners.delete(cb);
  }

  public onTelemetry(cb: TelemetryCallback): () => void {
    this.telemetryListeners.add(cb);
    this.connectTelemetry();
    return () => this.telemetryListeners.delete(cb);
  }
}

export const sentrySocket = new SentrySocketManager();
