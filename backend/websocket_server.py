from __future__ import annotations

import time

import socketio

from .config import AUTOPILOT_COOLDOWN_SEC, AUTOPILOT_THRESHOLD, FRONTEND_ORIGINS
from .models import FocusRegionEvent, SentimentUpdate


class SocketHub:
    def __init__(self) -> None:
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=FRONTEND_ORIGINS + ["*"],
        )
        self._recent_focus_signatures: dict[str, float] = {}

        @self.sio.event
        async def connect(sid, environ, auth):
            return True

        @self.sio.event
        async def disconnect(sid):
            return None

    def mount_app(self) -> socketio.ASGIApp:
        return socketio.ASGIApp(self.sio, socketio_path="")

    async def emit_sentiment_update(self, payload: SentimentUpdate) -> None:
        await self.sio.emit("sentiment_update", payload.model_dump(mode="json"))

    async def emit_focus_region(self, payload: FocusRegionEvent) -> None:
        await self.sio.emit("focus_region", payload.model_dump(mode="json"))

    def should_trigger_autopilot(
        self,
        sentiment_score: int,
        has_location: bool,
        signature: str,
    ) -> bool:
        if not has_location or abs(sentiment_score) < AUTOPILOT_THRESHOLD:
            return False

        now = time.monotonic()
        cutoff = now - AUTOPILOT_COOLDOWN_SEC
        self._recent_focus_signatures = {
            key: ts
            for key, ts in self._recent_focus_signatures.items()
            if ts >= cutoff
        }

        if signature in self._recent_focus_signatures:
            return False

        self._recent_focus_signatures[signature] = now
        return True
