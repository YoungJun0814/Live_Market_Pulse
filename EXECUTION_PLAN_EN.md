# Live Market Pulse — Execution Plan (v7 Final · Hackathon Day)

> **Changelog**:
> v1 → v2: Promoted Fishjam/Smelter, included full features from pre-MVP, added session explanations
> v2 → v3: Unified sentiment_score (-100~+100), reassigned roles, added Neutral, finalized market data logic
> v3 → v4 (2026-03-28): Hackathon Day Final Version
>   - Removed pre-MVP section (will implement directly on the day)
>   - News Source: Dual strategy using Bloomberg (Primary) + Sky News (24/7 fallback)
>   - Tamas: Bloomberg/Sky News + Finance/Econ RSS / Tim: Politics/Twitter RSS strictly
>   - Andy: Adopted 5-Layer engine for market_engine.py → `backend/market_engine.py`
>   - Architecture: Integrated (Method B, shared via GitHub)
>   - Dashboard: 6-area layout + 2D Map event markers
>   - Saturday Demo Strategy: Record 2 hours of data on Friday + Demo trigger buttons
>   - Extract city-level location from news articles using Gemini (GKG not required)
> v4 → v5 (2026-03-28): Auto-Pilot Broadcast Mode added
>   - 2D Map: Auto-highlight new events with Pulse marker animation
>   - Country/Marker click → Right-side semi-transparent Country News Panel slide-in
>   - `focus_region` WebSocket event + autopilot trigger threshold/cooldown logic
>   - `country_profiles.json` static data (10 countries, key indicators)
>   - Autopilot trigger logic added to Central Hub
> v5 → v6 (2026-03-28): Fishjam × Smelter Deep Integration
>   - Section 7: Added full Agent SDK + Gemini Integration code (Tamas implementation reference)
>   - Section 7: Added Smelter React scene code + WHIP output config + WHEP frontend player
>   - Section 7: Added Naive vs Deep Integration comparison table + Tamas spec modifications
>   - Tech Stack: Separated Smelter Server (Node.js) as its own category, added `fishjam-server-sdk[gemini]`
>   - Directory: Added `smelter/` directory + `fishjam_audio_agent.py`
>   - Timeline: Hour 3-4 expanded with Smelter→WHIP→Fishjam→WHEP verification step
> v6 → v7 (2026-03-28): RSS Pivot for Tamas & Tim
>   - Replaced GDELT inputs with RSS feeds for Tamas (Finance/Econ) and Tim (Politics/Twitter)
>   - Tamas RSS source fixed to Google News Finance/Economics feed
>   - Tim RSS source fixed to rss.app Iran/Israel politics feed
>   - Renamed planned collectors to `rss_econ_collector.py` and `rss_political_collector.py`
>   - Andy's `market_engine.py` remains unchanged

---

## Project Overview

Real-time multimodal dashboard. Fuses financial news broadcasts (Bloomberg/Sky News) + RSS-based finance/politics headlines + market data to predict financial market sentiment (Bullish/Neutral/Bearish, -100~+100).

**Key Differentiator**: Real-time transmission of news broadcast audio to Gemini Live API via Fishjam, combined with Smelter overlaying sentiment graphics onto the video as the core visual demo.

**News Source Strategy**: Bloomberg (Finance specialist, prioritized during market hours) → Sky News (24/7 uninterrupted, fallback) + supplemental RSS feeds for finance/economics and politics.
**Saturday Demo**: Pre-record 2 hours of live market data on Friday + Real-time simulation using Demo Trigger buttons.

---

## 1. Team Structure & Roles

| Name | Role | Responsibilities | Output Delivered |
|------|------|------------------|------------------|
| **Jun** | Team Lead / Architecture | Central Hub, Gemini Inference Engine, 2D Map (Event Markers), Pipeline Integration | Final sentiment_score (Overall) |
| **Tamas** | News Stream | Bloomberg/Sky News (Fishjam→Gemini STT+Sentiment) + **Finance/Econ RSS** → sentiment_score | `sentiment_score: -100~+100` |
| **Tim** | Political Intelligence | **Politics/Twitter RSS** → Gemini Fact-check+Location Extraction → sentiment_score | `sentiment_score: -100~+100` |
| **Andy** | Market Data + Frontend | `backend/market_engine.py` (5-Layer) + Build entire Frontend | `sentiment_score: -100~+100` |

### Rationale for Role Distribution
- **Tamas**: Bloomberg/Sky News (Economic news broadcast) + Google News Finance/Econ RSS = Same category → Summarized into a single `sentiment_score`
- **Tim**: Politics/Twitter RSS feed = Focus strictly on policy headlines and geopolitical narratives → Gemini fact-check + city location extraction yields `sentiment_score`
- **Andy**: Moved 1235-line 5-Layer engine to `backend/market_engine.py`. Central Hub imports it via `from market_engine import MarketSentimentEngine`

---

## 2. Core Concepts Explained

### What is a "Session"?

| Category | Analogy | How it Works |
|----------|---------|--------------|
| **Standard Gemini API** | 📮 Letter | 1 Request → 1 Response → End. Does not remember past conversation. |
| **Gemini Live API Session** | 📞 Phone Call | Session opens → Keep talking → Keep answering → Maintained until hung up. Remembers previous context. |

**Why two sessions?**
- **Session A (Tamas)**: Continually streams Sky News audio for real-time STT + sentiment analysis.
- **Session B (Jun)**: Continually injects all derived data for synthesized, overall assessments.

---

## 3. System Architecture (Hackathon Day)

> **Architecture Approach: Method B (Built-in)**
> Import and run all modules on a single server. Share code via GitHub → Individual pushes → Jun pulls and runs it all together.

