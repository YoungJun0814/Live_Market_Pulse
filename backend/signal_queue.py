from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from .config import QUEUE_TTL_SECONDS
from .models import MarketDataSignal, NewsStreamSignal, PoliticianSignal, QueueSnapshot

QueuedSignal = NewsStreamSignal | PoliticianSignal | MarketDataSignal


@dataclass(slots=True)
class QueuedItem:
    payload: QueuedSignal
    received_at: datetime


class SignalQueue:
    def __init__(self, ttl_seconds: int = QUEUE_TTL_SECONDS) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, deque[QueuedItem]] = {
            "news_stream": deque(),
            "politician": deque(),
            "market_data": deque(),
        }
        self._lock = RLock()

    def add(self, signal: QueuedSignal) -> None:
        with self._lock:
            self._expire_locked()
            self._items[signal.source].append(
                QueuedItem(payload=signal, received_at=datetime.now(UTC))
            )

    def expire(self) -> None:
        with self._lock:
            self._expire_locked()

    def clear(self) -> None:
        with self._lock:
            for queue in self._items.values():
                queue.clear()

    def latest_by_source(self) -> dict[str, QueuedSignal]:
        with self._lock:
            self._expire_locked()
            return {
                source: queue[-1].payload
                for source, queue in self._items.items()
                if queue
            }

    def latest_received_at_by_source(self) -> dict[str, datetime | None]:
        with self._lock:
            self._expire_locked()
            return {
                source: (queue[-1].received_at if queue else None)
                for source, queue in self._items.items()
            }

    def snapshot(self) -> QueueSnapshot:
        with self._lock:
            self._expire_locked()
            latest = {
                source: (queue[-1].received_at if queue else None)
                for source, queue in self._items.items()
            }
            counts = {source: len(queue) for source, queue in self._items.items()}
        return QueueSnapshot(counts=counts, latest_timestamps=latest)

    def _expire_locked(self) -> None:
        cutoff = datetime.now(UTC) - self.ttl
        for queue in self._items.values():
            while queue and queue[0].received_at < cutoff:
                queue.popleft()
