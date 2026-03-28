import { startTransition, useEffect, useRef, useState } from "react";

import type { FocusRegionEvent, SentimentUpdate } from "../types";
import { useWebSocket } from "./useWebSocket";

function seedSentiment(): SentimentUpdate {
  const timestamp = new Date().toISOString();
  return {
    sentiment_score: 12,
    overall_sentiment: "Neutral",
    confidence: 58,
    bullish_pct: 56,
    previous_sentiment: "Neutral",
    sentiment_change: "continuation",
    drivers: [
      {
        source: "market_data",
        sentiment_score: 18,
        signal: "S&P grinds higher while VIX cools off.",
        weight: 0.4,
        timestamp,
      },
      {
        source: "news_stream",
        sentiment_score: 22,
        signal: "Fed speakers keep the door open for easing later this year.",
        weight: 0.35,
        timestamp,
      },
      {
        source: "politician",
        sentiment_score: -8,
        signal: "Trade rhetoric adds mild geopolitical drag.",
        weight: 0.25,
        timestamp,
        fact_check: "Real (78%)",
        event_location: {
          lat: 38.9,
          lon: -77.0,
          city: "Washington DC",
          country: "US",
        },
      },
    ],
    market_snapshot: {
      sp500: { price: 5421, change_pct: 0.8 },
      nasdaq: { price: 17182, change_pct: 1.1 },
      vix: { price: 18.2, change_pct: -3.1 },
      oil: { price: 78.3, change_pct: 1.2 },
      dxy: { price: 104.2, change_pct: -0.3 },
      gold: { price: 2218.4, change_pct: 0.4 },
      us10y: { yield: 4.21, change_bps: -2.4 },
    },
    reasoning:
      "Market data is mildly constructive and the news tape is supportive, but geopolitical headlines still cap conviction.",
    data_freshness: {
      news_last: timestamp,
      politician_last: timestamp,
      market_last: timestamp,
    },
    timestamp,
  };
}

function buildFocusEventFromUpdate(update: SentimentUpdate): FocusRegionEvent | null {
  const driverWithLocation = update.drivers.find((driver) => driver.event_location);
  if (!driverWithLocation?.event_location) {
    return null;
  }

  return {
    event: "focus_region",
    lat: driverWithLocation.event_location.lat,
    lon: driverWithLocation.event_location.lon,
    city: driverWithLocation.event_location.city,
    country: driverWithLocation.event_location.country,
    trigger_signal: driverWithLocation.signal,
    sentiment_score: driverWithLocation.sentiment_score,
    source: driverWithLocation.source,
    timestamp: driverWithLocation.timestamp,
  };
}

function mergeFocusEvent(
  previous: FocusRegionEvent[],
  nextEvent: FocusRegionEvent,
): FocusRegionEvent[] {
  const alreadyPresent = previous.some(
    (event) =>
      event.source === nextEvent.source &&
      event.city === nextEvent.city &&
      event.country === nextEvent.country &&
      event.timestamp === nextEvent.timestamp,
  );

  if (alreadyPresent) {
    return previous;
  }

  return [nextEvent, ...previous].slice(0, 30);
}

export function useSentiment() {
  const { isConnected, latestUpdate, latestFocusRegion } = useWebSocket();
  const initialSentimentRef = useRef<SentimentUpdate>(seedSentiment());
  const initialSentiment = initialSentimentRef.current;
  const [current, setCurrent] = useState<SentimentUpdate>(initialSentiment);
  const [signalHistory, setSignalHistory] = useState<SentimentUpdate[]>([initialSentiment]);
  const [focusEvents, setFocusEvents] = useState<FocusRegionEvent[]>(() => {
    const initialFocusEvent = buildFocusEventFromUpdate(initialSentiment);
    return initialFocusEvent ? [initialFocusEvent] : [];
  });

  useEffect(() => {
    if (!latestUpdate || latestUpdate.timestamp === current.timestamp) {
      return;
    }

    startTransition(() => {
      setCurrent(latestUpdate);
      setSignalHistory((prev) => [latestUpdate, ...prev].slice(0, 100));
      const derivedFocusEvent = buildFocusEventFromUpdate(latestUpdate);
      if (derivedFocusEvent) {
        setFocusEvents((prev) => mergeFocusEvent(prev, derivedFocusEvent));
      }
    });
  }, [current.timestamp, latestUpdate]);

  useEffect(() => {
    if (!latestFocusRegion) {
      return;
    }

    startTransition(() => {
      setFocusEvents((prev) => mergeFocusEvent(prev, latestFocusRegion));
    });
  }, [latestFocusRegion]);

  return {
    isConnected,
    current,
    signalHistory,
    focusEvents,
  };
}
