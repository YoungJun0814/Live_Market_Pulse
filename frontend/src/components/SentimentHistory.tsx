import { useEffect, useRef, useState, useCallback } from "react";
import type { SentimentUpdate } from "../types";

/* ── colours ── */
const C = {
  bearish: "#FF2D55",
  caution: "#FF9500",
  neutral: "#FFD60A",
  bullish: "#30D158",
  info: "#00E5FF",
  text: "#F5F5F7",
  muted: "#48484A",
  secondary: "#8E8E93",
  gridLine: "rgba(255,255,255,0.04)",
};

function sentimentColor(v: number): string {
  if (v < -50) return C.bearish;
  if (v < -20) return C.caution;
  if (v > 50) return C.bullish;
  if (v > 20) return C.bullish;
  return C.neutral;
}

function sourceColor(source: string | null | undefined, alpha: number): string {
  const map: Record<string, string> = {
    news_stream: `rgba(0, 229, 255, ${alpha})`,
    politician: `rgba(255, 149, 0, ${alpha})`,
    market_data: `rgba(29, 161, 242, ${alpha})`,
  };
  return source && map[source] ? map[source] : `rgba(245, 245, 247, ${alpha})`;
}

interface HistoryPoint {
  time: number;
  value: number;
  source: string | null;
}

interface SentimentHistoryProps {
  history: SentimentUpdate[];
}

const RANGES = [
  { label: "5m", minutes: 5 },
  { label: "15m", minutes: 15 },
  { label: "30m", minutes: 30 },
  { label: "All", minutes: 60 },
];

