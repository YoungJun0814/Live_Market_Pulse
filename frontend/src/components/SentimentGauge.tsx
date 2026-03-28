import { useRef } from "react";
import type { SentimentUpdate } from "../types";

interface SentimentGaugeProps {
  sentiment: SentimentUpdate;
  signalCount?: number;
  delta5min?: number | null;
}

/* ── gauge geometry ── */
const CX = 200;
const CY = 220;
const RADIUS = 150;
const START_ANGLE = Math.PI;      // 180° (left)
const END_ANGLE = 2 * Math.PI;   // 360° (right)
const ARC_LENGTH = RADIUS * Math.PI;

function describeArc(
  cx: number, cy: number, r: number, startAngle: number, endAngle: number,
): string {
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const large = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

function buildTicks(): { x1: number; y1: number; x2: number; y2: number; major: boolean }[] {
  const vals = [-100, -75, -50, -25, 0, 25, 50, 75, 100];
  return vals.map((v) => {
    const frac = (v + 100) / 200;
    const angle = START_ANGLE + frac * (END_ANGLE - START_ANGLE);
    const major = v % 50 === 0;
    const innerR = RADIUS - (major ? 24 : 18);
    const outerR = RADIUS - 10;
    return {
      x1: CX + innerR * Math.cos(angle),
      y1: CY + innerR * Math.sin(angle),
      x2: CX + outerR * Math.cos(angle),
      y2: CY + outerR * Math.sin(angle),
      major,
    };
  });
}

function sentimentColor(v: number): string {
  if (v < -50) return "#FF2D55";
  if (v < -20) return "#FF9500";
  if (v > 50) return "#30D158";
  if (v > 20) return "#30D158";
  return "#FFD60A";
}

function badgeInfo(v: number): { label: string; cls: string } {
  if (v < -50) return { label: "EXTREME FEAR", cls: "mp-badge mp-badge--bearish" };
  if (v < -20) return { label: "BEARISH", cls: "mp-badge mp-badge--bearish" };
  if (v > 50) return { label: "EXTREME GREED", cls: "mp-badge mp-badge--bullish" };
  if (v > 20) return { label: "BULLISH", cls: "mp-badge mp-badge--bullish" };
  return { label: "NEUTRAL", cls: "mp-badge mp-badge--neutral" };
}

function stateClass(v: number): string {
  if (v < -20) return "mp-gauge-zone--bearish";
  if (v > 20) return "mp-gauge-zone--bullish";
  return "mp-gauge-zone--neutral";
}

const arcD = describeArc(CX, CY, RADIUS, START_ANGLE, END_ANGLE);
const TICKS = buildTicks();

export function SentimentGauge({ sentiment, signalCount = 0, delta5min }: SentimentGaugeProps) {
  const prevRef = useRef(0);
  const value = sentiment.sentiment_score;
  const clamped = Math.max(-100, Math.min(100, value));

  // Track previous value for smooth CSS transitions (the SVG transition handles it)
  prevRef.current = clamped;

  // Derived values
  const fraction = (clamped + 100) / 200;
  const offset = ARC_LENGTH * (1 - fraction);

  const needleAngle = START_ANGLE + fraction * (END_ANGLE - START_ANGLE);
  const needleLen = RADIUS - 30;
  const nx = CX + needleLen * Math.cos(needleAngle);
  const ny = CY + needleLen * Math.sin(needleAngle);

  const color = sentimentColor(clamped);
  const sign = clamped > 0 ? "+" : "";
  const badge = badgeInfo(clamped);
  const zoneState = stateClass(clamped);

  const textColorClass =
    clamped < -20 ? "mp-gauge-text--bearish" :
    clamped > 20 ? "mp-gauge-text--bullish" : "mp-gauge-text--neutral";

  const deltaSign = delta5min != null && delta5min > 0 ? "+" : "";
  const deltaColor =
    delta5min != null
      ? delta5min > 0 ? "#30D158" : delta5min < 0 ? "#FF2D55" : "#FFD60A"
      : undefined;

  return (
    <section className={`panel mp-gauge-zone ${zoneState}`}>
      <div className="mp-gauge-header">
        <div>
          <p className="eyebrow">Sentiment Score</p>
        </div>
        <div className={badge.cls}>{badge.label}</div>
      </div>

      <div className="mp-gauge-wrapper">
        <svg viewBox="0 0 400 280" className="mp-gauge-svg">
          <defs>
            <linearGradient id="mpArcGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#FF2D55" />
              <stop offset="25%" stopColor="#FF6B35" />
              <stop offset="50%" stopColor="#FFD60A" />
              <stop offset="75%" stopColor="#30D158" />
              <stop offset="100%" stopColor="#00E5FF" />
            </linearGradient>
            <filter id="mpArcGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="mpNeedleGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="mpTextShadow">
              <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="currentColor" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Background track */}
          <path d={arcD} className="mp-gauge-bg" />

          {/* Coloured arc */}
          <path
            d={arcD}
            className="mp-gauge-value"
            filter="url(#mpArcGlow)"
            style={{
              strokeDasharray: ARC_LENGTH,
              strokeDashoffset: offset,
            }}
          />

          {/* Tick marks */}
          <g className="mp-gauge-ticks">
            {TICKS.map((t, i) => (
              <line
                key={i}
                x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
                style={{ strokeWidth: t.major ? 2 : 1 }}
              />
            ))}
          </g>

          {/* Needle */}
          <g filter="url(#mpNeedleGlow)">
            <line
              x1={CX} y1={CY} x2={nx} y2={ny}
              className="mp-gauge-needle"
              style={{ stroke: color }}
            />
            <circle cx={CX} cy={CY} r={8} className="mp-gauge-cap" />
            <circle cx={CX} cy={CY} r={4} className="mp-gauge-cap-inner" style={{ fill: color }} />
          </g>

          {/* Value */}
          <text x={200} y={195} className={`mp-gauge-value-text ${textColorClass}`} filter="url(#mpTextShadow)">
            {sign}{Math.round(clamped)}
          </text>
          <text x={200} y={260} className="mp-gauge-label-text">MARKET SENTIMENT</text>

          {/* Min / max */}
          <text x={48} y={240} className="mp-gauge-range mp-gauge-range--min">-100</text>
          <text x={352} y={240} className="mp-gauge-range mp-gauge-range--max">+100</text>
        </svg>

        {/* Sub-metrics */}
        <div className="mp-gauge-metrics">
          <div className="mp-metric-card">
            <span className="mp-metric-label">Confidence</span>
            <span className="mp-metric-value">{sentiment.confidence}%</span>
          </div>
          <div className="mp-metric-card">
            <span className="mp-metric-label">Signals</span>
            <span className="mp-metric-value">{signalCount}</span>
          </div>
          <div className="mp-metric-card">
            <span className="mp-metric-label">Δ 5min</span>
            <span className="mp-metric-value" style={deltaColor ? { color: deltaColor } : undefined}>
              {delta5min != null ? `${deltaSign}${delta5min.toFixed(1)}` : "—"}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