```text
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
├──────────────────┬──────────────────┬────────────────────────┤
│ Bloomberg/Sky News│ Politics/Twitter │ Market Data            │
│ + Finance RSS     │ RSS (Tim)        │ (Andy — 5-Layer Eng.)  │
│ (Tamas)           │                  │                        │
└────────┬─────────┴────────┬─────────┴────────┬───────────────┘
         │                  │                  │
         ▼                  ▼                  │
┌──────────────────┐ ┌──────────────┐          │
│ Fishjam          │ │ RSS Feed Poller │        │
│ (WebRTC Ingest)  │ │ + Article Fetch │        │
│ Audio Collection  │ └──────┬─────────┘        │
└───┬──────────┬───┘        │                  │
    │          │             │                  │
    │     Extract Audio      │                  │
    │          │             │                  │
    │          ▼             ▼                  │
    │  ┌───────────────┐ ┌──────────────┐      │
    │  │ Gemini Live   │ │ Gemini API   │      │
    │  │ API Session A │ │ (Fact-check)  │      │
    │  │ (STT+Sentiment)│ │              │     │
    │  └───────┬───────┘ └──────┬───────┘      │
    │          │                │               │
    │          ▼                ▼               ▼
    │  ┌──────────────────────────────────────────────────┐
    │  │           CENTRAL HUB (Python FastAPI)            │
    │  │                                                    │
    │  │  Source Weights: market(0.40) news(0.35) pol(0.25) │
    │  │  Andy's engine is imported natively                 │
    │  │                      │                             │
    │  │          ┌───────────┴───────────┐                 │
    │  │          │  Gemini Live API      │                 │
    │  │          │  Session B (Inference)│                 │
    │  │          │  Maintains Context    │                 │
    │  │          └───────────┬───────────┘                 │
    │  │                      ▼                             │
    │  │           JSON Output Generation                    │
    │  └──────────────┬───────────────────────────────────┘
    │                 │ WebSocket (socket.io)
    │                 ├──────────────────────────────────┐
    │                 ▼                                  ▼
    │  ┌──────────────────────────────┐  ┌──────────────────────────────┐
    │  │  SMELTER SERVER (Node.js)    │  │                              │
    │  │                              │  │                              │
    │  │  Input: News Video (Fishjam) │  │                              │
    │  │       + Sentiment JSON (WS)  │  │                              │
    │  │                              │  │                              │
    │  │  React component compositing │  │                              │
    │  │  → Video frame overlay bake  │  │                              │
    │  │                              │  │                              │
    │  │  Output: WHIP ──────────┐    │  │                              │
    │  └─────────────────────────┼────┘  │                              │
    │                            │       │                              │
    │                            ▼       │                              │
    │  ┌──────────────────────────────┐  │                              │
    │  │  FISHJAM LIVESTREAM ROOM     │  │                              │
    │  │  (Receives composited stream) │  │                              │
    │  └──────────────┬───────────────┘  │                              │
    │                 │ WHEP             │                              │
    │                 ▼                  │                              │
    │  ┌──────────────────────────────────────────────────┐
    │  │            FRONTEND (React + Vite)                 │
    │  │                                                    │
    │  │  ┌──────────────────┐  ┌─────────────────────┐   │
    │  │  │ News Video       │  │ Sentiment Gauge     │   │
    │  │  │ (WHEP Player —   │  │ + Time-series Graph │   │
    │  │  │  composited by   │  ├─────────────────────┤   │
    │  │  │  Smelter)        │  │ Market Charts       │   │
    │  │  ├──────────────────┤  │ S&P, NASDAQ, VIX    │   │
    │  │  │ AI Signal Feed   │  ├─────────────────────┤   │
    │  │  │ (Driver List)    │  │ 2D Map (RSS Events) │   │
    │  │  │                  │  │ Geo-risk Markers    │   │
    │  │  └──────────────────┘  └─────────────────────┘   │
    │  └──────────────────────────────────────────────────┘
    │          ▲
    └──────────┘ (Fishjam WebRTC Video via WHEP)
```

---

## 4. Tech Stack

### Backend (Python)
| Tech | Purpose | Note |
|------|---------|------|
| **Python 3.11+** | Main Language | Confirmed |
| **FastAPI** | Central Hub API Server | Async support |
| **uvicorn** | ASGI Server | Runs FastAPI |
| **python-socketio** | WebSocket Server | socket.io protocol |
| **market_sentiment_engine.py** | Andy's 5-Layer Market Analysis Engine | Imported internally |
| **yfinance** | Market data collection (Inside Engine) | 60+ tickers |
| **fredapi** | FRED Macroeconomic data (Inside Engine) | 17 series |
| **google-genai** | Gemini Live API | Session A (STT), Session B (Inference) |
| **google-generativeai** | Gemini Generic API | Tim's Fact-checking |
| **yt-dlp** | YouTube Audio Extraction | For Sky News Stream |
| **apscheduler** | 30s Batch Scheduler | Data Convergence Timing |
| **feedparser** | RSS feed parsing | Tamas (Google News RSS) + Tim (rss.app feed) |
| **python-dotenv** | Environment Variables | API Key Security |
| **fishjam-server-sdk[gemini]** | Fishjam Agent + Gemini Live Integration | Audio bridge + auto sample rate matching |

### Frontend (React)
| Tech | Purpose | Note |
|------|---------|------|
| **React 18 + Vite** | Frontend Framework | TypeScript |
| **socket.io-client** | Receive backend WebSockets | Real-time updates |
| **Recharts** | Sentiment History Chart | React native chart |
| **Leaflet / react-leaflet** | 2D World Map | Show RSS-derived event markers |
| **@fishjam-cloud/react-client** | Fishjam WebRTC Stream Player | Display Sky News video |
| **framer-motion** | UI Animations | Gauges/Transitions |

### Smelter Server (Node.js — Server-Side Video Compositing)
| Tech | Purpose | Note |
|------|---------|------|
| **@swmansion/smelter** | Server-side video frame compositing | React component-based scene definition |
| **ffmpeg** (bundled) | H.264 Video Encoding | Required by Smelter for WHIP output stream |
| **WHIP → WHEP Protocol** | Push composited stream to Fishjam | Smelter → Fishjam Livestream Room → Frontend |

