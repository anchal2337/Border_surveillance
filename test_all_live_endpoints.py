import asyncio
import io
import json
import time
import cv2
import numpy as np
import httpx
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"

results = []

def record(category, method, path, status, success, detail=""):
    results.append({
        "category": category,
        "method": method,
        "path": path,
        "status": status,
        "success": success,
        "detail": detail[:80] + ("..." if len(detail) > 80 else ""),
    })
    mark = "PASS" if success else "FAIL"
    print(f"[{mark:4}] {method:6} {path:<40} -> Status: {status} | {detail[:60]}")


async def main():
    print("=" * 80)
    print("      IBVAP LIVE SYSTEM END-TO-END ENDPOINT VERIFICATION SUITE")
    print(f"      Target: {BASE_URL}  |  WebSockets: {WS_BASE}")
    print("=" * 80)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # ---------------------------------------------------------------------
        # 1. System & Health Probes
        # ---------------------------------------------------------------------
        r = await client.get("/")
        record("System", "GET", "/", r.status_code, r.status_code == 200, r.json().get("system", ""))

        r = await client.get("/health")
        record("System", "GET", "/health", r.status_code, r.status_code == 200, r.json().get("status", ""))

        # ---------------------------------------------------------------------
        # 2. Authentication & User Administration
        # ---------------------------------------------------------------------
        r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        token_data = r.json()
        token = token_data.get("access_token", "")
        record("Auth", "POST", "/api/v1/auth/login", r.status_code, r.status_code == 200 and bool(token), f"Role: {token_data.get('role')}")

        headers = {"Authorization": f"Bearer {token}"}

        r = await client.get("/api/v1/auth/me", headers=headers)
        record("Auth", "GET", "/api/v1/auth/me", r.status_code, r.status_code == 200, f"User: {r.json().get('username')}")

        r = await client.get("/api/v1/auth/users", headers=headers)
        users = r.json()
        record("Auth", "GET", "/api/v1/auth/users", r.status_code, r.status_code == 200, f"Found {len(users)} users")

        test_uname = f"test_op_{int(time.time())}"
        r = await client.post("/api/v1/auth/users", headers=headers, json={
            "username": test_uname,
            "password": "Password123!",
            "email": f"{test_uname}@ibvap.internal",
            "full_name": "Temporary Test Operator",
            "role": "OPERATOR",
            "badge_number": "TMP-01"
        })
        created_user = r.json()
        created_user_id = created_user.get("id")
        record("Auth", "POST", "/api/v1/auth/users", r.status_code, r.status_code == 201, f"Created {test_uname}")

        if created_user_id:
            r = await client.patch(f"/api/v1/auth/users/{created_user_id}/role", headers=headers, json={"role": "COMMANDER"})
            record("Auth", "PATCH", f"/api/v1/auth/users/{created_user_id}/role", r.status_code, r.status_code == 200, f"Promoted to {r.json().get('role')}")

        # ---------------------------------------------------------------------
        # 3. Camera Management
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/cameras", headers=headers)
        cams = r.json()
        record("Cameras", "GET", "/api/v1/cameras", r.status_code, r.status_code == 200, f"{len(cams)} cameras listed")

        test_cam_id = f"CAM-TEST-{int(time.time())%10000}"
        r = await client.post("/api/v1/cameras", headers=headers, json={
            "id": test_cam_id,
            "name": "Live Synthetic Sentry Post",
            "sector_zone": "Sector 9",
            "source_type": "RTSP",
            "stream_url": "rtsp://127.0.0.1:8554/live"
        })
        record("Cameras", "POST", "/api/v1/cameras", r.status_code, r.status_code == 201, f"Provisioned {test_cam_id}")

        r = await client.post(f"/api/v1/cameras/{test_cam_id}/connect", headers=headers)
        record("Cameras", "POST", f"/api/v1/cameras/{test_cam_id}/connect", r.status_code, r.status_code == 200, r.json().get("message", ""))

        # Allow worker 0.5s to start and render frame
        await asyncio.sleep(0.5)

        # ---------------------------------------------------------------------
        # 4. Live Streaming Gateway & Telemetry
        # ---------------------------------------------------------------------
        r = await client.get(f"/api/v1/streams/{test_cam_id}/telemetry", headers=headers)
        telem = r.json()
        has_matrix = "model_confidences" in telem
        record("Streams", "GET", f"/api/v1/streams/{test_cam_id}/telemetry", r.status_code, r.status_code == 200 and has_matrix, f"FPS: {telem.get('fps')} | Matrix: {list(telem.get('model_confidences', {}).keys())}")

        r = await client.get(f"/api/v1/streams/{test_cam_id}/snapshot")
        is_jpeg = r.headers.get("content-type") == "image/jpeg" and len(r.content) > 1000
        record("Streams", "GET", f"/api/v1/streams/{test_cam_id}/snapshot", r.status_code, r.status_code == 200 and is_jpeg, f"Size: {len(r.content)} bytes JPEG")

        # Stream feed (read first chunk)
        feed_ok = False
        try:
            async with client.stream("GET", f"/api/v1/streams/{test_cam_id}/feed") as response:
                if response.status_code == 200 and "multipart/x-mixed-replace" in response.headers.get("content-type", ""):
                    async for chunk in response.aiter_bytes():
                        if len(chunk) > 100:
                            feed_ok = True
                            break
        except Exception:
            pass
        record("Streams", "GET", f"/api/v1/streams/{test_cam_id}/feed", 200 if feed_ok else 500, feed_ok, "Multipart MJPEG active frame stream")

        # ---------------------------------------------------------------------
        # 5. Dynamic Zone Calibration
        # ---------------------------------------------------------------------
        r = await client.get(f"/api/v1/zones/{test_cam_id}", headers=headers)
        record("Zones", "GET", f"/api/v1/zones/{test_cam_id}", r.status_code, r.status_code == 200, f"Zones: {len(r.json())}")

        r = await client.post(f"/api/v1/zones/{test_cam_id}", headers=headers, json={
            "camera_id": test_cam_id,
            "geofence": [[100, 150], [500, 150], [500, 450], [100, 450]],
            "tripwire": [[120, 300], [480, 300]]
        })
        record("Zones", "POST", f"/api/v1/zones/{test_cam_id}", r.status_code, r.status_code == 200, r.json().get("message", ""))

        r = await client.post(f"/api/v1/cameras/{test_cam_id}/disconnect", headers=headers)
        record("Cameras", "POST", f"/api/v1/cameras/{test_cam_id}/disconnect", r.status_code, r.status_code == 200, "Worker stopped")

        # ---------------------------------------------------------------------
        # 6. Perimeter Security Alerts
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/alerts?limit=10", headers=headers)
        alerts = r.json()
        record("Alerts", "GET", "/api/v1/alerts", r.status_code, r.status_code == 200, f"Retrieved {len(alerts)} alerts")

        r = await client.get("/api/v1/alerts/summary", headers=headers)
        summary = r.json()
        record("Alerts", "GET", "/api/v1/alerts/summary", r.status_code, r.status_code == 200, f"Total: {summary.get('total_alerts')} | Unacked: {summary.get('unacknowledged')}")

        if alerts:
            first_alert_id = alerts[0]["id"]
            r = await client.get(f"/api/v1/alerts/{first_alert_id}", headers=headers)
            record("Alerts", "GET", f"/api/v1/alerts/{first_alert_id}", r.status_code, r.status_code == 200, f"Type: {r.json().get('alert_type')}")

            r = await client.post(f"/api/v1/alerts/{first_alert_id}/acknowledge", headers=headers, json={"resolution_notes": "Verified by automated audit drone."})
            record("Alerts", "POST", f"/api/v1/alerts/{first_alert_id}/acknowledge", r.status_code, r.status_code == 200, f"Ack: {r.json().get('is_acknowledged')}")

        # ---------------------------------------------------------------------
        # 7. Forensic Evidence Locker
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/evidence?limit=10", headers=headers)
        ev_list = r.json()
        record("Evidence", "GET", "/api/v1/evidence", r.status_code, r.status_code == 200, f"Retrieved {len(ev_list)} cases")

        if ev_list:
            first_ev_id = ev_list[0]["id"]
            r = await client.get(f"/api/v1/evidence/{first_ev_id}", headers=headers)
            record("Evidence", "GET", f"/api/v1/evidence/{first_ev_id}", r.status_code, r.status_code == 200, f"Event: {r.json().get('event')}")

            r = await client.post(f"/api/v1/evidence/{first_ev_id}/verify", headers=headers)
            record("Evidence", "POST", f"/api/v1/evidence/{first_ev_id}/verify", r.status_code, r.status_code == 200, f"Verified: {r.json().get('is_valid')}")

            r = await client.patch(f"/api/v1/evidence/{first_ev_id}/status", headers=headers, json={"status": "INVESTIGATING"})
            record("Evidence", "PATCH", f"/api/v1/evidence/{first_ev_id}/status", r.status_code, r.status_code == 200, f"Status: {r.json().get('status')}")

        # ---------------------------------------------------------------------
        # 8. ANPR Checkpoint Vehicle Crossings
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/crossings?limit=10", headers=headers)
        crossings = r.json()
        record("Crossings", "GET", "/api/v1/crossings", r.status_code, r.status_code == 200, f"Retrieved {len(crossings)} crossings")

        r = await client.get("/api/v1/crossings/summary", headers=headers)
        cross_sum = r.json()
        record("Crossings", "GET", "/api/v1/crossings/summary", r.status_code, r.status_code == 200, f"Total: {cross_sum.get('total_crossings')} | Auth: {cross_sum.get('whitelisted_count')}")

        if crossings:
            first_cid = crossings[0]["id"]
            r = await client.get(f"/api/v1/crossings/{first_cid}", headers=headers)
            record("Crossings", "GET", f"/api/v1/crossings/{first_cid}", r.status_code, r.status_code == 200, f"Plate: {r.json().get('license_plate')}")

        # ---------------------------------------------------------------------
        # 9. Biometric & Vehicle Whitelist
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/whitelist/personnel", headers=headers)
        record("Whitelist", "GET", "/api/v1/whitelist/personnel", r.status_code, r.status_code == 200, f"Personnel: {len(r.json())}")

        dummy_emb = [0.05] * 512
        r = await client.post("/api/v1/whitelist/personnel", headers=headers, json={
            "full_name": f"Officer Raw {int(time.time())}",
            "designation": "Border Patrol Guard",
            "badge_number": "BPG-99",
            "face_embedding": dummy_emb
        })
        raw_person = r.json()
        record("Whitelist", "POST", "/api/v1/whitelist/personnel", r.status_code, r.status_code == 201, f"Enrolled {raw_person.get('full_name')}")

        # Photo upload with CLAHE
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.circle(img, (100, 100), 45, (220, 220, 220), -1)
        _, enc = cv2.imencode(".jpg", img)
        photo_bytes = enc.tobytes()

        r = await client.post(
            "/api/v1/whitelist/personnel/upload-photo",
            headers=headers,
            files={"photo": ("portrait.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
            data={
                "full_name": f"Major Vikram {int(time.time())}",
                "designation": "Commanding Officer",
                "badge_number": "CO-13JAK",
                "department": "Special Perimeter Force",
                "enhance": "true"
            }
        )
        photo_person = r.json()
        record("Whitelist", "POST", "/api/v1/whitelist/personnel/upload-photo", r.status_code, r.status_code == 201, f"Photo URL: {photo_person.get('photo_path')}")

        if raw_person.get("id"):
            r = await client.delete(f"/api/v1/whitelist/personnel/{raw_person['id']}", headers=headers)
            record("Whitelist", "DELETE", f"/api/v1/whitelist/personnel/{raw_person['id']}", r.status_code, r.status_code == 200, "Revoked personnel")

        r = await client.get("/api/v1/whitelist/vehicles", headers=headers)
        record("Whitelist", "GET", "/api/v1/whitelist/vehicles", r.status_code, r.status_code == 200, f"Vehicles: {len(r.json())}")

        test_plate = f"TEST{int(time.time())%10000}X"
        r = await client.post("/api/v1/whitelist/vehicles", headers=headers, json={
            "license_plate": test_plate,
            "vehicle_type": "jeep",
            "owner_name": "Perimeter Patrol Convoy",
            "department": "Quick Reaction Team"
        })
        v_rec = r.json()
        record("Whitelist", "POST", "/api/v1/whitelist/vehicles", r.status_code, r.status_code == 201, f"Registered plate {test_plate}")

        if v_rec.get("id"):
            r = await client.delete(f"/api/v1/whitelist/vehicles/{v_rec['id']}", headers=headers)
            record("Whitelist", "DELETE", f"/api/v1/whitelist/vehicles/{v_rec['id']}", r.status_code, r.status_code == 200, "Revoked vehicle")

        r = await client.post("/api/v1/whitelist/sync", headers=headers)
        record("Whitelist", "POST", "/api/v1/whitelist/sync", r.status_code, r.status_code == 200, r.json().get("message", ""))

        # ---------------------------------------------------------------------
        # 10. Dashboard & C2 Overview
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/dashboard/summary", headers=headers)
        d_sum = r.json()
        record("Dashboard", "GET", "/api/v1/dashboard/summary", r.status_code, r.status_code == 200, f"Active cams: {d_sum.get('active_cameras')} | Incidents: {d_sum.get('total_incidents')}")

        # ---------------------------------------------------------------------
        # 11. Object Tracking & Kinematics
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/tracks/active", headers=headers)
        active_t = r.json()
        record("Tracking", "GET", "/api/v1/tracks/active", r.status_code, r.status_code == 200, f"Active tracks count: {len(active_t)}")

        r = await client.get("/api/v1/tracks/CAM-01/history?limit=10", headers=headers)
        hist_t = r.json()
        record("Tracking", "GET", "/api/v1/tracks/CAM-01/history", r.status_code, r.status_code == 200, f"Historical tracks: {len(hist_t)}")

        if hist_t:
            first_sess_id = hist_t[0]["id"]
            r = await client.get(f"/api/v1/tracks/sessions/{first_sess_id}", headers=headers)
            record("Tracking", "GET", f"/api/v1/tracks/sessions/{first_sess_id}", r.status_code, r.status_code == 200, f"Track #{r.json().get('track_number')} | Threat: {r.json().get('max_threat_score')}%")

        # ---------------------------------------------------------------------
        # 12. Military Non-Repudiation Audit Logs
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/audit-logs?limit=10", headers=headers)
        audits = r.json()
        record("Audit", "GET", "/api/v1/audit-logs", r.status_code, r.status_code == 200, f"Total audit logs retrieved: {len(audits)}")

        if audits:
            first_aid = audits[0]["id"]
            r = await client.get(f"/api/v1/audit-logs/{first_aid}", headers=headers)
            record("Audit", "GET", f"/api/v1/audit-logs/{first_aid}", r.status_code, r.status_code == 200, f"Action: {r.json().get('action')}")

        # ---------------------------------------------------------------------
        # 13. System Storage & Air-Gapped Maintenance
        # ---------------------------------------------------------------------
        r = await client.get("/api/v1/system/storage", headers=headers)
        stor = r.json()
        record("System", "GET", "/api/v1/system/storage", r.status_code, r.status_code == 200, f"Free: {round(stor.get('free_disk_bytes',0)/(1024**3), 2)} GB | Healthy: {stor.get('is_healthy')}")

        r = await client.post("/api/v1/system/prune", headers=headers, json={"max_age_days": 60})
        record("System", "POST", "/api/v1/system/prune", r.status_code, r.status_code == 200, r.json().get("message", ""))

    # -------------------------------------------------------------------------
    # 14. Real-Time WebSockets
    # -------------------------------------------------------------------------
    ws_alerts_ok = False
    try:
        async with websockets.connect(f"{WS_BASE}/ws/alerts") as ws:
            await ws.send(json.dumps({"action": "PING"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            if data.get("event") == "PONG" or data.get("status") == "LIVE":
                ws_alerts_ok = True
    except Exception as e:
        pass
    record("WebSockets", "WS", "/ws/alerts", 101 if ws_alerts_ok else 500, ws_alerts_ok, "Real-time incident alert broadcast stream")

    ws_telem_ok = False
    try:
        async with websockets.connect(f"{WS_BASE}/ws/telemetry") as ws:
            await ws.send(json.dumps({"action": "PING"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            if data.get("event") == "PONG" or data.get("status") == "LIVE":
                ws_telem_ok = True
    except Exception as e:
        pass
    record("WebSockets", "WS", "/ws/telemetry", 101 if ws_telem_ok else 500, ws_telem_ok, "1Hz tactical HUD telemetry & confidence stream")

    # -------------------------------------------------------------------------
    # Final Scorecard
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("                     VERIFICATION SCORECARD SUMMARY")
    print("=" * 80)
    total_endpoints = len(results)
    passed_endpoints = sum(1 for r in results if r["success"])
    failed_endpoints = total_endpoints - passed_endpoints

    print(f"Total Endpoints Tested : {total_endpoints}")
    print(f"Passed Successfully    : {passed_endpoints} ({round(passed_endpoints/total_endpoints*100, 1)}%)")
    print(f"Failed                 : {failed_endpoints}")
    print("=" * 80)

    if failed_endpoints == 0:
        print(">>> ALL API ENDPOINTS & WEBSOCKETS ARE 100% OPERATIONAL ON LIVE SERVER! <<<")
    else:
        print(f">>> {failed_endpoints} ENDPOINT(S) RETURNED ERRORS. INSPECT DETAILS ABOVE. <<<")


if __name__ == "__main__":
    asyncio.run(main())
