"""IBVAP API v1 Router Package"""
from fastapi import APIRouter
from .auth import router as auth_router
from .cameras import router as cameras_router
from .streams import router as streams_router
from .zones import router as zones_router
from .alerts import router as alerts_router
from .evidence import router as evidence_router
from .crossings import router as crossings_router
from .whitelist import router as whitelist_router
from .dashboard import router as dashboard_router
from .audit_logs import router as audit_logs_router
from .tracks import router as tracks_router
from .system import router as system_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & RBAC"])
api_router.include_router(cameras_router, prefix="/cameras", tags=["Camera Management"])
api_router.include_router(streams_router, prefix="/streams", tags=["Live Video Streaming Gateway"])
api_router.include_router(zones_router, prefix="/zones", tags=["Dynamic Zone Calibration"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Perimeter Security Alerts"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["Forensic Evidence Locker"])
api_router.include_router(crossings_router, prefix="/crossings", tags=["ANPR Checkpoint Vehicle Crossings"])
api_router.include_router(whitelist_router, prefix="/whitelist", tags=["Biometric & Vehicle Whitelist"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Tactical Dashboard Metrics"])
api_router.include_router(audit_logs_router, prefix="/audit-logs", tags=["Military Non-Repudiation Audit Logs"])
api_router.include_router(tracks_router, prefix="/tracks", tags=["Object Tracking & Kinematics"])
api_router.include_router(system_router, prefix="/system", tags=["System Storage & Maintenance"])

__all__ = ["api_router"]