export function SentimentHistory({ history }: SentimentHistoryProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [selectedRange, setSelectedRange] = useState(5);
  const [hoverInfo, setHoverInfo] = useState<{
    x: number; y: number; time: string; value: string; source: string;
  } | null>(null);
  const rafRef = useRef<number | null>(null);

  // Build data from history prop
  const data: HistoryPoint[] = [...history]
    .reverse()
    .map((entry) => ({
      time: new Date(entry.timestamp).getTime(),
      value: entry.sentiment_score,
      source: entry.drivers[0]?.source ?? null,
    }));

  // Event markers — pick entries with strong drivers
  const markers: HistoryPoint[] = data.filter(
    (_, i) => history[history.length - 1 - i]?.drivers.some(
      (d) => Math.abs(d.sentiment_score) > 60,
    ),
  );

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;

    const dpr = window.devicePixelRatio || 1;
    const w = wrapper.clientWidth;
    const h = wrapper.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    ctx.clearRect(0, 0, w, h);

    const pad = { top: 20, right: 20, bottom: 40, left: 56 };
    const cw = w - pad.left - pad.right;
    const ch = h - pad.top - pad.bottom;

    // Filter by range
    const now = Date.now();
    const rangeMs = selectedRange * 60 * 1000;
    const visible = data.filter((d) => now - d.time < rangeMs);

    if (visible.length < 2) {
      ctx.fillStyle = C.muted;
      ctx.font = "500 13px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Awaiting sentiment data…", w / 2, h / 2);
      return;
    }

    const tMin = visible[0].time;
    const tMax = visible[visible.length - 1].time;
    const tSpan = Math.max(tMax - tMin, 1000);

    const toX = (t: number) => pad.left + ((t - tMin) / tSpan) * cw;
    const toY = (v: number) => pad.top + ch / 2 - (v / 100) * (ch / 2);

    // Horizontal grid
    ctx.strokeStyle = C.gridLine;
    ctx.lineWidth = 1;
    for (const v of [-100, -50, 0, 50, 100]) {
      const y = toY(v);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      ctx.fillStyle = C.muted;
      ctx.font = '500 10px "JetBrains Mono", monospace';
      ctx.textAlign = "right";
      ctx.fillText(String(v), pad.left - 8, y + 4);
    }

    // Zero line
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, toY(0));
    ctx.lineTo(w - pad.right, toY(0));
    ctx.stroke();
    ctx.setLineDash([]);

    // Gradient fill
    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
    grad.addColorStop(0, "rgba(48, 209, 88, 0.15)");
    grad.addColorStop(0.45, "rgba(255, 214, 10, 0.05)");
    grad.addColorStop(0.55, "rgba(255, 214, 10, 0.05)");
    grad.addColorStop(1, "rgba(255, 45, 85, 0.15)");

    ctx.beginPath();
    ctx.moveTo(toX(visible[0].time), toY(0));
    visible.forEach((d, i) => {
      if (i === 0) {
        ctx.lineTo(toX(d.time), toY(d.value));
      } else {
        const prev = visible[i - 1];
        const cpx = (toX(prev.time) + toX(d.time)) / 2;
        ctx.bezierCurveTo(cpx, toY(prev.value), cpx, toY(d.value), toX(d.time), toY(d.value));
      }
    });
    ctx.lineTo(toX(visible[visible.length - 1].time), toY(0));
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Main line
    ctx.beginPath();
    visible.forEach((d, i) => {
      if (i === 0) {
        ctx.moveTo(toX(d.time), toY(d.value));
      } else {
        const prev = visible[i - 1];
        const cpx = (toX(prev.time) + toX(d.time)) / 2;
        ctx.bezierCurveTo(cpx, toY(prev.value), cpx, toY(d.value), toX(d.time), toY(d.value));
      }
    });
    const lineGrad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
    lineGrad.addColorStop(0, C.bullish);
    lineGrad.addColorStop(0.5, C.neutral);
    lineGrad.addColorStop(1, C.bearish);
    ctx.strokeStyle = lineGrad;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    // Glow on line
    ctx.shadowColor = "rgba(0, 229, 255, 0.3)";
    ctx.shadowBlur = 8;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.08)";
    ctx.lineWidth = 6;
    ctx.beginPath();
    visible.forEach((d, i) => {
      if (i === 0) ctx.moveTo(toX(d.time), toY(d.value));
      else {
        const prev = visible[i - 1];
        const cpx = (toX(prev.time) + toX(d.time)) / 2;
        ctx.bezierCurveTo(cpx, toY(prev.value), cpx, toY(d.value), toX(d.time), toY(d.value));
      }
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Event markers
    const visMarkers = markers.filter((m) => now - m.time < rangeMs);
    for (const m of visMarkers) {
      const mx = toX(m.time);
      const my = toY(m.value);

      ctx.strokeStyle = sourceColor(m.source, 0.2);
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(mx, pad.top);
      ctx.lineTo(mx, pad.top + ch);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.shadowColor = sourceColor(m.source, 0.6);
      ctx.shadowBlur = 10;
      ctx.fillStyle = sourceColor(m.source, 1);
      ctx.beginPath();
      ctx.arc(mx, my, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.strokeStyle = sourceColor(m.source, 0.4);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(mx, my, 9, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Pulsing current-value dot
    if (visible.length > 0) {
      const last = visible[visible.length - 1];
      const lx = toX(last.time);
      const ly = toY(last.value);
      const pulse = 1 + 0.3 * Math.sin(Date.now() / 400);

      ctx.shadowColor = sentimentColor(last.value);
      ctx.shadowBlur = 12 * pulse;
      ctx.fillStyle = sentimentColor(last.value);
      ctx.beginPath();
      ctx.arc(lx, ly, 4 * pulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.strokeStyle = sentimentColor(last.value);
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.3 * (1 + Math.sin(Date.now() / 600)) / 2;
      ctx.beginPath();
      ctx.arc(lx, ly, 12 * pulse, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Time labels (x-axis)
    ctx.fillStyle = C.muted;
    ctx.font = '500 10px "JetBrains Mono", monospace';
    ctx.textAlign = "center";
    const labelCount = Math.min(6, visible.length);
    for (let i = 0; i < labelCount; i++) {
      const idx = Math.floor(i * (visible.length - 1) / (labelCount - 1));
      const d = visible[idx];
      const x = toX(d.time);
      const label = new Date(d.time).toLocaleTimeString("en-US", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
      ctx.fillText(label, x, h - 12);
    }

    rafRef.current = requestAnimationFrame(draw);
  }, [data, markers, selectedRange]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(draw);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [draw]);

  // Tooltip handler
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const w = canvas.clientWidth;
      const pad = { left: 56, right: 20 };
      const cw = w - pad.left - pad.right;

      const now = Date.now();
      const rangeMs = selectedRange * 60 * 1000;
      const visible = data.filter((d) => now - d.time < rangeMs);
      if (visible.length < 2) return;

      const tMin = visible[0].time;
      const tMax = visible[visible.length - 1].time;
      const tSpan = Math.max(tMax - tMin, 1000);

      let closest = 0;
      let minDist = Infinity;
      visible.forEach((d, i) => {
        const x = pad.left + ((d.time - tMin) / tSpan) * cw;
        const dist = Math.abs(x - mouseX);
        if (dist < minDist) { minDist = dist; closest = i; }
      });

      if (minDist < 40) {
        const d = visible[closest];
        const x = pad.left + ((d.time - tMin) / tSpan) * cw;
        const sign = d.value > 0 ? "+" : "";
        setHoverInfo({
          x: Math.min(x + 12, w - 160),
          y: 30,
          time: new Date(d.time).toLocaleTimeString(),
          value: sign + d.value.toFixed(1),
          source: d.source ? `Source: ${d.source}` : "",
        });
      } else {
        setHoverInfo(null);
      }
    },
    [data, selectedRange],
  );

  return (
    <section className="panel mp-chart-zone">
      <div className="mp-chart-header">
        <div>
          <p className="eyebrow">Sentiment Timeline</p>
        </div>
        <div className="mp-chart-controls">
          {RANGES.map((r) => (
            <button
              key={r.minutes}
              type="button"
              className={`mp-chart-btn${selectedRange === r.minutes ? " mp-chart-btn--active" : ""}`}
              onClick={() => setSelectedRange(r.minutes)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mp-chart-wrapper" ref={wrapperRef}>
        <canvas
          ref={canvasRef}
          style={{ cursor: "crosshair" }}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverInfo(null)}
        />
        {hoverInfo && (
          <div
            className="mp-chart-tooltip mp-chart-tooltip--visible"
            style={{ left: hoverInfo.x, top: hoverInfo.y }}
          >
            <div className="mp-tooltip-time">{hoverInfo.time}</div>
            <div
              className="mp-tooltip-value"
              style={{ color: sentimentColor(parseFloat(hoverInfo.value)) }}
            >
              {hoverInfo.value}
            </div>
            {hoverInfo.source && <div className="mp-tooltip-source">{hoverInfo.source}</div>}
          </div>
        )}
      </div>

      <div className="mp-chart-legend">
        <div className="mp-legend-item">
          <span className="mp-legend-dot mp-legend-dot--broadcast" />News Stream
        </div>
        <div className="mp-legend-item">
          <span className="mp-legend-dot mp-legend-dot--political" />Political
        </div>
        <div className="mp-legend-item">
          <span className="mp-legend-dot mp-legend-dot--market" />Market Data
        </div>
        <div className="mp-legend-item">
          <span className="mp-legend-dot mp-legend-dot--composite" />Composite
        </div>
      </div>
    </section>
  );
}
