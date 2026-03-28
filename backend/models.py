from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class EventLocation(BaseModel):
    lat: float
    lon: float
    city: str
    country: str


class MarketDetailPoint(BaseModel):
    price: float | None = None
    change_pct: float | None = None
    yield_: float | None = Field(default=None, alias="yield")
    change_bps: float | None = None

    model_config = {"populate_by_name": True}


class MarketDetails(BaseModel):
    sp500: MarketDetailPoint | None = None
    nasdaq: MarketDetailPoint | None = None
    vix: MarketDetailPoint | None = None
    oil: MarketDetailPoint | None = None
    dxy: MarketDetailPoint | None = None
    gold: MarketDetailPoint | None = None
    us10y: MarketDetailPoint | None = None


class BaseSignal(BaseModel):
    sentiment_score: int = Field(ge=-100, le=100)
    confidence: int = Field(ge=0, le=100)
    signal: str
    timestamp: datetime


class NewsStreamSignal(BaseSignal):
    source: Literal["news_stream"]
    keywords: list[str] = Field(default_factory=list)
    data_origin: str
    segment_duration_sec: int | None = None


class PoliticianSignal(BaseSignal):
    source: Literal["politician"]
    author: str
    platform: str
    tier: Literal[
        "president",
        "fed_chair",
        "cabinet",
        "senator",
        "representative",
        "other",
    ]
    fact_check: Literal["Real", "Fake", "Unverified", "Misleading"]
    fact_check_reasoning: str
    affected_sectors: list[str] = Field(default_factory=list)
    event_location: EventLocation | None = None


class MarketDataSignal(BaseSignal):
    source: Literal["market_data"]
    details: MarketDetails
    market_status: str


SignalPayload = Annotated[
    NewsStreamSignal | PoliticianSignal | MarketDataSignal,
    Field(discriminator="source"),
]


class Driver(BaseModel):
    source: Literal["news_stream", "politician", "market_data"]
    sentiment_score: int = Field(ge=-100, le=100)
    signal: str
    weight: float
    timestamp: datetime
    fact_check: str | None = None
    event_location: EventLocation | None = None


class MarketSnapshot(BaseModel):
    sp500: MarketDetailPoint | None = None
    nasdaq: MarketDetailPoint | None = None
    vix: MarketDetailPoint | None = None
    oil: MarketDetailPoint | None = None
    dxy: MarketDetailPoint | None = None
    gold: MarketDetailPoint | None = None
    us10y: MarketDetailPoint | None = None


class DataFreshness(BaseModel):
    news_last: datetime | None = None
    politician_last: datetime | None = None
    market_last: datetime | None = None


class SentimentUpdate(BaseModel):
    sentiment_score: int = Field(ge=-100, le=100)
    overall_sentiment: Literal["Bullish", "Neutral", "Bearish"]
    confidence: int = Field(ge=0, le=100)
    bullish_pct: float = Field(ge=0, le=100)
    previous_sentiment: Literal["Bullish", "Neutral", "Bearish"] | None = None
    sentiment_change: Literal["initial", "continuation", "reversal"]
    drivers: list[Driver]
    market_snapshot: MarketSnapshot
    reasoning: str
    data_freshness: DataFreshness
    timestamp: datetime


class CountryData(BaseModel):
    stock_index: str
    stock_value: float | None = None
    gdp_growth: float | None = None
    cpi: float | None = None
    currency: str | None = None


class FocusRegionEvent(BaseModel):
    event: Literal["focus_region"] = "focus_region"
    lat: float
    lon: float
    city: str
    country: str
    trigger_signal: str
    sentiment_score: int = Field(ge=-100, le=100)
    source: Literal["news_stream", "politician", "market_data"]
    country_data: CountryData | None = None
    timestamp: datetime | None = None


class QueueSnapshot(BaseModel):
    counts: dict[str, int]
    latest_timestamps: dict[str, datetime | None]
