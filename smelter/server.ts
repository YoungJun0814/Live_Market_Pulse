import "dotenv/config";

import React from "react";
import { MarketOverlayScene } from "./MarketOverlayScene.js";

const INPUT_ID = "live-news-input";
const OUTPUT_ID = "market-broadcast";

interface OverlayPayload {
  headline: string;
  overall_sentiment: string;
  sentiment_score: number;
  reasoning: string;
  timestamp?: string;
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

async function fetchOverlayPayload(apiUrl: string): Promise<OverlayPayload> {
  const response = await fetch(apiUrl);
  if (!response.ok) {
    throw new Error(`Overlay API returned ${response.status}`);
  }
  return (await response.json()) as OverlayPayload;
}

async function main() {
  const smelterModule = await import("@swmansion/smelter-node");
  const Smelter = ((smelterModule as { default?: unknown }).default ?? smelterModule) as unknown as {
    new (): {
      init(): Promise<void>;
      registerInput(inputId: string, request: { type: "hls"; url: string }): Promise<unknown>;
      registerOutput(
        outputId: string,
        root: React.ReactElement,
        request: Record<string, unknown>,
      ): Promise<{ endpointRoute?: string }>;
      start(): Promise<void>;
    };
  };
  const liveInputUrl = requireEnv("LIVE_NEWS_HLS_URL");
  const overlayApiUrl =
    process.env.OVERLAY_API_URL ?? "http://127.0.0.1:8000/api/live_overlay";

  const overlay = await fetchOverlayPayload(overlayApiUrl);
  const smelter = new Smelter();

  console.log("[smelter] Initializing compositor...");
  await smelter.init();
  await smelter.registerInput(INPUT_ID, {
    type: "hls",
    url: liveInputUrl,
  });
  const result = await smelter.registerOutput(
    OUTPUT_ID,
    React.createElement(MarketOverlayScene, {
      inputId: INPUT_ID,
      sentimentScore: overlay.sentiment_score,
      overallSentiment: overlay.overall_sentiment,
      headline: overlay.headline,
      reasoning: overlay.reasoning,
      timestamp: overlay.timestamp,
    }),
    {
      type: "whep_server",
      video: null,
      audio: null,
    },
  );
  console.log("[smelter] WHEP endpoint:", result);
  await smelter.start();
  console.log("[smelter] Pipeline started.");
}

main().catch((error) => {
  console.error("[smelter] Failed to start:", error);
  process.exitCode = 1;
});
