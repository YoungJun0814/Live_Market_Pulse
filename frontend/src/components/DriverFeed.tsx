import type { SentimentUpdate } from "../types";
import { SignalCard } from "./SignalCard";

interface DriverFeedProps {
  history: SentimentUpdate[];
}

export function DriverFeed({ history }: DriverFeedProps) {
  const drivers = history.flatMap((entry) => entry.drivers).slice(0, 8);

  return (
    <section className="panel panel--feed">
      <div className="panel__heading">
        <p className="eyebrow">Zone 5 - Political / AI Signals</p>
        <h2>Fact-Checked Feed</h2>
      </div>
      <div className="feed-list">
        {drivers.map((driver, index) => (
          <SignalCard key={`${driver.source}-${driver.timestamp}-${index}`} driver={driver} />
        ))}
      </div>
    </section>
  );
}
