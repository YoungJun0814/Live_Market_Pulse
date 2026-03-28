export type SourceType = "news_stream" | "politician" | "market_data";

export interface EventLocation {
  lat: number;
  lon: number;
  city: string;
  country: string;
}

export interface MarketPoint {
  price?: number | null;
  change_pct?: number | null;
  yield?: number | null;
  change_bps?: number | null;
}

export interface MarketSnapshot {
  sp500?: MarketPoint | null;
  nasdaq?: MarketPoint | null;
  vix?: MarketPoint | null;
  oil?: MarketPoint | null;
  dxy?: MarketPoint | null;
  gold?: MarketPoint | null;
  us10y?: MarketPoint | null;
}

export interface Driver {
  source: SourceType;
  sentiment_score: number;
  signal: string;
  weight: number;
  timestamp: string;
  fact_check?: string | null;
  event_location?: EventLocation | null;
}

export interface DataFreshness {
  news_last?: string | null;
  politician_last?: string | null;
  market_last?: string | null;
}

export interface SentimentUpdate {
  sentiment_score: number;
  overall_sentiment: "Bullish" | "Neutral" | "Bearish";
  confidence: number;
  bullish_pct: number;
  previous_sentiment?: "Bullish" | "Neutral" | "Bearish" | null;
  sentiment_change: "initial" | "continuation" | "reversal";
  drivers: Driver[];
  market_snapshot: MarketSnapshot;
  reasoning: string;
  data_freshness: DataFreshness;
  timestamp: string;
}

export interface CountryData {
  stock_index: string;
  stock_value: number;
  gdp_growth: number;
  cpi: number;
  currency: string;
}

export interface FocusRegionEvent {
  event: "focus_region";
  lat: number;
  lon: number;
  city: string;
  country: string;
  trigger_signal: string;
  sentiment_score: number;
  source: SourceType;
  country_data?: CountryData | null;
  timestamp?: string;
}
