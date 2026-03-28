import type { SentimentUpdate } from "../types";

interface ReasoningPanelProps {
  sentiment: SentimentUpdate;
}

function formatSourceLabel(value?: string) {
  if (!value) {
    return "No update";
  }

  const labels: Record<string, string> = {
    market_data: "Market",
    news_stream: "News",
    politician: "Politics",
  };

  return labels[value] ?? value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function freshnessLabel(value?: string | null) {
  if (!value) {
    return "No update";
  }

  const diffMinutes = Math.max(
    0,
    Math.round((Date.now() - new Date(value).getTime()) / 60000),
  );

  if (diffMinutes < 10) {
    return "Live now";
  }
  if (diffMinutes === 1) {
    return "1 min ago";
  }
  return `${diffMinutes} mins ago`;
}

export function ReasoningPanel({ sentiment }: ReasoningPanelProps) {
  const strongest = sentiment.drivers[0];

  return (
    <section className="panel panel--reasoning">
      <div className="panel__heading">
        <p className="eyebrow">Zone 2 - AI Analysis</p>
        <h2>Reasoning & Context</h2>
      </div>
      <div className="reasoning-card">
        <p className="reasoning-card__copy" title={sentiment.reasoning}>
          {sentiment.reasoning}
        </p>
        <div className="reasoning-card__meta">
          <span className="reasoning-pill">Trend {sentiment.sentiment_change}</span>
          <span className="reasoning-pill">
            Prev {sentiment.previous_sentiment ?? "None"}
          </span>
        </div>
      </div>
      <div className="reasoning-freshness-row">
        <div
          className="reasoning-summary-item"
          title={strongest?.signal}
        >
          <span>Primary</span>
          <strong>{formatSourceLabel(strongest?.source)}</strong>
        </div>
        <div
          className="reasoning-summary-item"
        >
          <span>News</span>
          <strong>{freshnessLabel(sentiment.data_freshness.news_last)}</strong>
        </div>
        <div className="reasoning-summary-item">
          <span>Politics</span>
          <strong>{freshnessLabel(sentiment.data_freshness.politician_last)}</strong>
        </div>
        <div className="reasoning-summary-item">
          <span>Market</span>
          <strong>{freshnessLabel(sentiment.data_freshness.market_last)}</strong>
        </div>
      </div>
    </section>
  );
}
