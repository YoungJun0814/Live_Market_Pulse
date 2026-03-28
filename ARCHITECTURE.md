# Live Market Pulse Architecture

## One-line summary

Live Market Pulse collects economic RSS, political RSS, and 5-layer market data, converts them into normalized sentiment signals, aggregates them in a central hub, and streams the result to a React dashboard in real time.

## Slide-ready architecture

```mermaid
flowchart LR
  subgraph External["External Data Sources"]
    EconRSS["Google News / Economic RSS"]
    PolRSS["Political RSS Feed"]
    Gemini["Gemini API\n(optional fact-check + impact analysis)"]
    Yahoo["Yahoo Finance"]
    FRED["FRED API"]
    CNN["CNN Fear & Greed / Alternative.me"]
    Trends["Google Trends"]
  end

  subgraph Ingestion["Signal Ingestion Layer"]
    EconCollector["rss_econ_collector.py\nkeyword-based scoring"]
    PolCollector["rss_political_collector.py"]
    Checker["politician_checker.py\nGemini + heuristic fallback"]
  end

  subgraph Analytics["Market Analytics Layer"]
    MarketEngine["market_engine.py\n5-layer market sentiment engine"]
  end

  subgraph Hub["Central Hub Backend"]
    Api["main.py\nFastAPI + /api/signal + /api/latest"]
    Queue["signal_queue.py\nTTL queue by source"]
    Scheduler["scheduler.py\n30s aggregation scheduler"]
    SocketHub["websocket_server.py\nSocket.IO event broadcaster"]
    Profiles["data/country_profiles.json"]
  end

  subgraph Frontend["Frontend Dashboard"]
    WS["useWebSocket.ts\nSocket.IO client"]
    State["useSentiment.ts\nstate + history + focus events"]
    UI["React UI\nMap / Gauge / Reasoning / Feed / Market cards"]
    Demo["DemoControls.tsx\nmanual signal injection"]
  end

  EconRSS --> EconCollector
  PolRSS --> PolCollector
  PolCollector --> Checker
  Gemini -.optional.-> Checker

  Yahoo --> MarketEngine
  FRED --> MarketEngine
  CNN --> MarketEngine
  Trends --> MarketEngine

  EconCollector -->|POST /api/signal| Api
  Checker -->|POST /api/signal| Api

  Api --> Queue
  Scheduler --> Queue
  Scheduler --> MarketEngine
  Profiles --> Scheduler
  Scheduler --> SocketHub

  SocketHub -->|sentiment_update / focus_region| WS
  WS --> State
  State --> UI
  Demo -->|POST /api/signal| Api
```

## Runtime flow

```mermaid
sequenceDiagram
  participant ER as Econ RSS Collector
  participant PR as Political RSS Collector
  participant PC as Politician Checker
  participant HUB as Central Hub API
  participant Q as Signal Queue
  participant SCH as Hub Scheduler
  participant ME as Market Engine
  participant WS as Socket Hub
  participant FE as React Frontend

  ER->>HUB: POST news_stream signal
  PR->>PC: Raw political article
  PC->>HUB: POST politician signal
  HUB->>Q: Store signal by source

  loop Every 30 seconds
    SCH->>Q: Read latest per source
    SCH->>ME: Load market_data payload
    ME-->>SCH: market_data signal
    SCH->>SCH: Weighted sentiment aggregation
    SCH->>WS: Emit sentiment_update
    SCH->>WS: Emit focus_region if strong location event
  end

  WS-->>FE: Real-time Socket.IO updates
  FE->>FE: Update map, gauge, history, feed, market cards
```

## Key design points

- The central hub is the orchestration core. It receives normalized signals, keeps only fresh signals in a TTL queue, and creates one unified `SentimentUpdate`.
- Market data is not pushed in from an external worker. The scheduler pulls it directly from `market_engine.py` during each aggregation cycle.
- Political signals are richer than the others: they include fact-check status, affected sectors, and optional event coordinates for map focus.
- The frontend is event-driven. It does not poll for updates; it subscribes to Socket.IO events and updates dashboard state in real time.
- Country-level side panels are enriched with static metadata from `data/country_profiles.json`.

## Suggested presentation framing

1. Data collection: RSS feeds and market sources are converted into three normalized signal types.
2. AI analysis: political content is fact-checked and market impact is estimated before entering the hub.
3. Aggregation: the hub combines market, news, and political signals into one weighted sentiment score.
4. Real-time delivery: Socket.IO pushes the result to the dashboard for live visualization.
