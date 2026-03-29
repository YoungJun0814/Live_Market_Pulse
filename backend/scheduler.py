from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .config import (
    COUNTRY_PROFILE_PATH,
    FALLBACK_WEIGHTS,
    SCHEDULER_INTERVAL_SECONDS,
    SENTIMENT_THRESHOLDS,
    SOURCE_WEIGHTS,
)
from .models import (
    CountryData,
    DataFreshness,
    Driver,
    FocusRegionEvent,
    MarketDataSignal,
    MarketSnapshot,
    NewsStreamSignal,
    PoliticianSignal,
    SentimentUpdate,
)
from .signal_queue import QueuedSignal, SignalQueue
from .websocket_server import SocketHub


class HubScheduler:
    def __init__(self, queue: SignalQueue, socket_hub: SocketHub) -> None:
        self.queue = queue
        self.socket_hub = socket_hub
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.scheduler.add_job(
            self.run_batch_sync,
            "interval",
            seconds=SCHEDULER_INTERVAL_SECONDS,
            id="signal-batch",
            replace_existing=True,
        )
        self.last_payload: SentimentUpdate | None = None
        self.country_profiles = self._load_country_profiles()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def ingest(self, signal: QueuedSignal) -> None:
        self.queue.add(signal)

    def run_batch_sync(self) -> None:
        asyncio.run(self.aggregate_and_publish())

    async def aggregate_and_publish(self, use_live_market: bool = True) -> SentimentUpdate:
        latest = self.queue.latest_by_source()
        queued_market = latest.get("market_data")
        if use_live_market and not self._is_demo_market_signal(queued_market):
            latest["market_data"] = self._load_market_signal()

        payload = self._build_sentiment_update(latest)
        self.last_payload = payload

        await self.socket_hub.emit_sentiment_update(payload)

        focus_event = self._build_focus_region_event(latest)
        if focus_event is not None:
            await self.socket_hub.emit_focus_region(focus_event)

        return payload

    def get_last_payload(self) -> SentimentUpdate | None:
        return self.last_payload

    async def inject_demo_risk_event(self) -> SentimentUpdate:
        timestamp = datetime.now(timezone.utc)
        self.queue.add(
            PoliticianSignal(
                source="politician",
                sentiment_score=-92,
                confidence=94,
                signal=(
                    "Trump orders direct strikes on Iranian nuclear sites, triggering "
                    "an immediate flight to safety across global risk assets."
                ),
                timestamp=timestamp,
                author="White House Alert Desk",
                platform="rss",
                tier="president",
                fact_check="Real",
                fact_check_reasoning="Scenario payload for live demo stress testing.",
                affected_sectors=["Energy", "Defense", "Airlines", "Shipping"],
                event_location={
                    "lat": 35.6892,
                    "lon": 51.3890,
                    "city": "Tehran",
                    "country": "IR",
                },
            )
        )
        self.queue.add(
            MarketDataSignal(
                source="market_data",
                sentiment_score=-88,
                confidence=95,
                signal=(
                    "Equities gap lower, volatility surges, and safe-haven positioning "
                    "takes over after the strike order."
                ),
                timestamp=timestamp,
                details={
                    "sp500": {"price": 5160.0, "change_pct": -4.8},
                    "nasdaq": {"price": 16090.0, "change_pct": -6.4},
                    "vix": {"price": 31.8, "change_pct": 39.6},
                    "oil": {"price": 86.7, "change_pct": 5.8},
                    "dxy": {"price": 105.4, "change_pct": 0.9},
                    "gold": {"price": 2298.6, "change_pct": 2.4},
                    "us10y": {"yield": 4.03, "change_bps": -18.0},
                },
                market_status="demo_risk_event",
            )
        )
        return await self.aggregate_and_publish(use_live_market=False)

    async def inject_demo_rss_relief(self) -> SentimentUpdate:
        timestamp = datetime.now(timezone.utc)
        self.queue.add(
            NewsStreamSignal(
                source="news_stream",
                sentiment_score=58,
                confidence=86,
                signal=(
                    "Emergency diplomacy headlines calm the tape as ceasefire odds rise "
                    "and traders rebuild risk exposure."
                ),
                timestamp=timestamp,
                keywords=["ceasefire", "de-escalation", "risk-on"],
                data_origin="demo_relief_rss",
                segment_duration_sec=30,
            )
        )
        self.queue.add(
            MarketDataSignal(
                source="market_data",
                sentiment_score=76,
                confidence=91,
                signal=(
                    "Stocks rebound sharply, volatility unwinds, and the cross-asset "
                    "tape shifts back toward relief."
                ),
                timestamp=timestamp,
                details={
                    "sp500": {"price": 5418.0, "change_pct": 3.9},
                    "nasdaq": {"price": 17040.0, "change_pct": 5.1},
                    "vix": {"price": 19.6, "change_pct": -24.7},
                    "oil": {"price": 79.2, "change_pct": -3.8},
                    "dxy": {"price": 103.9, "change_pct": -0.6},
                    "gold": {"price": 2231.1, "change_pct": -1.4},
                    "us10y": {"yield": 4.18, "change_bps": 11.0},
                },
                market_status="demo_rss_relief",
            )
        )
        return await self.aggregate_and_publish(use_live_market=False)

    async def reset_demo_state(self) -> SentimentUpdate:
        timestamp = datetime.now(timezone.utc)
        market_signal = self._load_market_signal(store=False)

        self.queue.clear()
        self.last_payload = None
        self.queue.add(
            NewsStreamSignal(
                source="news_stream",
                sentiment_score=0,
                confidence=68,
                signal="Macro RSS baseline restored with mixed headlines and no clear risk impulse.",
                timestamp=timestamp,
                keywords=["baseline", "mixed", "neutral"],
                data_origin="demo_reset",
                segment_duration_sec=30,
            )
        )
        self.queue.add(
            PoliticianSignal(
                source="politician",
                sentiment_score=0,
                confidence=72,
                signal="Policy and geopolitical wires return to a watchful but neutral baseline.",
                timestamp=timestamp,
                author="Demo Control",
                platform="demo",
                tier="other",
                fact_check="Real",
                fact_check_reasoning="Operator reset uses a synthetic neutral baseline.",
                affected_sectors=[],
                event_location=None,
            )
        )
        self.queue.add(
            MarketDataSignal(
                source="market_data",
                sentiment_score=0,
                confidence=market_signal.confidence,
                signal="Live market snapshot preserved while the demo baseline resets to neutral.",
                timestamp=timestamp,
                details=market_signal.details,
                market_status="demo_reset",
            )
        )
        return await self.aggregate_and_publish(use_live_market=False)

    def _load_market_signal(self, store: bool = True) -> MarketDataSignal:
        from .market_engine import get_hub_payload

        response = get_hub_payload()
        payload = json.loads(response.body.decode("utf-8"))
        signal = MarketDataSignal.model_validate(payload)
        if store:
            self.queue.add(signal)
        return signal

    def _is_demo_market_signal(self, signal: QueuedSignal | None) -> bool:
        return (
            isinstance(signal, MarketDataSignal)
            and signal.market_status.startswith("demo_")
        )

    def _load_country_profiles(self) -> dict[str, CountryData]:
        if not COUNTRY_PROFILE_PATH.exists():
            return {}

        raw = json.loads(COUNTRY_PROFILE_PATH.read_text(encoding="utf-8"))
        return {
            code: CountryData.model_validate(profile)
            for code, profile in raw.items()
        }

    def _weights_for(self, latest: dict[str, QueuedSignal]) -> dict[str, float]:
        available = set(latest.keys())
        if available == {"market_data"}:
            return FALLBACK_WEIGHTS["only_market"]
        if "news_stream" not in available and "politician" in available:
            return FALLBACK_WEIGHTS["no_news"]
        if "politician" not in available and "news_stream" in available:
            return FALLBACK_WEIGHTS["no_politician"]

        weights = {key: SOURCE_WEIGHTS[key] for key in available if key in SOURCE_WEIGHTS}
        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}

    def _effective_score(self, signal: QueuedSignal) -> int:
        if isinstance(signal, PoliticianSignal) and signal.fact_check == "Fake":
            return 0
        return signal.sentiment_score

    def _label_for(self, score: int) -> str:
        if score >= SENTIMENT_THRESHOLDS["bullish"]:
            return "Bullish"
        if score <= SENTIMENT_THRESHOLDS["bearish"]:
            return "Bearish"
        return "Neutral"

    def _build_sentiment_update(self, latest: dict[str, QueuedSignal]) -> SentimentUpdate:
        weights = self._weights_for(latest)
        latest_received = self.queue.latest_received_at_by_source()

        weighted_score = 0.0
        weighted_confidence = 0.0
        drivers: list[Driver] = []

        for source, signal in latest.items():
            weight = weights.get(source, 0.0)
            effective_score = self._effective_score(signal)
            weighted_score += effective_score * weight
            weighted_confidence += signal.confidence * weight
            drivers.append(
                Driver(
                    source=signal.source,
                    sentiment_score=effective_score,
                    signal=signal.signal,
                    weight=round(weight, 2),
                    timestamp=signal.timestamp,
                    fact_check=(
                        f"{signal.fact_check} ({signal.confidence}%)"
                        if isinstance(signal, PoliticianSignal)
                        else None
                    ),
                    event_location=(
                        signal.event_location
                        if isinstance(signal, PoliticianSignal)
                        else None
                    ),
                )
            )

        drivers.sort(key=lambda item: abs(item.sentiment_score * item.weight), reverse=True)

        sentiment_score = int(round(max(-100, min(100, weighted_score))))
        overall_sentiment = self._label_for(sentiment_score)
        bullish_pct = round((sentiment_score + 100) / 2, 1)
        confidence = int(round(max(0, min(100, weighted_confidence))))

        previous = self.last_payload.overall_sentiment if self.last_payload else None
        if previous is None:
            sentiment_change = "initial"
        elif previous == overall_sentiment:
            sentiment_change = "continuation"
        else:
            sentiment_change = "reversal"

        market_signal = latest.get("market_data")
        market_snapshot = (
            MarketSnapshot(
                sp500=market_signal.details.sp500,
                nasdaq=market_signal.details.nasdaq,
                vix=market_signal.details.vix,
                oil=market_signal.details.oil,
                dxy=market_signal.details.dxy,
                gold=market_signal.details.gold,
                us10y=market_signal.details.us10y,
            )
            if isinstance(market_signal, MarketDataSignal)
            else MarketSnapshot()
        )

        freshness = DataFreshness(
            news_last=latest_received.get("news_stream"),
            politician_last=latest_received.get("politician"),
            market_last=latest_received.get("market_data"),
        )

        reasoning = self._build_reasoning(
            drivers=drivers,
            sentiment_score=sentiment_score,
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            previous_sentiment=previous,
            sentiment_change=sentiment_change,
            market_snapshot=market_snapshot,
            freshness=freshness,
        )

        return SentimentUpdate(
            sentiment_score=sentiment_score,
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            bullish_pct=bullish_pct,
            previous_sentiment=previous,
            sentiment_change=sentiment_change,
            drivers=drivers,
            market_snapshot=market_snapshot,
            reasoning=reasoning,
            data_freshness=freshness,
            timestamp=datetime.now(timezone.utc),
        )

    def _build_reasoning(
        self,
        drivers: list[Driver],
        sentiment_score: int,
        overall_sentiment: str,
        confidence: int,
        previous_sentiment: str | None,
        sentiment_change: str,
        market_snapshot: MarketSnapshot,
        freshness: DataFreshness,
    ) -> str:
        if not drivers:
            return "No live signals available yet."

        strongest = drivers[0]
        opposing = next(
            (
                driver
                for driver in drivers[1:]
                if (driver.sentiment_score < 0) != (strongest.sentiment_score < 0)
            ),
            None,
        )
        aligned_sources = [
            self._format_source_label(driver.source)
            for driver in drivers
            if (driver.sentiment_score < 0) == (sentiment_score < 0)
        ]
        divergence_sources = [
            self._format_source_label(driver.source)
            for driver in drivers
            if (driver.sentiment_score < 0) != (sentiment_score < 0)
        ]

        analysis = [
            (
                f"Overall sentiment is {overall_sentiment.lower()} at {sentiment_score} "
                f"with confidence at {confidence}%."
            ),
            (
                f"The primary driver is {self._format_source_label(strongest.source).lower()}, "
                f"contributing a {self._direction_word(strongest.sentiment_score)} impulse: "
                f"{strongest.signal}"
            ),
        ]

        market_read = self._build_market_read(market_snapshot)
        if market_read:
            analysis.append(market_read)

        if opposing is not None:
            analysis.append(
                "The main counter-pressure comes from "
                f"{self._format_source_label(opposing.source).lower()}: {opposing.signal}"
            )

        if aligned_sources:
            alignment_text = ", ".join(aligned_sources)
            analysis.append(f"Sources currently aligned with the tape: {alignment_text}.")

        if divergence_sources:
            divergence_text = ", ".join(divergence_sources)
            analysis.append(f"Offsets or balancing inputs are coming from {divergence_text}.")

        regime_view = self._build_regime_view(
            overall_sentiment=overall_sentiment,
            previous_sentiment=previous_sentiment,
            sentiment_change=sentiment_change,
            freshness=freshness,
        )
        if regime_view:
            analysis.append(regime_view)

        return " ".join(sentence.strip() for sentence in analysis if sentence).strip()

    def _format_source_label(self, source: str) -> str:
        labels = {
            "market_data": "Market",
            "news_stream": "News",
            "politician": "Politics",
        }
        return labels.get(source, source.replace("_", " ").title())

    def _direction_word(self, value: int) -> str:
        if value >= 25:
            return "bullish"
        if value > 0:
            return "supportive"
        if value <= -25:
            return "bearish"
        if value < 0:
            return "defensive"
        return "neutral"

    def _build_market_read(self, snapshot: MarketSnapshot) -> str:
        snippets: list[str] = []

        if snapshot.sp500 and snapshot.sp500.change_pct is not None:
            snippets.append(f"S&P {snapshot.sp500.change_pct:+.2f}%")
        if snapshot.nasdaq and snapshot.nasdaq.change_pct is not None:
            snippets.append(f"Nasdaq {snapshot.nasdaq.change_pct:+.2f}%")
        if snapshot.vix and snapshot.vix.change_pct is not None:
            snippets.append(f"VIX {snapshot.vix.change_pct:+.2f}%")
        if snapshot.oil and snapshot.oil.change_pct is not None:
            snippets.append(f"Oil {snapshot.oil.change_pct:+.2f}%")
        if snapshot.gold and snapshot.gold.change_pct is not None:
            snippets.append(f"Gold {snapshot.gold.change_pct:+.2f}%")

        if not snippets:
            return ""

        return "Cross-asset context remains in focus with " + ", ".join(snippets[:5]) + "."

    def _build_regime_view(
        self,
        overall_sentiment: str,
        previous_sentiment: str | None,
        sentiment_change: str,
        freshness: DataFreshness,
    ) -> str:
        available_feeds = [
            label
            for label, value in (
                ("News", freshness.news_last),
                ("Politics", freshness.politician_last),
                ("Market", freshness.market_last),
            )
            if value is not None
        ]

        if sentiment_change == "initial":
            trend_text = f"This is the first aggregated {overall_sentiment.lower()} read."
        elif sentiment_change == "reversal" and previous_sentiment is not None:
            trend_text = (
                f"The dashboard has flipped from {previous_sentiment.lower()} "
                f"to {overall_sentiment.lower()}."
            )
        else:
            trend_text = (
                f"The dashboard remains in {overall_sentiment.lower()} continuation mode "
                f"versus the previous batch."
            )

        if not available_feeds:
            return trend_text

        feeds_text = ", ".join(available_feeds)
        return f"{trend_text} Live inputs currently active: {feeds_text}."

    def _build_focus_region_event(
        self,
        latest: dict[str, QueuedSignal],
    ) -> FocusRegionEvent | None:
        candidates = [
            signal
            for signal in latest.values()
            if isinstance(signal, PoliticianSignal) and signal.event_location is not None
        ]
        if not candidates:
            return None

        candidates.sort(key=lambda signal: abs(signal.sentiment_score), reverse=True)
        signal = candidates[0]
        focus_signature = (
            f"{signal.source}:{signal.event_location.country}:{signal.event_location.city}:"
            f"{signal.signal[:96]}"
        )
        if not self.socket_hub.should_trigger_autopilot(
            sentiment_score=signal.sentiment_score,
            has_location=signal.event_location is not None,
            signature=focus_signature,
        ):
            return None

        country_data = self.country_profiles.get(signal.event_location.country)
        return FocusRegionEvent(
            lat=signal.event_location.lat,
            lon=signal.event_location.lon,
            city=signal.event_location.city,
            country=signal.event_location.country,
            trigger_signal=signal.signal,
            sentiment_score=signal.sentiment_score,
            source=signal.source,
            country_data=country_data,
            timestamp=datetime.now(timezone.utc),
        )
