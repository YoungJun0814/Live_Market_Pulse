import type { Driver } from "../types";

interface SignalCardProps {
  driver: Driver;
  onCountrySelect?: (country: string) => void;
}

function formatTimestamp(timestamp: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}

export function SignalCard({ driver, onCountrySelect }: SignalCardProps) {
  const sentimentClass =
    driver.sentiment_score > 0
      ? "signal-card__score--bullish"
      : driver.sentiment_score < 0
        ? "signal-card__score--bearish"
        : "signal-card__score--neutral";
  const factCheckTone =
    driver.fact_check?.includes("Real")
      ? "signal-card__fact-check--real"
      : driver.fact_check?.includes("Fake")
        ? "signal-card__fact-check--fake"
        : "signal-card__fact-check--neutral";

  return (
    <article className="signal-card">
      <header className="signal-card__header">
        <div>
          <p className="signal-card__source">{driver.source.replace("_", " ")}</p>
          <h4>{driver.signal}</h4>
        </div>
        <div className={`signal-card__score ${sentimentClass}`}>
          {driver.sentiment_score > 0 ? "+" : ""}
          {driver.sentiment_score}
        </div>
      </header>
      <footer className="signal-card__meta">
        <span>{formatTimestamp(driver.timestamp)}</span>
        <span>Weight {Math.round(driver.weight * 100)}%</span>
        {driver.fact_check ? (
          <span className={`signal-card__fact-check ${factCheckTone}`}>
            {driver.fact_check}
          </span>
        ) : null}
        {driver.event_location ? (
          <button
            className="signal-card__country"
            type="button"
            onClick={() => onCountrySelect?.(driver.event_location!.country)}
          >
            {driver.event_location.city}, {driver.event_location.country}
          </button>
        ) : null}
      </footer>
    </article>
  );
}