### External APIs & Services
| API | Key Req. | Cost | Purpose |
|-----|----------|------|---------|
| Gemini Live API | O | Provided for Hackathon | Real-time STT + Synthesis Inference Session |
| Gemini API (Classic) | O | Free | Tim fact-check |
| YouTube Data API v3 | O | Free (Quota) | Auto-detect Sky News Live URL |
| yfinance | X | Free | 60+ Market Tickers (Inside Andy's Engine) |
| FRED API | O | Free | Macroeconomic Indicators (Inside Andy's Engine) |
| Google News RSS | X | Free | Finance/Econ feed for Tamas |
| rss.app RSS Feed | X | Free/Paid | Politics/Twitter feed for Tim |
| Fishjam Cloud | O | Free Tier | WebRTC stream ingest/playback |
| Smelter | X | Completely Free | Video compositing overlay, self-hosted |

---

## 5. Data Interface Schema (JSON Contract Between Team Members)

> All team members compute a **unified `sentiment_score` (-100 ~ +100)** and POST to the Central Hub.
> Endpoint: `POST /api/signal`
>
> **Score rules:** `+100` = Extreme Bullish, `0` = Neutral, `-100` = Extreme Bearish

### 5-1. Tamas → Central Hub (Sky News + Finance/Econ RSS)
```json
{
  "source": "news_stream",
  "sentiment_score": 72,
  "confidence": 85,
  "signal": "Fed hints at rate pause in June meeting",
  "keywords": ["Fed", "rate", "pause"],
  "data_origin": "bloomberg",
  "segment_duration_sec": 30,
  "timestamp": "2026-03-28T14:32:00Z"
}
```
**Field Explanations:**
- `source`: Always `"news_stream"` (Bloomberg/Sky News + Finance/Econ RSS merged)
- `data_origin`: `"bloomberg"` | `"sky_news"` | `"google_news_rss"` (To track origin)
- `sentiment_score`: **-100 ~ +100** (Generated directly by Gemini)

### 5-2. Tim → Central Hub (Politics/Twitter RSS)
```json
{
  "source": "politician",
  "sentiment_score": -78,
  "confidence": 94,
  "signal": "Trump announces 50% tariffs on China starting Monday",
  "author": "Donald Trump",
  "platform": "rss",
  "tier": "president",
  "fact_check": "Real",
  "fact_check_reasoning": "Official White House schedule confirms meeting with trade advisors",
  "affected_sectors": ["trade", "manufacturing"],
  "event_location": {"lat": 38.9, "lon": -77.0, "city": "Washington DC", "country": "US"},
  "timestamp": "2026-03-28T14:33:00Z"
}
```
**Field Explanations:**
- `sentiment_score`: **-100 ~ +100** (Gemini reflects fact-check + impact. 0 if Fake)
- `event_location`: Coordinates for map markers (**Gemini extracts city from article and maps coordinates**)
- `tier`: "president" | "fed_chair" | "cabinet" | "senator" | "representative" | "other"

### 5-3. Andy → Central Hub (Market Data — 5-Layer Engine)
```json
{
  "source": "market_data",
  "sentiment_score": 10,
  "confidence": 75,
  "signal": "S&P +0.8%, VIX -3.1% — mild risk-on sentiment",
  "details": {
    "sp500": { "price": 5421.30, "change_pct": 0.8 },
    "vix": { "price": 18.2, "change_pct": -3.1 },
    "oil": { "price": 78.3, "change_pct": 1.2 },
    "dxy": { "price": 104.2, "change_pct": -0.3 },
    "gold": { "price": 2045.5, "change_pct": 0.5 },
    "us10y": { "yield": 4.25, "change_bps": -5 }
  },
  "market_status": "open",
  "timestamp": "2026-03-28T14:30:00Z"
}
```
**Field Explanations:**
- `sentiment_score`: **-100 ~ +100** (Calculated natively via Andy's 5-Layer Engine `compute_composite_score()`)
- Replaces simple §6-2 formula → fuses 5 layers (Price/Breadth/Options/Macro/Survey)

### 5-4. Central Hub → Frontend (Final Output)
```json
{
  "sentiment_score": 19,
  "overall_sentiment": "Neutral",
  "confidence": 62,
  "bullish_pct": 59.5,
  "previous_sentiment": "Bearish",
  "sentiment_change": "reversal",
  "drivers": [
    {
      "source": "news_stream",
      "sentiment_score": 72,
      "signal": "Fed hints at rate pause — Powell tone notably dovish",
      "weight": 0.35,
      "timestamp": "2026-03-28T14:32:00Z"
    },
    {
      "source": "politician",
      "sentiment_score": -78,
      "signal": "Trump announces 50% tariffs on China",
      "weight": 0.25,
      "fact_check": "Real (94%)",
      "timestamp": "2026-03-28T14:31:00Z"
    },
    {
      "source": "market_data",
      "sentiment_score": 10,
      "signal": "VIX drops 3.1%, S&P500 up 0.8%",
      "weight": 0.40,
      "timestamp": "2026-03-28T14:30:00Z"
    }
  ],
  "market_snapshot": {
    "sp500": { "price": 5421, "change_pct": 0.8 },
    "vix": { "price": 18.2, "change_pct": -3.1 },
    "oil": { "price": 78.3, "change_pct": 1.2 },
    "dxy": { "price": 104.2, "change_pct": -0.3 }
  },
  "reasoning": "Fed dovish tone is bullish, but Trump tariff announcement offsets this. Market indicators are slightly positive.",
  "data_freshness": {
    "news_last": "2026-03-28T14:32:00Z",
    "politician_last": "2026-03-28T14:31:00Z",
    "market_last": "2026-03-28T14:30:00Z"
  },
  "timestamp": "2026-03-28T14:32:30Z"
}
```
**Frontend Gauge Mapping:**
- `sentiment_score` → Gauge position (-100 ~ +100)
- `bullish_pct` = `(sentiment_score + 100) / 2` → Display percentage
- Thresholds: `+21~+100` = 🟢 Bullish, `-20~+20` = 🟡 Neutral, `-100~-21` = 🔴 Bearish

### 5-5. Central Hub → Frontend (Auto-Pilot Event)
> When a major event is detected, the Central Hub emits a separate `focus_region` WebSocket event.
> The frontend creates a Pulse marker at the target coordinates and auto-highlights the event.

```json
{
  "event": "focus_region",
  "lat": 38.9,
  "lon": -77.0,
  "city": "Washington DC",
  "country": "US",
  "trigger_signal": "Trump announces 50% tariffs on China",
  "sentiment_score": -78,
  "source": "politician",
  "country_data": {
    "stock_index": "S&P 500",
    "stock_value": 5421.30,
    "gdp_growth": 2.1,
    "cpi": 3.4
  }
}
```
**Trigger Conditions:**
```python
AUTOPILOT_THRESHOLD = 60   # |sentiment_score| ≥ 60 to trigger
AUTOPILOT_COOLDOWN_SEC = 30  # Minimum 30s between triggers
```

---

## 6. Weights & Scoring Design

### 6-1. Weights Among Sources (Hardcoded — `config.py`)
```python
SOURCE_WEIGHTS = {
    "market_data": 0.40,    # Most objective baseline
    "news_stream": 0.35,    # Sky News + Finance/Econ RSS
    "politician": 0.25      # Policy Signals (Post fact-check filter)
}

# Fallback redistribution if data is missing
FALLBACK_WEIGHTS = {
    "no_news": {"market_data": 0.55, "politician": 0.45},
    "no_politician": {"market_data": 0.55, "news_stream": 0.45},
    "only_market": {"market_data": 1.0}
}

# Sentiment Thresholds
SENTIMENT_THRESHOLDS = {
    "bullish": 21,    # +21 or higher = Bullish
    "bearish": -21,   # -21 or lower = Bearish
    # -20 ~ +20 = Neutral
}
```

### 6-2. Market Data Score (Andy's 5-Layer Engine)
> ⚠️ The simple `calculate_market_sentiment()` formula from v3 is **deleted**.
> Andy's `market_sentiment_engine.py` (1235 lines), specifically `compute_composite_score()`, replaces this.
>
> 5 Layers: Price Signals → Market Breadth → Options Market → Macro/FRED → Sentiment Surveys
> Internally outputs 0-100 → maps linearly to -100~+100 (`(score - 50) * 2`)
>
> Invoked cleanly on the Central Hub via `from market_sentiment_engine import MarketSentimentEngine`.

### 6-3. Intra-source Weights (Delegated to Gemini Prompts)
Instructions embedded directly into prompts:
- **Person Weight**: Sitting Presidents or Fed Chairs have 3x influence compared to standard legislators.
- **Fact Filter**: If `fact_check` == "Fake", set `sentiment_score` to 0.
- **Keyword Weights**: Sky News mentions of Fed/Interest Rate/Inflation/GDP/Employment → high impact.
- **Deduplication**: If multiple sources report the same event, don't double count → boost confidence.
- **Time Decay**: Data within 5 mins > Data 5-30 mins old > Data >30 mins.

---

## 7. Validating Fishjam / Smelter Roles

> **Core Principle**: Fishjam and Smelter must be **architecturally irreplaceable** — removing either breaks the system.
> Judges must conclude: "This team deeply understands and utilizes our technology."

### Naive vs Deep Integration Comparison

| Aspect | Naive Approach ❌ | Our Deep Integration ✅ |
|--------|------------------|------------------------|
| YouTube → Gemini | ffmpeg → direct WebSocket | Fishjam Agent → `fishjam.integrations.gemini` |
| Video Overlay | CSS `position:absolute` | Smelter server-side video compositing |
| Frontend Video | YouTube iframe embed | Fishjam WHEP Player (composited stream) |
| Audio Format | Manual PCM conversion | `GEMINI_INPUT_AUDIO_SETTINGS` auto-match |
| Multi-client | Each viewer opens YouTube | Fishjam SFU distributes once |
| Recording | Overlay disappears | Baked into video frames |
| Room Optimization | None | Audio-Only Room (75% cost saving) |

### 7-1. Fishjam (Audio→AI Pipeline + Gemini Built-in Integration)
```text
Bloomberg / Sky News YouTube Live
     │
     ▼
  youtube_resolver.py (Bloomberg prioritized, Sky News fallback)
     │
     ▼
  Fishjam (WebRTC Audio Stream Ingestion)
     │
     ├──→ Audio Track → Gemini Live API Session A (Real-time STT + Sentiment)
     │
     └──→ Video Track → Smelter (Compositing overlay) → Frontend Playback
```

**News Source Priority:**
```python
def get_live_url():
    bloomberg = try_bloomberg()  # Auto detect Bloomberg TV Live
    if bloomberg:
        return bloomberg, "bloomberg"
    return SKY_NEWS_URL, "sky_news"  # 24/7 un-interruptable fallback

SKY_NEWS_URL = "https://www.youtube.com/watch?v=YDvsBbKfLPA"
```

**Core Pitch**: Capitalizes on the official Fishjam ↔ Gemini Live API integration guide. 
→ Highlights to Judges: "We made SWM tech a fundamental core feature."

**Fishjam Agent SDK + Gemini Built-in Integration (Implementation Reference for Tamas):**
```python
# Installation: pip install "fishjam-server-sdk[gemini]"
from fishjam import FishjamClient, AgentOptions
from fishjam.integrations.gemini import GeminiIntegration
from google.genai.types import Blob, Modality

# 1. Client init — Fishjam's Gemini-specific helpers
fishjam_client = FishjamClient(fishjam_id=FISHJAM_ID, management_token=MGMT_TOKEN)
gen_ai = GeminiIntegration.create_client(api_key=GOOGLE_API_KEY)

# 2. Room + Agent — Gemini-compatible audio format auto-configured (16kHz)
room = fishjam_client.create_room()
agent_options = AgentOptions(output=GeminiIntegration.GEMINI_INPUT_AUDIO_SETTINGS)
agent = fishjam_client.create_agent(room.id, agent_options)

# 3. Bidirectional bridge — Fishjam ↔ Gemini
async with agent.connect() as fishjam_session:
    outgoing_track = await fishjam_session.add_track(
        GeminiIntegration.GEMINI_OUTPUT_AUDIO_SETTINGS  # 24kHz auto
    )
    
    async with gen_ai.aio.live.connect(
        model="gemini-2.0-flash",
        config={"response_modalities": [Modality.AUDIO]}
    ) as gemini_session:
        
        # Fishjam → Gemini (forward news audio)
        async def forward_audio_to_gemini():
            async for track_data in fishjam_session.receive():
                await gemini_session.send_realtime_input(
                    audio=Blob(
                        mime_type=GeminiIntegration.GEMINI_AUDIO_MIME_TYPE,
                        data=track_data.data
                    )
                )
        
        # Gemini → Fishjam (play AI response back to Room)
        async def forward_audio_to_fishjam():
            async for msg in gemini_session.receive():
                if msg.server_content and msg.server_content.model_turn:
                    for part in msg.server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            await outgoing_track.send_chunk(part.inline_data.data)
        
        await asyncio.gather(forward_audio_to_gemini(), forward_audio_to_fishjam())
```

**Why this is essential:**
- `GeminiIntegration.create_client()` → Auto sample rate matching (16kHz in / 24kHz out)
- `GEMINI_INPUT_AUDIO_SETTINGS` → Eliminates audio glitches from format mismatch
- Without Fishjam SDK: manual PCM conversion → garbled voice issues

**Talking point for judges:**
> "We used Fishjam's built-in Gemini integration module (`fishjam.integrations.gemini`)
> which automatically handles sample rate matching between Fishjam's WebRTC audio
> and Gemini's expected input format. Without this, we'd have audio glitches."

### 7-2. Smelter (Server-Side Video Compositing)
Used in Zone 3 "Live News" widget. **Not CSS overlay — actual video frame compositing.**

| Method | Implementation | Result |
|--------|---------------|--------|
| CSS `position:absolute` | div layered over video in browser | Recording loses overlay. Fake. |
| **Smelter** | Server composites onto video frames | **Recording preserves overlay. Real.** |

**Smelter React Scene Definition (Implementation Reference):**
```tsx
import { View, Text, InputStream, Rescaler } from '@swmansion/smelter';

function MarketOverlayScene({ sentiment, confidence, signal }) {
  const color = sentiment > 20 ? '#00FF88' : sentiment < -20 ? '#FF4444' : '#FFAA00';
  const label = sentiment > 20 ? 'BULLISH' : sentiment < -20 ? 'BEARISH' : 'NEUTRAL';
  
  return (
    <View style={{ direction: 'column', width: 1920, height: 1080 }}>
      {/* Background: news video fullscreen */}
      <Rescaler style={{ rescaleMode: 'fill' }}>
        <InputStream inputId="news_video" />
      </Rescaler>
      
      {/* Top-left: sentiment badge */}
      <View style={{ 
        position: 'absolute', top: 40, left: 40,
        backgroundColor: color, padding: 16, borderRadius: 8 
      }}>
        <Text style={{ fontSize: 28, fontWeight: 'bold', color: '#fff' }}>
          {label} {sentiment > 0 ? '+' : ''}{sentiment}
        </Text>
      </View>
      
      {/* Bottom ticker: latest signal */}
      <View style={{ 
        position: 'absolute', bottom: 0, left: 0, right: 0,
        backgroundColor: 'rgba(0,0,0,0.7)', padding: 12 
      }}>
        <Text style={{ fontSize: 22, color: '#fff' }}>
          🔴 LIVE ANALYSIS: {signal}
        </Text>
      </View>
    </View>
  );
}
```

**Dynamic Scene Updates (React State → Auto Video Frame Update):**
```tsx
function LiveOverlay() {
  const [sentiment, setSentiment] = useState(0);
  const [signal, setSignal] = useState('');
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/sentiment');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setSentiment(data.sentiment_score);
      setSignal(data.reasoning);
    };
    return () => ws.close();
  }, []);
  
  return <MarketOverlayScene sentiment={sentiment} signal={signal} />;
}
```

**WHIP Output → Fishjam Livestream (The Fishjam ↔ Smelter Bridge):**
```typescript
// smelter/server.ts
await smelter.registerOutput("market_broadcast", <MarketOverlayScene />, {
  type: "whip",
  endpointUrl: "https://fishjam.io/api/v1/live/api/whip",
  bearerToken: FISHJAM_STREAMER_TOKEN,
  video: {
    resolution: { width: 1920, height: 1080 },
    encoder: { type: "ffmpeg_h264" },
  },
  audio: {
    encoder: { type: "opus" }
  }
});
```

**Full compositing pipeline:**
```text
Smelter (composited video) ──WHIP──→ Fishjam Livestream Room ──WHEP──→ Frontend Player
```

**Frontend WHEP Player (receive composited stream):**
```tsx
import { useRemotePeers } from '@fishjam-cloud/react-client';

function LiveNewsPlayer() {
  const peers = useRemotePeers();
  const newsStream = peers.find(p => p.metadata?.role === 'news_ingester');
  
  return (
    <video 
      ref={ref => { if (ref && newsStream) ref.srcObject = newsStream.videoTrack }}
      autoPlay muted
    />
  );
}
```

**Talking point for judges:**
> "The overlay is not CSS — it's actual video compositing via Smelter.
> If you record this stream, the overlay persists. The composited output is pushed
> via WHIP to Fishjam and distributed to all viewers via WHEP."

### 7-3. Tamas Pipeline Spec Modifications

> Key changes from Tamas's original spec to align with the deep integration strategy:

| Original (Tamas Spec) | Modified |
|------------------------|----------|
| Docker self-hosted Fishjam | **Fishjam Cloud (SaaS)** — zero infra setup |
| `yt-dlp \| ffmpeg → RTP → Fishjam` | **Python Agent SDK → Fishjam Room** |
| Redis intermediate storage | **Agent streams directly to Gemini** |
| Manual Gemini WebSocket | **`fishjam-server-sdk[gemini]` built-in module** |
| Time-based Bloomberg/Sky switch | **Priority-based (`try_bloomberg() → fallback sky_news`)** |

---

## 8. Final Dashboard Layout

### Wireframe (6-Zone Grid + Country News Panel)

```text
┌─────────────────────────────────────────────────────────────┐
│                  LIVE MARKET PULSE             🔴 LIVE  UTC │ ← Header
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│  [Zone 1] 2D World Map       │  [Zone 2] Sentiment Score    │
│  (RSS Event Markers)         │  + Confidence Level          │
│                              │  + Time-series Graph         │
│  • Tariffs/Sanctions→🔴 High │  + AI Analysis (Reasoning)   │
│  • Political Tension→🟠 Elev.│                              │
│  • Economic Events  →🟢 Monit│  • Semicircle Gauge (Center) │
│  ★ New Events → Pulse Highl. │  • Hover inflection→AI reason│
│  ★ Marker Click → News Panel │                              │
│          ~50%                │          ~50%                │
│                              │                              │
├───────────────┬──────────────┴──────────────┬───────────────┤
│               │                             │               │
│  [Zone 3]     │  [Zone 4] Market Drivers    │  [Zone 5]     │
│  Live News    │  (Core Indicator Charts)    │  Political    │
│  Sky News     │                             │  News / AI    │
│  (Fishjam +   │  • S&P 500 Sparkline        │  Signal Feed  │
│   Smelter     │  • NASDAQ Sparkline         │               │
│   Overlay)    │  • VIX Gauge                │  • Fact-check │
│               │  • Gold / Oil               │  • Chrono Feed│
│     ~25%      │  • 10Y Yield                │     ~25%      │
│               │         ~50%                │               │
├───────────────┴─────────────────────────────┴───────────────┤
│  [Zone 6] 📰 Headlines Ticker: 24hr Billboard Scroll        │
└─────────────────────────────────────────────────────────────┘

                   Country Click Overlay:
┌─────────────────────────────────────┬───────────────────────┐
│                                     │ 🇺🇸 United States     │
│                                     │                       │
│    Dashboard (dimmed, blurred)      │  S&P 500: 5,421 ▲0.8%│
│    Click backdrop to close          │  GDP: 2.1%           │
│                                     │  CPI: 3.4%           │
│    backdrop: rgba(0,0,0,0.4)        │ ─────────────────── │
│    backdrop-filter: blur(4px)       │  📰 Related News Feed │
│                                     │  • Trump tariffs...  │
│                                     │  • Fed rate pause... │
│                                     │  (Live filtered feed) │
│                                     │  width: 420px        │
└─────────────────────────────────────┴───────────────────────┘
```

### Zone Breakdown

| # | Zone | Content | Data Source | Assignee |
|---|------|---------|-------------|----------|
| 1 | 2D World Map | RSS-driven Event Markers (Lat/Lon) + **Pulse Marker Auto-highlight** + **Marker Click → Country News Panel** | Tim's `event_location` + `focus_region` WS | Jun |
| 2 | Sentiment & History | Semicircle Gauge + Line Graph + Gemini reasoning | Central Hub final output | Andy |
| 3 | Live News | Sky News video (Fishjam Player + Smelter Overlay) | Fishjam WebRTC Stream | Tamas+Jun |
| 4 | Market Drivers | S&P, NASDAQ, VIX, Gold, Oil, 10Y Sparklines (2x3 grid) | Andy's 5-Layer Engine | Andy |
| 5 | AI Signal Feed | Fact-check cards + feed scroll | Tim + Tamas driver data | Andy |
| 6 | Headlines Ticker | Right-to-Left scrolling marquee (24hr RSS lines) | RSS feeds | Jun |
| — | Country News Panel | Right-side slide-in glassmorphism panel on country/marker click. Country indicators + live filtered news | `country_profiles.json` + WebSocket signal history | Andy(panel) + Jun(click handler) |

### 8-1. Auto-Pilot Broadcast Mode (Event-Driven Auto-Highlight)

**Concept**: When the Central Hub detects a major sentiment shift, it automatically highlights the relevant region's marker with a Pulse animation.

**Flow:**
1. **Trigger**: Tim's RSS pipeline detects major event (|sentiment_score| ≥ 60)
2. **Central Hub**: Emits `focus_region` WebSocket event (includes coordinates + signal)
3. **Frontend**: Creates a Pulse marker at target coordinates (CSS animation repeats 3x then converts to normal marker)
4. **User Interaction**: Click marker/country → Right-side CountryNewsPanel slides in

**Pulse Marker CSS:**
```css
.pulse-ring {
  animation: pulse 1.5s ease-out 3;
  border: 3px solid #FF4444; /* Bearish=red, Bullish=#00FF88 */
  border-radius: 50%;
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(3); opacity: 0; }
}
```

### 8-2. Country News Panel

**Behavior**: Clicking a marker or country region on the 2D Map slides in a glassmorphism panel from the right.

**Panel Structure:**
- Top: Country flag + name + key economic indicators (Stock Index, GDP, CPI) — sourced from `country_profiles.json`
- Bottom: Real-time filtered news signals for that country (filters WebSocket drivers by `event_location.country`)

**Panel Design:**
- Position: `position: fixed; right: 0; top: 0; height: 100vh; width: 420px`
- Background: `background: rgba(13, 17, 23, 0.85); backdrop-filter: blur(12px)` (glassmorphism)
- Dashboard backdrop: `background: rgba(0,0,0,0.4)` — click to close panel
- Animation: `framer-motion` — `initial={{ x: 420 }} animate={{ x: 0 }}` slide-in

**Data Sources** (No new API needed):
- Economic metrics: `data/country_profiles.json` (10 countries, pre-populated static data)
- News filtering: `useSentiment` hook accumulates signal history → `.filter()` by `country` field

### Design Guide
- Requires **Dark Mode** (Background #0D1117, Borders #30363D)
- Data Accents: Neon shades (Bullish=#00FF88, Bearish=#FF4444, Neutral=#FFAA00)
- Inspiration Reference: https://github.com/koala73/worldmonitor (Map style, layer toggles)
- Glassmorphism UI (backdrop-filter: blur)

---

## 9. Gemini API Invocation Structure

| Session | API | Assignee | Purpose |
|---------|-----|----------|---------|
| Session A | **Gemini Live API** | Tamas | Sky News Audio → Real-time STT + Sentiment (Using Fishjam Official Integration) |
| Session B | **Gemini Live API** | Jun | Unified Inference (Continuous Session, Maintains context, event-based injection) |
| Discrete Call| Gemini API (Classic) | Tim | Political RSS article → Fact Check → sentiment_score |

**Key takeaway**: Session A automates its pipeline directly with the Fishjam × Gemini Live API official integration.

---

## 10. RSS Feed Guide (Shared for Tamas & Tim)

### For Tamas: Finance/Economics RSS
```python
import feedparser

TAMAS_FINANCE_RSS_URL = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"

def fetch_economic_news():
    feed = feedparser.parse(TAMAS_FINANCE_RSS_URL)
    keywords = ["market", "fed", "interest rate", "inflation", "gdp", "earnings"]
    entries = []
    for entry in feed.entries:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        if any(keyword in text for keyword in keywords):
            entries.append({
                "title": entry.get("title"),
                "url": entry.get("link"),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", ""),
                "source": "google_news_rss",
            })
    return entries
```

### For Tim: Politics/Twitter RSS + Gemini Geo Extraction
```python
import feedparser

TIM_POLITICS_RSS_URL = "https://rss.app/rss-feed?keyword=Iran%20Israel&region=US&lang=en"

def fetch_political_news():
    feed = feedparser.parse(TIM_POLITICS_RSS_URL)
    return [
        {
            "title": entry.get("title"),
            "url": entry.get("link"),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
            "platform": "rss",
        }
        for entry in feed.entries
    ]

# Gemini Fact-check prompt incorporates Location Extraction.
# If the RSS summary is too thin, fetch the article URL first and pass
# title + summary + article text to Gemini for stronger geo extraction.
```

### RSS Characteristics
- Feed update cadence depends on the upstream publisher; a 2-5 minute polling loop is sufficient.
- No API key is required for the two fixed feed URLs above.
- Location intel is **not embedded in the feed itself**; Gemini must extract city + coordinates from title/summary/article body.
- Duplicate headlines are common; de-duplicate by link or title hash before posting to Central Hub.

---

## 11. Saturday Demo Strategy (Market Closed Mitigation)

> **⚠️ Hackathon Day = Saturday = Market Closed. yfinance will return Friday close data.**

### Strategy: Record 2-hour Friday dataset + Built-in Demo Triggers

**1. Friday Prep Work (Pre-Coding):**
- Record 2 hours of intraday Friday market data to `data/fallback/friday_session.json` using Andy's engine.
- Save 2 hours worth of Finance/Econ RSS and Politics RSS items.
- Ensure actual sentiment shift examples are captured for the history graph.

**2. Saturday Demo Architecture:**
- **Live Components (Operating legitimately):** Sky News Live Video/Audio Streams + RSS feed updates (News never closes).
- **Recorded Components (Replay Simulation):** Market data → Maps chronologically matched actual Friday data to graphs.
- **Simulated Triggers:** Built-in Demo Action Buttons.
  ```text
  [Inject: Fed Rate Cut]    → Immediately fires an +80 Bullish Signal
  [Inject: Trade War]       → Immediately fires a -70 Bearish Signal
  [Reset to Neutral]        → Rebase Default
  ```

**3. Talking Track:**
> "Since it's Saturday, the US markets are closed. The market data graphs you see emulate real intraday data captured yesterday, Friday. However, the news stream on the left is actively downloading live. By triggering these simulation buttons representing sudden market events, I will demonstrate how the dashboard dynamically responds and correlates in real time."

---

## 12. Execution Timeline (Hackathon Day — 6 Hours)

> **Rule:** ALL coding must begin on Hackathon Day. Pre-preparation was limited strictly to design/docs/keys.

### Hour 0-1: Environment Setup & Scaffolding (Everyone)
- [ ] Git clone + input actual `.env` keys
- [ ] `pip install -r requirements.txt` + `npm install` (frontend)
- [ ] `cd smelter && npm install` (Smelter Node.js server)
- [ ] FastAPI Server Skeleton (`main.py`, `config.py`, `models.py`)
- [ ] React + Vite Project Init + Establish Grid Layout
- [ ] Fishjam Cloud Connection Test

### Hour 1-3: Module Dev in Parallel (Divided)
**Tamas:**
- [ ] Auto URL detection for Bloomberg/Sky News live streams (`youtube_resolver.py`)
- [ ] Fishjam Agent SDK → Gemini Live bridge (`fishjam_audio_agent.py` — use Section 7-1 code reference)
- [ ] Finance/Econ RSS Collector (`rss_econ_collector.py`)
- [ ] Emit sentiment_score JSON → `POST /api/signal`

**Tim:**
- [ ] Politics/Twitter RSS Collector (`rss_political_collector.py`)
- [ ] Gemini Fact-check Module (`politician_checker.py`)
- [ ] `event_location` geo-extraction → pass map marker data
- [ ] Emit sentiment_score JSON → `POST /api/signal`

**Andy:**
- [ ] Integrate `backend/market_engine.py` into Central Hub directly (`from market_engine import MarketSentimentEngine`)
- [ ] Frontend layout setup with 6 Zones (CSS Grid)
- [ ] Sentiment Gauge + Time-series History Chart components
- [ ] Render 6 Market Drivers spark-line widgets
- [ ] CountryNewsPanel component (country click → right-side glassmorphism news panel)

**Jun:**
- [ ] Central Hub logic infrastructure (`signal_queue.py`, `scheduler.py`)
- [ ] Gemini Live API Session B (Unified inference engine)
- [ ] WebSocket Server setup (`sentiment_update` + `focus_region` event emit)
- [ ] 2D Map Integration (Leaflet + RSS markers + Pulse highlight)
- [ ] Autopilot trigger logic (threshold + cooldown)
- [ ] Marker click handler → CountryNewsPanel integration

### Hour 3-4: Hub Integration & Smelter
- [ ] Connect individual pipelines → Push/Test to Central Hub
- [ ] WebSocket → Validate real-time updates hitting Frontend state
- [ ] Smelter Node.js Server: `MarketOverlayScene.tsx` + `server.ts` WHIP output → Fishjam Livestream Room
- [ ] Frontend: Fishjam WHEP Player integration in Zone 3 (receive composited stream)
- [ ] Verify end-to-end: Smelter (compose) → WHIP → Fishjam → WHEP → Frontend Player
- [ ] Initialize Fallback mechanisms (Prep Friday data + Demo Trigger buttons)

### Hour 4-5: UI Polish & Demo Finalization
- [ ] Enforce global Dark Mode (Financial Terminal aesthetics)
- [ ] Fine-tune animation & transition fluidity
- [ ] Construct the lower-third Headlines Ticker
- [ ] Tidy up the UI/UX on the AI Signal Feed cards
- [ ] CountryNewsPanel UI polish (glassmorphism + slide-in animation)
- [ ] Pulse marker CSS animation fine-tuning
- [ ] Populate `country_profiles.json` with 10 countries' data

### Hour 5-6: Presentation Prep & Rehearsal
- [ ] Deck outline (Problem → Solution → Arch. → Demo → Tech Stack)
- [ ] Rehearse demo scenario below 3x
- [ ] Fallback failsafe planning (In case live APIs go down, deploy purely recorded fallback feed)

---

## 12-1. Live Demo Scenario (5-Minute Script)

> **Core Strategy**: First walk through the live dashboard explaining each zone,
> then use trigger buttons to inject extreme scenarios and showcase the **cascading reaction across all 6 zones**.

### Phase 1: Live Dashboard Tour (≈2 min)

> 🎤 **Narration**: *"What you're looking at is the Live Market Pulse dashboard. Let me walk you through the live components first."*

**[Point to Zone 3 — Live News]**
> 🎤 *"In the bottom-left, Sky News is streaming live via Fishjam WebRTC.
> The audio is being fed into the Gemini Live API right now for real-time STT and sentiment analysis.
> The sentiment overlay you see on the video is composited by Smelter directly onto the video frame — not CSS."*

**[Point to Zone 2 — Sentiment Gauge]**
> 🎤 *"The gauge in the center shows the overall market sentiment.
> It's a weighted average from 3 data sources — News (35%), Market Data (40%), Political News (25%) — 
> synthesized by Gemini's real-time inference engine. Currently sitting in the Neutral zone."*

**[Point to Zone 4 — Market Drivers]**
> 🎤 *"These sparklines show real intraday data from yesterday, Friday — 
> S&P 500, NASDAQ, VIX, Gold, Oil, and 10-Year yield.
> Since it's Saturday, markets are closed, but this is actual Friday trading data."*

**[Point to Zone 1 — Map]**
> 🎤 *"The 2D map displays global events collected from our RSS pipelines.
> Each marker is placed at city coordinates extracted by Gemini from news articles."*

**[Point to Zone 5 — AI Signal Feed]**
> 🎤 *"On the right, fact-checked political and news signals are listed chronologically.
> Each card shows Gemini's fact-check verdict and estimated market impact."*

---

### Phase 2: Extreme Scenario Injection — Trade War (≈1.5 min)

> 🎤 *"Now let me show you how the dashboard reacts when an extreme market event occurs."*

**[🔴 Click "Inject: Trade War" button]**

> 🎤 *"We're simulating President Trump announcing 50% tariffs on China."*

**Dashboard Cascade Reaction (What Judges Will See):**

```text
[1s]  Zone 5: 🔴 New signal card appears
      "Trump announces 50% tariffs on China" — Bearish -78, Fact-check: Real
       
[2s]  Zone 1: 🔴 Pulse markers spawn simultaneously at Washington DC + Beijing
      Red rings pulse 3 times to grab attention
       
[3s]  Zone 2: Gauge drops from Neutral → Bearish
      sentiment_score: +19 → -35
      Gauge color transitions green → red
      bullish_pct: 59.5% → 32.5%
       
[4s]  Zone 2 (below): Time-series graph shows sharp downward kink
      Gemini reasoning updates: "Tariff announcement severely dampens market sentiment"
       
[5s]  Zone 3: Smelter overlay changes to [BEARISH -35] in red
       
[6s]  Zone 6: Bottom ticker scrolls "BREAKING: Trump 50% tariffs on China"
```

> 🎤 *"As you can see, a single event cascades across all 6 zones simultaneously.
> The gauge turns red, new markers appear on the map, the time-series graph kinks downward,
> and even the overlay on the live news video updates in real time."*

**[Click Washington DC marker on Map]**

> 🎤 *"If I click this marker on the map..."*

```text
[Click]  Glassmorphism panel slides in from right
         🇺🇸 United States
         S&P 500: 5,421 | GDP: 2.1% | CPI: 3.4%
         ────────────────
         📰 Related News:
         • Trump announces 50% tariffs on China  [-78]
         • Fed hints at rate pause               [+72]
         (Only signals related to this country are filtered and displayed)
```

> 🎤 *"This is a country-level intelligence view — filtered news and economic indicators for the selected country."*

**[Click outside panel → panel closes]**

---

### Phase 3: Counter-Scenario — Recovery (≈1 min)

> 🎤 *"Let's see the opposite scenario. The Fed signals a potential rate cut."*

**[🟢 Click "Inject: Fed Rate Cut" button]**

**Dashboard Cascade Reaction:**

```text
[1s]  Zone 5: 🟢 New signal card appears
      "Fed signals potential rate cut" — Bullish +80
       
[2s]  Zone 2: Gauge climbs from Bearish → Bullish
      sentiment_score: -35 → +42
      Gauge color transitions red → green
      sentiment_change: "reversal" ← Gemini detects direction change
       
[3s]  Zone 2 (below): Time-series graph shows V-shaped recovery
      reasoning: "Fed rate cut signal partially offsets tariff shock"
       
[4s]  Zone 3: Smelter overlay changes to [BULLISH +42] in green
       
[5s]  Zone 6: Ticker scrolls "BREAKING: Fed signals rate cut"
```

> 🎤 *"The Fed's rate cut signal offsets the tariff shock, and the gauge recovers.
> Notice that Gemini detected a 'reversal' — a direction change — shown in the reasoning panel.
> This is the core of Live Market Pulse: not a single indicator, but AI-powered real-time synthesis across multiple sources."*

---

### Phase 4: Closing (≈30s)

> 🎤 *"In summary, this dashboard:
> 1. Ingests live news broadcasts via Fishjam,
> 2. Composites AI analysis directly onto video frames with Smelter,
> 3. Fuses RSS feeds, market data, and news through Gemini's real-time inference, and
> 4. Predicts financial market sentiment from -100 to +100.
> Thank you."*

### Demo Timing Summary

| Phase | Content | Duration | Key Impact |
|-------|---------|----------|-----------|
| 1 | Live Dashboard Tour | 2 min | Explain 6 zones, emphasize live elements |
| 2 | Trade War Injection | 1.5 min | **All zones react simultaneously**, Map click → News panel |
| 3 | Fed Rate Cut Injection | 1 min | **Counter-scenario recovery**, reversal detection |
| 4 | Closing | 30s | Summary of core tech stack |
| **Total** | | **5 min** | |

---

## 12. MVP Priority Hierarchy (Cutoff Lines)

```text
Must Have (Crucial for Demo)
  ✅ Central Hub + Gemini Live API Inference Engine
  ✅ Natively linked Andy's 5-Layer Market Engine
  ✅ Fontend Sentiment Gauge + History Charts
  ✅ Bloomberg/Sky News STT + Sentiment (Fishjam → Gemini Live)
  ✅ Fishjam Video ingestion & presentation
  ✅ Smelter native video overlays
  ✅ RSS Political Fact-checks
  ✅ Fallback dummy data + demo simulation triggers

Should Have (Time Permitting)
  🟡 RSS Economic updates (Secondary source for Tamas)
  🟡 2D Interactive Map and markers
  🟡 Complete 6-grid of Market Sparklines
  🟡 Headlines Ticker Marquee
  🟡 Auto-Pilot Pulse Markers (Auto-highlight new events)
  🟡 Country News Panel (Marker click → country-level filtered news panel)

Nice to Have (Bonus Additions)
  ⚪ Telethon (Telegram Scrape tool for pol. figures)
  ⚪ Voice Q&A module (Judges manually asking Gemini voice questions)
  ⚪ Push-alert notifications on sudden sentiment pivots
  ⚪ Geographic map-layer toggles (like worldmonitor)
```

---

## 13. Risks & Contingencies

| # | Risk | Contingency |
|---|------|-------------|
| 1 | Sky News Youtube Live goes offline | Switch to CNBC/Bloomberg or trigger recorded fallback |
| 2 | Gemini API gets rate-limited | Restrict API to 30s batches, implement cached responses |
| 3 | Fishjam connector fails completely | Revert to purely embedding a basic Youtube iframe |
| 4 | Smelter fails to render on frame | Fallback to basic CSS `position:absolute` overlays |
| 5 | RSS feeds contain duplicates or thin summaries | De-dup by link/title and fetch article body before Gemini fact-check when summary quality is poor. |
| 6 | Stock market closed on Sat. | Simulated via Demo Triggers on top of Friday EOD data. |
| 7 | Teammate module unfinished | Instantly substitute their input flow with sample generic JSONs. |
| 8 | Websockets sever | Add auto-reconnect loops that store last-known states. |

---

## 14. Core Gemini Prompts (Final Versions)

### 14-1. Unified Inference Prompt (Jun — Central Hub)

```text
You are a senior financial market analyst. Analyze the following 3 real-time data sources 
and determine the overall market sentiment.

[SOURCE WEIGHTS]
- Real-time Market Indicators (40%): Most objective baseline — prices don't lie
- News Stream Analysis (35%): Sky News broadcast + finance/econ RSS
- Political Intelligence (25%): Policy signals (filtered by fact-check results)

[ANALYSIS RULES]
1. PERSON WEIGHT: Statements from sitting President and Fed Chair carry 3x weight vs regular legislators
2. FACT FILTER: If fact_check == "Fake", completely ignore that statement
3. KEYWORD WEIGHT: News mentions of Fed, interest rate, inflation, GDP, employment → higher weight
4. DEDUP: If multiple sources point to the same event, don't double-count — raise confidence instead
5. TIME DECAY: Data < 5min old > 5-30min > 30min+
6. MARKET STATUS: If market_status == "closed", note this and weight recent news higher
7. If any source has no data, redistribute its weight proportionally to available sources

[INPUT DATA]
News Stream Analysis: {news_data}
Political Intelligence: {politician_data}
Market Indicators: {market_data}

[OUTPUT — respond ONLY with this JSON, no other text]
{{
  "sentiment_score": integer -100 to +100,
  "overall_sentiment": "Bullish" or "Neutral" or "Bearish",
  "confidence": integer 0-100,
  "previous_sentiment": "{prev_sentiment}",
  "sentiment_change": "continuation" or "reversal" or "initial",
  "drivers": [
    {{
      "source": "news_stream" or "politician" or "market_data",
      "sentiment_score": integer -100 to +100,
      "signal": "one-sentence summary of the key signal",
      "weight": float (0.25, 0.35, or 0.40)
    }}
  ],
  "reasoning": "2-3 sentence explanation of your overall judgment"
}}
```

### 14-2. Sky News Sentiment Analysis Prompt (Tamas)

```text
You are a financial media analyst. Analyze the following Sky News broadcast transcript 
and extract market sentiment signals.

[AUDIO TRANSCRIPT]
{transcript_text}

[RULES]
1. Focus on actionable market-moving information only
2. Ignore advertisements, transitions, and filler content
3. Extract up to 5 keywords that are most market-relevant
4. Rate confidence based on speaker certainty and information specificity

[OUTPUT — respond ONLY with this JSON, no other text]
{{
  "source": "news_stream",
  "sentiment_score": integer -100 to +100,
  "confidence": integer 0-100,
  "signal": "one-sentence summary of the key information",
  "keywords": ["keyword1", "keyword2", ...],
  "data_origin": "sky_news",
  "segment_duration_sec": {duration}
}}
```

### 14-3. Fact Check Prompt (Tim)

```text
You are a political fact-checker specializing in financial market impact. 
Verify the following political news and assess its potential market impact.

[NEWS ARTICLE]
Source: RSS feed
Title: "{title}"
Author/Subject: {author}
Tier: {tier}
Content: "{content}"

[RULES]
1. Check if the statement/event is factually accurate based on your knowledge
2. Assess whether this could realistically move markets
3. Identify which sectors would be most affected
4. For unverifiable future claims (e.g., "will impose tariffs"), mark as "Unverified" not "Fake"

[OUTPUT — respond ONLY with this JSON, no other text]
{{
  "source": "politician",
  "sentiment_score": integer -100 to +100 (if fact_check is Fake, must be 0),
  "confidence": integer 0-100,
  "signal": "one-sentence market impact summary",
  "author": "{author}",
  "platform": "rss",
  "tier": "{tier}",
  "fact_check": "Real" or "Fake" or "Unverified" or "Misleading",
  "fact_check_reasoning": "one-sentence explanation",
  "affected_sectors": ["sector1", "sector2"],
  "event_location": {{
    "city": "city name where the event is most relevant",
    "lat": float (latitude),
    "lon": float (longitude),
    "country": "2-letter country code"
  }}
}}
```

---

## 15. Directory Structure (Final)

```text
Hackathon/
├── backend/
│   ├── main.py                        # FastAPI server entry point + Routers
│   ├── config.py                      # SOURCE_WEIGHTS, FALLBACK_WEIGHTS, Constants
│   ├── models.py                      # Pydantic Schemas
│   ├── gemini_live_engine.py          # Gemini Live API Session B (Unified Inference)
│   ├── signal_queue.py                # Source-specific signal queue mgmt
│   ├── scheduler.py                   # 30-sec batch scheduler
│   ├── youtube_resolver.py            # Sky News Live URL automatic resolver
│   ├── fishjam_audio_agent.py         # Tamas: Fishjam Agent SDK → Gemini Live bridge
│   ├── rss_econ_collector.py          # Tamas: Finance/Econ RSS Collector
│   ├── rss_political_collector.py     # Tim: Politics/Twitter RSS Collector
│   ├── politician_checker.py          # Tim: Gemini Fact-check module
│   ├── fallback_manager.py            # Auto-routing fallback datasets
│   ├── websocket_server.py            # socket.io Server Engine
│   ├── requirements.txt
│   └── .env                           # API Keys (gitignore)
│
│   ├── market_engine.py               # Andy: 5-Layer Market Engine (Imported to Central Hub)
│
├── smelter/                             # Smelter Node.js Video Compositing Server
│   ├── package.json
│   ├── tsconfig.json
│   ├── server.ts                      # Smelter entry point + WHIP output config
│   └── scenes/
│       └── MarketOverlayScene.tsx     # React overlay scene (sentiment badge + ticker)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main App + 6-Zone Grid Setup
│   │   ├── theme.ts                   # Financial Terminal Dark Mode specs
│   │   ├── components/
│   │   │   ├── SentimentGauge.tsx      # Semicircle UI (Bullish/Neutral/Bearish)
│   │   │   ├── SentimentHistory.tsx    # Recharts Time Series lines
│   │   │   ├── DriverFeed.tsx         # AI Signal Feed (Fact-check cards)
│   │   │   ├── MarketDrivers.tsx      # S&P/NASDAQ/VIX blocks (2x3 grid)
│   │   │   ├── LiveNewsPlayer.tsx     # Fishjam Player + Smelter Overlays
│   │   │   ├── WorldMap.tsx           # Leaflet 2D Maps + RSS-derived geo-markers + Pulse highlight
│   │   │   ├── CountryNewsPanel.tsx   # Country click → right-side glassmorphism news panel
│   │   │   ├── HeadlinesTicker.tsx    # Lower Marquee scroller
│   │   │   ├── DemoControls.tsx       # Sim trigger buttons panel
│   │   │   └── StatusBar.tsx          # Connection Status + Latest update log
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        # Setup socket.io hooks
│   │   │   └── useSentiment.ts        # Manage unified sentiment state + signal history accumulation
│   │   └── types/
│   │       └── index.ts               # Core TS Definitions
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── data/
│   ├── country_profiles.json          # 10 countries key economic indicators (static)
│   └── fallback/
│       ├── sample_news.json           # 10x Sky News samples
│       ├── sample_politicians.json    # 10x Pol News samples
│       └── sample_timeline.json       # 5-min demo scenario loop logic
│
├── .env.example
├── .gitignore
├── EXECUTION_PLAN.md                  # This logic template
└── README.md
```

---

## 16. References & Docs

| Reference | Location | Purpose |
|-----------|----------|---------|
| Fishjam Official Docs | https://docs.fishjam.io | WebRTC stream ingestion & player |
| Fishjam × Gemini Live Integration | https://docs.fishjam.io/tutorials/gemini-live-integration | Core mapping for Session A pipeline |
| Smelter Official Docs | https://smelter.dev | Video Compositing Overlay tech |
| Smelter GitHub Repo | https://github.com/software-mansion/smelter | Source codebase & install guides |
| Gemini Live API Reference | https://ai.google.dev/docs/gemini-api/live | Core Live session management API |
| Google News RSS (Finance & Economics) | https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen | Tamas finance/econ RSS source |
| rss.app Feed (Iran Israel) | https://rss.app/rss-feed?keyword=Iran%20Israel&region=US&lang=en | Tim politics/Twitter RSS source |
| feedparser Docs | https://feedparser.readthedocs.io/en/latest/ | Python RSS parsing reference |
| worldmonitor examples | https://github.com/koala73/worldmonitor | Layer toggling aesthetics refs |
| FastAPI Docs | https://fastapi.tiangolo.com | Core generic backend tech frame |
| yfinance Source | https://github.com/ranaroussi/yfinance | Market retrieval logic for Engine |
