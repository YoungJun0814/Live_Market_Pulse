import { useEffect, useState } from "react";

import type { SentimentUpdate } from "../types";

interface StatusBarProps {
  isConnected: boolean;
  current: SentimentUpdate;
}

function formatFreshness(value?: string | null) {
  if (!value) {
    return "pending";
  }

  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export function StatusBar({ isConnected, current }: StatusBarProps) {
  const [utcClock, setUtcClock] = useState(() =>
    new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "UTC",
      hour12: false,
    }).format(new Date()),
  );

  useEffect(() => {
    const timer = window.setInterval(() => {
      setUtcClock(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          timeZone: "UTC",
          hour12: false,
        }).format(new Date()),
      );
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="status-bar">
      <div className="status-bar__brand">
        <h1>Live Market Pulse</h1>
      </div>
      <div className="status-bar__live">
        <span className="status-bar__dot" />
        <strong>Live</strong>
        <span>UTC {utcClock}</span>
      </div>
      <div className="status-bar__chips">
        <span className={isConnected ? "chip chip--live" : "chip chip--offline"}>
          {isConnected ? "Socket Live" : "Socket Offline"}
        </span>
        <span className="chip">Sentiment {current.sentiment_score}</span>
        <span className="chip">News {formatFreshness(current.data_freshness.news_last)}</span>
        <span className="chip">
          Politics {formatFreshness(current.data_freshness.politician_last)}
        </span>
        <span className="chip">
          Market {formatFreshness(current.data_freshness.market_last)}
        </span>
      </div>
    </header>
  );
}
