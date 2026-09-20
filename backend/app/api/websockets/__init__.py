"""WebSocket Gateway Package for IBVAP"""
from .alerts_ws import router as ws_router

__all__ = ["ws_router"]
