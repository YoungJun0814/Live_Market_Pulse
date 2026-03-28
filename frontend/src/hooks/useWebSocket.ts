import { useEffect, useState } from "react";
import { io } from "socket.io-client";

import type { FocusRegionEvent, SentimentUpdate } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const SOCKET_PATH = import.meta.env.VITE_SOCKET_PATH ?? "/socket.io";

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [latestUpdate, setLatestUpdate] = useState<SentimentUpdate | null>(null);
  const [latestFocusRegion, setLatestFocusRegion] = useState<FocusRegionEvent | null>(null);

  useEffect(() => {
    let isCancelled = false;

    void fetch(`${API_BASE_URL}/api/latest`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Initial latest fetch failed with ${response.status}`);
        }
        return response.json() as Promise<SentimentUpdate>;
      })
      .then((payload) => {
        if (!isCancelled) {
          setLatestUpdate(payload);
        }
      })
      .catch((error) => {
        console.warn("Initial sentiment fetch failed", error);
      });

    const socket = io(API_BASE_URL, {
      path: SOCKET_PATH,
      transports: ["websocket"],
    });

    socket.on("connect", () => setIsConnected(true));
    socket.on("disconnect", () => setIsConnected(false));
    socket.on("sentiment_update", (payload: SentimentUpdate) => setLatestUpdate(payload));
    socket.on("focus_region", (payload: FocusRegionEvent) => setLatestFocusRegion(payload));

    return () => {
      isCancelled = true;
      socket.disconnect();
    };
  }, []);

  return {
    isConnected,
    latestUpdate,
    latestFocusRegion,
  };
}
