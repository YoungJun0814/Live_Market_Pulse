import { Suspense, lazy, useDeferredValue, useMemo, useState } from "react";

import countryProfiles from "../../data/country_profiles.json";
import { DemoControls } from "./components/DemoControls";
import { DriverFeed } from "./components/DriverFeed";
import { HeadlinesTicker } from "./components/HeadlinesTicker";
import { LiveNewsPlayer } from "./components/LiveNewsPlayer";
import { MarketDrivers } from "./components/MarketDrivers";
import { ReasoningPanel } from "./components/ReasoningPanel";
import { SentimentGauge } from "./components/SentimentGauge";
import { SentimentHistory } from "./components/SentimentHistory";
import { StatusBar } from "./components/StatusBar";
import { useSentiment } from "./hooks/useSentiment";

const WorldMap = lazy(async () => {
  const module = await import("./components/WorldMap");
  return { default: module.WorldMap };
});

const CountryNewsPanel = lazy(async () => {
  const module = await import("./components/CountryNewsPanel");
  return { default: module.CountryNewsPanel };
});

function App() {
  const { isConnected, current, signalHistory, focusEvents } = useSentiment();
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const deferredHistory = useDeferredValue(signalHistory);

  const headlines = deferredHistory
    .flatMap((entry) => entry.drivers)
    .slice(0, 10)
    .map((driver) => driver.signal);
  const isPanelOpen = selectedCountry !== null;

  // Compute signal count and 5-min delta for the upgraded gauge
  const signalCount = useMemo(
    () => deferredHistory.reduce((sum, e) => sum + e.drivers.length, 0),
    [deferredHistory],
  );

  const delta5min = useMemo(() => {
    if (deferredHistory.length < 2) return null;
    const now = Date.now();
    const fiveMinAgo = deferredHistory.find(
      (e) => now - new Date(e.timestamp).getTime() >= 5 * 60_000,
    );
    if (!fiveMinAgo) return null;
    return current.sentiment_score - fiveMinAgo.sentiment_score;
  }, [deferredHistory, current.sentiment_score]);

  return (
    <div className="app-shell">
      <div className={`dashboard-stage${isPanelOpen ? " dashboard-stage--blurred" : ""}`}>
        <StatusBar isConnected={isConnected} current={current} />
        <main className="dashboard-grid">
          <div className="zone zone--map">
            <Suspense fallback={<div className="panel panel--loading">Loading map...</div>}>
              <WorldMap events={focusEvents} onCountrySelect={setSelectedCountry} />
            </Suspense>
          </div>
          <div className="zone zone--sentiment">
            <div className="sentiment-layout">
              <div className="sentiment-layout__top-row">
                <SentimentGauge
                  sentiment={current}
                  signalCount={signalCount}
                  delta5min={delta5min}
                />
                <SentimentHistory history={deferredHistory} />
              </div>
              <div className="sentiment-layout__bottom-row">
                <ReasoningPanel sentiment={current} />
              </div>
            </div>
          </div>

          <div className="zone zone--video">
            <LiveNewsPlayer
              sentiment={current}
              headline={headlines[0] ?? current.reasoning}
            />
          </div>
          <div className="zone zone--drivers">
            <MarketDrivers snapshot={current.market_snapshot} />
          </div>
          <div className="zone zone--feed">
            <DriverFeed history={deferredHistory} />
          </div>
          <div className="zone zone--ticker">
            <HeadlinesTicker items={headlines.length ? headlines : [current.reasoning]} />
          </div>
        </main>
        <DemoControls />
      </div>
      {isPanelOpen ? (
        <button
          type="button"
          className="dashboard-backdrop"
          aria-label="Close country panel"
          onClick={() => setSelectedCountry(null)}
        />
      ) : null}
      <Suspense fallback={null}>
        <CountryNewsPanel
          selectedCountry={selectedCountry}
          profile={
            selectedCountry
              ? countryProfiles[selectedCountry as keyof typeof countryProfiles]
              : undefined
          }
          history={deferredHistory}
          onClose={() => setSelectedCountry(null)}
        />
      </Suspense>
    </div>
  );
}

export default App;
