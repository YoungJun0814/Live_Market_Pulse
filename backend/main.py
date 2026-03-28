from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import FRONTEND_ORIGINS
from .models import SignalPayload
from .scheduler import HubScheduler
from .signal_queue import SignalQueue
from .websocket_server import SocketHub

signal_queue = SignalQueue()
socket_hub = SocketHub()
hub_scheduler = HubScheduler(signal_queue, socket_hub)


@asynccontextmanager
async def lifespan(app: FastAPI):
    hub_scheduler.start()
    yield
    hub_scheduler.shutdown()


app = FastAPI(
    title="Live Market Pulse Central Hub",
    version="0.1.0",
    description="Central Hub for market, RSS, and political sentiment aggregation",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/socket.io", socket_hub.mount_app())


@app.get("/", tags=["Info"])
async def root():
    return {
        "service": "Live Market Pulse Central Hub",
        "version": "0.1.0",
        "docs": "/docs",
        "socket_path": "/socket.io",
    }


@app.get("/health", tags=["Info"])
async def health():
    queue_snapshot = signal_queue.snapshot()
    last_payload = hub_scheduler.get_last_payload()
    return {
        "status": "ok",
        "scheduler_running": hub_scheduler.scheduler.running,
        "queue": queue_snapshot.model_dump(mode="json"),
        "last_sentiment_timestamp": (
            last_payload.timestamp.isoformat() if last_payload is not None else None
        ),
    }


@app.post("/api/signal", tags=["Signals"])
async def ingest_signal(payload: SignalPayload = Body(..., discriminator="source")):
    hub_scheduler.ingest(payload)
    update = await hub_scheduler.aggregate_and_publish()
    return JSONResponse(
        {
            "status": "accepted",
            "source": payload.source,
            "queue": signal_queue.snapshot().model_dump(mode="json"),
            "latest": update.model_dump(mode="json"),
        }
    )


@app.post("/api/demo/reset-neutral", tags=["Signals"])
async def reset_demo_neutral():
    update = await hub_scheduler.reset_demo_state()
    return JSONResponse(
        {
            "status": "accepted",
            "mode": "demo_reset_neutral",
            "queue": signal_queue.snapshot().model_dump(mode="json"),
            "latest": update.model_dump(mode="json"),
        }
    )


@app.post("/api/demo/push-risk-event", tags=["Signals"])
async def push_demo_risk_event():
    update = await hub_scheduler.inject_demo_risk_event()
    return JSONResponse(
        {
            "status": "accepted",
            "mode": "demo_risk_event",
            "queue": signal_queue.snapshot().model_dump(mode="json"),
            "latest": update.model_dump(mode="json"),
        }
    )


@app.post("/api/demo/push-rss-relief", tags=["Signals"])
async def push_demo_rss_relief():
    update = await hub_scheduler.inject_demo_rss_relief()
    return JSONResponse(
        {
            "status": "accepted",
            "mode": "demo_rss_relief",
            "queue": signal_queue.snapshot().model_dump(mode="json"),
            "latest": update.model_dump(mode="json"),
        }
    )


@app.get("/api/latest", tags=["Signals"])
async def latest_signal():
    payload = hub_scheduler.get_last_payload()
    if payload is None:
        payload = await hub_scheduler.aggregate_and_publish()
    return JSONResponse(payload.model_dump(mode="json"))


@app.get("/api/live_overlay", tags=["Signals"])
async def live_overlay():
    payload = hub_scheduler.get_last_payload()
    if payload is None:
        payload = await hub_scheduler.aggregate_and_publish()

    primary_driver = payload.drivers[0] if payload.drivers else None
    return JSONResponse(
        {
            "headline": primary_driver.signal if primary_driver is not None else payload.reasoning,
            "overall_sentiment": payload.overall_sentiment,
            "sentiment_score": payload.sentiment_score,
            "reasoning": payload.reasoning,
            "primary_source": primary_driver.source if primary_driver is not None else None,
            "timestamp": payload.timestamp.isoformat(),
        }
    )
