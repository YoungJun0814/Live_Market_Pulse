import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function callDemoAction(path: string) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Demo action failed with ${response.status}`);
  }
}

export function DemoControls() {
  const [status, setStatus] = useState("Ready for demo scenarios");

  const publishMacroRelief = async () => {
    setStatus("Injecting RSS relief and market rebound...");
    await callDemoAction("/api/demo/push-rss-relief");
    setStatus("RSS relief delivered with market recovery");
  };

  const publishGeopoliticalShock = async () => {
    setStatus("Injecting geopolitical shock and market selloff...");
    await callDemoAction("/api/demo/push-risk-event");
    setStatus("Risk event delivered with market crash");
  };

  const resetToNeutral = async () => {
    setStatus("Resetting to neutral...");
    await callDemoAction("/api/demo/reset-neutral");
    setStatus("Neutral baseline restored");
  };

  return (
    <section className="demo-bar">
      <div>
        <p className="eyebrow">Operator Tools</p>
        <strong>Demo Controls</strong>
      </div>
      <div className="demo-bar__actions">
        <button type="button" onClick={() => void publishMacroRelief()}>
          Push RSS Relief
        </button>
        <button
          type="button"
          className="demo-bar__button--alert"
          onClick={() => void publishGeopoliticalShock()}
        >
          Push Risk Event
        </button>
        <button type="button" onClick={() => void resetToNeutral()}>
          Reset Neutral
        </button>
      </div>
      <p className="demo-bar__status">{status}</p>
    </section>
  );
}
