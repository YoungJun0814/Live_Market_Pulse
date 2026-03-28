import { useEffect, useRef } from "react";
import type { SentimentUpdate } from "../types";
import { useWHEP } from "../hooks/useWHEP";

interface LiveNewsPlayerProps {
  sentiment: SentimentUpdate;
  headline: string;
}

const DEFAULT_LIVE_NEWS_URL = "https://www.youtube.com/watch?v=YDvsBbKfLPA";
const DEFAULT_LIVE_NEWS_EMBED_URL =
  "https://www.youtube-nocookie.com/embed/YDvsBbKfLPA?autoplay=1&mute=1&playsinline=1&rel=0";

export function LiveNewsPlayer({ sentiment, headline }: LiveNewsPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const whepEndpoint = import.meta.env.VITE_FISHJAM_WHEP_ENDPOINT;
  const { stream, error, isConnected } = useWHEP(whepEndpoint);

  // If we don't have a WHEP endpoint or if connection actively failed, use fallback
  const useFallback = !whepEndpoint || Boolean(error);

  const liveNewsUrl = import.meta.env.VITE_LIVE_NEWS_URL ?? DEFAULT_LIVE_NEWS_URL;
  const liveNewsEmbedUrl =
    import.meta.env.VITE_LIVE_NEWS_EMBED_URL ?? DEFAULT_LIVE_NEWS_EMBED_URL;
  const toneClass =
    sentiment.sentiment_score > 20
      ? "player-shell__overlay--bullish"
      : sentiment.sentiment_score < -20
        ? "player-shell__overlay--bearish"
        : "player-shell__overlay--neutral";

  // Attach MediaStream to video element dynamically
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <section className="panel panel--player">
      <div className="panel__heading">
        <p className="eyebrow">Zone 3 - Live News</p>
        <h2>{useFallback ? "Live News Player (Fallback)" : "Fishjam WHEP Stream"}</h2>
      </div>
      <div className="player-shell">
        <div className="player-shell__screen">
          {useFallback ? (
            /* FALLBACK: YouTube Iframe + CSS Overlay */
            <>
              <iframe
                className="player-shell__iframe"
                src={liveNewsEmbedUrl}
                title="Live news broadcast"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
              />
              <div className="player-shell__tag-row">
                <div className="player-shell__tag">Sky News Fallback</div>
                <a
                  className="player-shell__link"
                  href={liveNewsUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open Source
                </a>
              </div>
              <div className={`player-shell__overlay ${toneClass}`}>
                <span>{sentiment.overall_sentiment}</span>
                <strong>
                  {sentiment.sentiment_score >= 0 ? "+" : ""}
                  {sentiment.sentiment_score}
                </strong>
              </div>
              <div className="player-shell__lower-third">
                <span>Breaking</span>
                <p>{headline}</p>
              </div>
            </>
          ) : (
            /* PRIMARY: Native WHEP Video Element */
            <video
              ref={videoRef}
              className="player-shell__iframe"
              autoPlay
              muted
              playsInline
              style={{ objectFit: "cover", width: "100%", height: "100%", display: "block" }}
            />
          )}

          {!useFallback && !isConnected && (
            <div className="player-shell__overlay player-shell__overlay--neutral">
              <span>Connecting to Fishjam...</span>
            </div>
          )}
        </div>
        <div className="player-shell__meters">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
      </div>
    </section>
  );
}
