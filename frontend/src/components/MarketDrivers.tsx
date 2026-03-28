import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { MarketPoint, MarketSnapshot } from "../types";

interface MarketDriversProps {
  snapshot: MarketSnapshot;
}

function buildSeries(point?: MarketPoint | null) {
  const current = point?.price ?? point?.yield ?? 0;
  const change = point?.change_pct ?? point?.change_bps ?? 0;
  const start = current - change;

  return Array.from({ length: 6 }, (_, index) => ({
    step: index,
    value: Number((start + ((current - start) * index) / 5).toFixed(2)),
  }));
}

function getTone(delta: number, invert = false) {
  const adjusted = invert ? -delta : delta;
  if (adjusted > 0.05) {
    return {
      stroke: "#30d158",
      fillTop: "rgba(48, 209, 88, 0.42)",
      fillBottom: "rgba(48, 209, 88, 0.02)",
      className: "market-tile__delta market-tile__delta--bullish",
    };
  }
  if (adjusted < -0.05) {
    return {
      stroke: "#ff453a",
      fillTop: "rgba(255, 69, 58, 0.42)",
      fillBottom: "rgba(255, 69, 58, 0.02)",
      className: "market-tile__delta market-tile__delta--bearish",
    };
  }
  return {
    stroke: "#6be3ff",
    fillTop: "rgba(107, 227, 255, 0.42)",
    fillBottom: "rgba(107, 227, 255, 0.02)",
    className: "market-tile__delta market-tile__delta--neutral",
  };
}

function MarketDriverTile({
  label,
  value,
  delta,
  series,
  tone,
}: {
  label: string;
  value: string;
  delta: string;
  series: { step: number; value: number }[];
  tone: ReturnType<typeof getTone>;
}) {
  const gradientId = `marketGradient-${label.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;

  return (
    <article className="market-tile">
      <div className="market-tile__header">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className={tone.className}>{delta}</div>
      <div className="market-tile__chart">
        <ResponsiveContainer width="100%" height={84}>
          <AreaChart data={series}>
            <Tooltip
              contentStyle={{
                background: "rgba(7, 14, 24, 0.96)",
                border: "1px solid rgba(108, 153, 204, 0.35)",
                borderRadius: "12px",
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={tone.stroke}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
            />
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={tone.fillTop} />
                <stop offset="95%" stopColor={tone.fillBottom} />
              </linearGradient>
            </defs>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

export function MarketDrivers({ snapshot }: MarketDriversProps) {
  const cards = [
    {
      label: "S&P 500",
      value: snapshot.sp500?.price?.toLocaleString() ?? "N/A",
      delta: `${snapshot.sp500?.change_pct?.toFixed(2) ?? "0.00"}%`,
      series: buildSeries(snapshot.sp500),
      tone: getTone(snapshot.sp500?.change_pct ?? 0),
    },
    {
      label: "NASDAQ",
      value: snapshot.nasdaq?.price?.toLocaleString() ?? "N/A",
      delta: `${snapshot.nasdaq?.change_pct?.toFixed(2) ?? "0.00"}%`,
      series: buildSeries(snapshot.nasdaq),
      tone: getTone(snapshot.nasdaq?.change_pct ?? 0),
    },
    {
      label: "VIX",
      value: snapshot.vix?.price?.toFixed(2) ?? "N/A",
      delta: `${snapshot.vix?.change_pct?.toFixed(2) ?? "0.00"}%`,
      series: buildSeries(snapshot.vix),
      tone: getTone(snapshot.vix?.change_pct ?? 0, true),
    },
    {
      label: "Gold",
      value: snapshot.gold?.price?.toFixed(2) ?? "N/A",
      delta: `${snapshot.gold?.change_pct?.toFixed(2) ?? "0.00"}%`,
      series: buildSeries(snapshot.gold),
      tone: getTone(snapshot.gold?.change_pct ?? 0),
    },
    {
      label: "WTI Oil",
      value: snapshot.oil?.price?.toFixed(2) ?? "N/A",
      delta: `${snapshot.oil?.change_pct?.toFixed(2) ?? "0.00"}%`,
      series: buildSeries(snapshot.oil),
      tone: getTone(snapshot.oil?.change_pct ?? 0),
    },
    {
      label: "US 10Y",
      value: snapshot.us10y?.yield?.toFixed(2) ?? "N/A",
      delta: `${snapshot.us10y?.change_bps?.toFixed(1) ?? "0.0"} bps`,
      series: buildSeries(snapshot.us10y),
      tone: getTone(snapshot.us10y?.change_bps ?? 0),
    },
  ];

  return (
    <section className="panel panel--drivers">
      <div className="panel__heading">
        <p className="eyebrow">Zone 4 - Core Indicators</p>
        <h2>Market Drivers</h2>
      </div>
      <div className="market-grid">
        {cards.map((card) => (
          <MarketDriverTile key={card.label} {...card} />
        ))}
      </div>
    </section>
  );
}
