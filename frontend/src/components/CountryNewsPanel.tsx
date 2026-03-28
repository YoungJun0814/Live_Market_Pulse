import { AnimatePresence, motion } from "framer-motion";

import type { CountryData, SentimentUpdate } from "../types";
import { SignalCard } from "./SignalCard";

interface CountryNewsPanelProps {
  selectedCountry: string | null;
  profile?: CountryData;
  history: SentimentUpdate[];
  onClose: () => void;
}

function flagEmoji(countryCode: string) {
  return countryCode
    .toUpperCase()
    .replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)));
}

export function CountryNewsPanel({
  selectedCountry,
  profile,
  history,
  onClose,
}: CountryNewsPanelProps) {
  const relatedSignals = selectedCountry
    ? history
        .flatMap((entry) => entry.drivers)
        .filter((driver) => driver.event_location?.country === selectedCountry)
        .slice(0, 5)
    : [];

  return (
    <AnimatePresence>
      {selectedCountry ? (
        <motion.aside
          className="country-panel"
          initial={{ x: 320, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 320, opacity: 0 }}
          transition={{ type: "spring", stiffness: 280, damping: 28 }}
        >
          <div className="country-panel__header">
            <div className="country-panel__title">
              <p className="eyebrow">Regional Focus</p>
              <h2>
                <span>{flagEmoji(selectedCountry)}</span>
                {selectedCountry}
              </h2>
            </div>
            <button type="button" className="country-panel__close" onClick={onClose}>
              Close
            </button>
          </div>

          {profile ? (
            <div className="country-panel__stats">
              <div>
                <span>Index</span>
                <strong>{profile.stock_index}</strong>
              </div>
              <div>
                <span>Market</span>
                <strong>{profile.stock_value.toLocaleString()}</strong>
              </div>
              <div>
                <span>GDP</span>
                <strong>{profile.gdp_growth}%</strong>
              </div>
              <div>
                <span>CPI</span>
                <strong>{profile.cpi}%</strong>
              </div>
              <div>
                <span>Currency</span>
                <strong>{profile.currency}</strong>
              </div>
            </div>
          ) : (
            <p className="country-panel__empty">
              Country metrics are not available for this focus region yet.
            </p>
          )}

          <div className="country-panel__signals">
            <div className="panel__heading">
              <p className="eyebrow">Latest Triggers</p>
              <h3>Country Signal Feed</h3>
            </div>
            {relatedSignals.length ? (
              relatedSignals.map((driver, index) => (
                <SignalCard
                  key={`${driver.source}-${driver.timestamp}-${index}`}
                  driver={driver}
                />
              ))
            ) : (
              <p className="country-panel__empty">
                No location-tagged political shock is stored for this country yet.
              </p>
            )}
          </div>
        </motion.aside>
      ) : null}
    </AnimatePresence>
  );
}
