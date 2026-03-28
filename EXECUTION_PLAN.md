# Live Market Pulse — 실행계획서 (v4 확정 · 해커톤 당일)

> **변경 이력**:
> v1 → v2: Fishjam/Smelter 승격, 사전 MVP 전체 기능 포함, 세션 설명 추가
> v2 → v3: 통일 sentiment_score(-100~+100), 역할 재배정, Neutral 추가, 시장데이터 공식
> v3 → v4 (2026-03-28): 해커톤 당일 확정판 (최종)
>   - 사전 MVP 섹션 삭제 (당일 직접 구현)
>   - 뉴스 소스: Bloomberg(우선) + Sky News(24시간 fallback) 이중 전략
>   - Tamas: Bloomberg/Sky News + GDELT(경제) / Tim: GDELT(정치)만
>   - Andy: market_engine.py 5-Layer 엔진 채택 → `backend/market_engine.py`
>   - 아키텍처: 내장(Method B, GitHub 공유)
>   - 대시보드 6영역 레이아웃 + 2D Map 이벤트 마커
>   - 토요일 데모 전략: 금요일 2시간 데이터 녹화 + 데모 트리거 버튼
>   - Gemini로 뉴스 기사에서 도시 수준 위치 추출 (GKG 불필요)

---

## 프로젝트 개요

실시간 멀티모달 대시보드. 금융 뉴스 방송(Bloomberg/Sky News) + 정치 뉴스(GDELT) + 시장 데이터를 융합해 금융 시장 심리(Bullish/Neutral/Bearish, -100~+100)를 예측.

**핵심 차별점**: Fishjam으로 뉴스 방송 오디오를 Gemini Live API에 실시간 전달하고, Smelter가 영상 위에 Sentiment 오버레이를 합성하는 것이 데모의 핵심 비주얼.

**뉴스 소스 전략**: Bloomberg(금융 전문, 장중 우선) → Sky News(24시간 무중단, fallback)
**토요일 데모**: 금요일 장중 2시간 데이터 사전 녹화 + 데모 트리거 버튼으로 실시간 시뮬레이션

---

## 1. 팀 구성 & 역할

| 이름 | 역할 | 담당 | 보내는 것 |
|------|------|------|----------|
| **Jun** | Team Lead / Architecture | Central Hub, Gemini 추론 엔진, 2D Map(이벤트 마커), 파이프라인 통합 | 최종 sentiment_score (종합) |
| **Tamas** | News Stream | Bloomberg/Sky News(Fishjam→Gemini STT+감성) + **GDELT(경제 필터)** → sentiment_score | `sentiment_score: -100~+100` |
| **Tim** | Political Intelligence | **GDELT(정치 필터)** → Gemini 팩트체크+위치추출 → sentiment_score | `sentiment_score: -100~+100` |
| **Andy** | Market Data + Frontend | `backend/market_engine.py`(5-Layer) + 프론트엔드 전체 구축 | `sentiment_score: -100~+100` |

### 역할 분담 근거
- **Tamas**: Bloomberg/Sky News(경제 뉴스 방송) + GDELT 경제 필터 = 같은 카테고리 → 합산 후 하나의 `sentiment_score`
- **Tim**: GDELT 정치 필터 = 정치인 발언/정책 뉴스만 집중 → Gemini 팩트체크+도시 위치 추출 후 `sentiment_score`
- **Andy**: 1235줄 5-Layer 엔진 → `backend/market_engine.py`로 이동. Central Hub에서 `from market_engine import MarketSentimentEngine`

---

## 2. 핵심 개념 설명

### "세션(Session)"이란?

| 구분 | 비유 | 작동 방식 |
|------|------|-----------|
| **일반 Gemini API** | 📮 편지 | 요청 1건 → 응답 1건 → 끝. 이전 대화 기억 못 함. |
| **Gemini Live API 세션** | 📞 전화 통화 | 세션 열림 → 계속 말함 → 계속 대답 → 끊기 전까지 유지. 이전에 한 말 기억. |

**왜 세션 2개?**
- **세션 A (Tamas)**: Sky News 오디오를 계속 흘려보내면서 실시간 STT + 감성분석
- **세션 B (Jun)**: 모든 데이터를 계속 주입하면서 종합 판단

---

## 3. 시스템 아키텍처 (해커톤 당일)

> **아키텍처 방식: Method B (내장)**
> 모든 모듈을 하나의 서버에서 import해서 실행. GitHub으로 코드 공유 → 각자 push → Jun이 pull해서 통합 실행.

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
├──────────────────┬──────────────────┬────────────────────────┤
│ Sky News Live    │ GDELT (정치 필터) │ Market Data            │
│ (Tamas)          │ (Tim)            │ (Andy — 5-Layer 엔진)   │
│ + GDELT (경제)    │                  │                        │
└────────┬─────────┴────────┬─────────┴────────┬───────────────┘
         │                  │                  │
         ▼                  ▼                  │
┌──────────────────┐ ┌──────────────┐          │
│ Fishjam          │ │ GDELT API    │          │
│ (WebRTC Ingest)  │ │ (정치 테마)   │          │
│ 오디오 수집       │ └──────┬───────┘          │
└───┬──────────┬───┘        │                  │
    │          │             │                  │
    │     오디오 추출        │                  │
    │          │             │                  │
    │          ▼             ▼                  │
    │  ┌───────────────┐ ┌──────────────┐      │
    │  │ Gemini Live   │ │ Gemini API   │      │
    │  │ API 세션 A    │ │ (팩트체크)    │      │
    │  │ (STT+감성분석)│ │              │      │
    │  └───────┬───────┘ └──────┬───────┘      │
    │          │                │               │
    │          ▼                ▼               ▼
    │  ┌──────────────────────────────────────────────────┐
    │  │           CENTRAL HUB (Python FastAPI)            │
    │  │                                                    │
    │  │  Source Weights: market(0.40) news(0.35) pol(0.25) │
    │  │  Andy 엔진은 import로 내장 (별도 서버 X)            │
    │  │                      │                             │
    │  │          ┌───────────┴───────────┐                 │
    │  │          │  Gemini Live API      │                 │
    │  │          │  세션 B (종합 추론)     │                 │
    │  │          │  컨텍스트 유지          │                 │
    │  │          └───────────┬───────────┘                 │
    │  │                      ▼                             │
    │  │           JSON 결과 출력                            │
    │  └──────────────┬───────────────────────────────────┘
    │                 │ WebSocket (socket.io)
    │                 ▼
    │  ┌──────────────────────────────────────────────────┐
    │  │            FRONTEND (React + Vite)                 │
    │  │                                                    │
    │  │  ┌──────────────────┐  ┌─────────────────────┐   │
    │  │  │ Sky News 영상    │  │ Sentiment 게이지     │   │
    │  │  │ Fishjam Player  │  │ + 시계열 그래프       │   │
    │  │  ├──────────────────┤  ├─────────────────────┤   │
    │  │  │ Smelter Overlay  │  │ Market Charts       │   │
    │  │  │ Sentiment 오버레이│  │ S&P, NASDAQ, VIX    │   │
    │  │  ├──────────────────┤  ├─────────────────────┤   │
    │  │  │ AI Signal Feed   │  │ 2D Map (GDELT 이벤트)│   │
    │  │  │ (Driver 리스트)   │  │ 지정학 리스크 마커    │   │
    │  │  └──────────────────┘  └─────────────────────┘   │
    │  └──────────────────────────────────────────────────┘
    │          ▲
    └──────────┘ (Fishjam WebRTC 영상 직접 전달)
```

---

## 4. 기술 스택

### Backend (Python)
| 기술 | 용도 | 비고 |
|------|------|------|
| **Python 3.11+** | 메인 언어 | 확정 |
| **FastAPI** | Central Hub API 서버 | 비동기 지원 |
| **uvicorn** | ASGI 서버 | FastAPI 실행 |
| **python-socketio** | WebSocket 서버 | socket.io 프로토콜 |
| **market_sentiment_engine.py** | Andy의 5-Layer 시장 분석 엔진 | import로 내장 |
| **yfinance** | 시장 데이터 수집 (엔진 내부) | 60+ 티커 |
| **fredapi** | FRED 매크로 경제 데이터 (엔진 내부) | 17개 시리즈 |
| **google-genai** | Gemini Live API | 세션 A(STT), 세션 B(추론) |
| **google-generativeai** | Gemini 일반 API | Tim 팩트체크용 |
| **yt-dlp** | YouTube 오디오 추출 | Sky News 스트림용 |
| **apscheduler** | 30초 배치 스케줄러 | 데이터 수렴 타이밍 |
| **gdeltdoc** | GDELT 뉴스 수집 | Tamas(경제) + Tim(정치) |
| **python-dotenv** | 환경변수 관리 | API 키 보안 |

### Frontend (React)
| 기술 | 용도 | 비고 |
|------|------|------|
| **React 18 + Vite** | 프론트엔드 프레임워크 | TypeScript |
| **socket.io-client** | 백엔드 WebSocket 수신 | 실시간 업데이트 |
| **Recharts** | Sentiment 히스토리 차트 | React 네이티브 차트 |
| **Leaflet / react-leaflet** | 2D 세계 지도 | GDELT 이벤트 마커 표시 |
| **@fishjam-cloud/react-client** | Fishjam WebRTC 스트림 재생 | Sky News 영상 표시 |
| **@swmansion/smelter** | 비디오 컴포지팅 오버레이 | ✅ 오픈소스 (self-hosted) |
| **framer-motion** | UI 애니메이션 | 게이지/트랜지션 |

### 외부 API & 서비스
| API | 키 필요 | 비용 | 용도 |
|-----|---------|------|------|
| Gemini Live API | O | 해커톤 제공 | 실시간 STT + 종합 추론 세션 |
| Gemini API (일반) | O | 무료 | Tim 팩트체크 |
| YouTube Data API v3 | O | 무료 (쿼터) | Sky News 라이브 URL 자동 탐지 |
| yfinance | X | 무료 | 60+ 시장 티커 (Andy 엔진 내부) |
| FRED API | O | 무료 | 매크로 경제 지표 (Andy 엔진 내부) |
| GDELT 2.0 API | X | 무료 | 경제 뉴스(Tamas) + 정치 뉴스(Tim) |
| Fishjam Cloud | O | 무료 티어 | WebRTC 스트림 수집/재생 |
| Smelter | X | 완전 무료 | 비디오 컴포지팅 오버레이, self-hosted |

---

## 5. 데이터 인터페이스 스키마 (팀원 간 JSON 약속)

> 모든 팀원은 **통일된 `sentiment_score` (-100 ~ +100)** 를 계산해서 Central Hub에 POST.
> 엔드포인트: `POST /api/signal`
>
> **스코어 규칙**: `+100` = 극도 Bullish, `0` = Neutral, `-100` = 극도 Bearish

### 5-1. Tamas → Central Hub (Sky News + GDELT 경제)
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
**필드 설명:**
- `source`: 항상 `"news_stream"` (Bloomberg/Sky News + GDELT 경제 통합)
- `data_origin`: `"bloomberg"` | `"sky_news"` | `"gdelt_econ"` (어디서 왔는지 구분)
- `sentiment_score`: **-100 ~ +100** (Gemini가 직접 산출)

### 5-2. Tim → Central Hub (GDELT 정치)
```json
{
  "source": "politician",
  "sentiment_score": -78,
  "confidence": 94,
  "signal": "Trump announces 50% tariffs on China starting Monday",
  "author": "Donald Trump",
  "platform": "gdelt",
  "tier": "president",
  "fact_check": "Real",
  "fact_check_reasoning": "Official White House schedule confirms meeting with trade advisors",
  "affected_sectors": ["trade", "manufacturing"],
  "event_location": {"lat": 38.9, "lon": -77.0, "city": "Washington DC", "country": "US"},
  "timestamp": "2026-03-28T14:33:00Z"
}
```
**필드 설명:**
- `sentiment_score`: **-100 ~ +100** (Gemini가 팩트체크+영향도 반영. Fake면 0)
- `event_location`: 지도 마커용 좌표 (**Gemini가 기사 내용에서 도시 추출 → 좌표 매핑**)
- `tier`: "president" | "fed_chair" | "cabinet" | "senator" | "representative" | "other"

### 5-3. Andy → Central Hub (Market Data — 5-Layer 엔진)
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
**필드 설명:**
- `sentiment_score`: **-100 ~ +100** (Andy 5-Layer 엔진 `compute_composite_score()` 결과)
- 기존 §6-2 단순 공식 대체 → 5개 레이어(Price/Breadth/Options/Macro/Survey) 종합

### 5-4. Central Hub → Frontend (최종 출력)
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
  "reasoning": "Fed의 금리 동결 시사가 Bullish이나, 트럼프 관세 발표가 상쇄. 시장 지표는 소폭 긍정적.",
  "data_freshness": {
    "news_last": "2026-03-28T14:32:00Z",
    "politician_last": "2026-03-28T14:31:00Z",
    "market_last": "2026-03-28T14:30:00Z"
  },
  "timestamp": "2026-03-28T14:32:30Z"
}
```
**프론트엔드 게이지 매핑:**
- `sentiment_score` → 게이지 위치 (-100 ~ +100)
- `bullish_pct` = `(sentiment_score + 100) / 2` → 퍼센트 표시
- 판정 구간: `+21~+100` = 🟢 Bullish, `-20~+20` = 🟡 Neutral, `-100~-21` = 🔴 Bearish

---

## 6. 가중치 & 스코어 설계

### 6-1. 소스 간 가중치 (하드코딩 — `config.py`)
```python
SOURCE_WEIGHTS = {
    "market_data": 0.40,    # 가장 객관적 — 가격은 거짓말 안 함
    "news_stream": 0.35,    # Sky News + GDELT 경제 뉴스
    "politician": 0.25      # 정책 시그널 (팩트체크 필터링 후)
}

# 데이터 누락 시 fallback 가중치 재분배
FALLBACK_WEIGHTS = {
    "no_news": {"market_data": 0.55, "politician": 0.45},
    "no_politician": {"market_data": 0.55, "news_stream": 0.45},
    "only_market": {"market_data": 1.0}
}

# Sentiment 판정 구간
SENTIMENT_THRESHOLDS = {
    "bullish": 21,    # +21 이상 = Bullish
    "bearish": -21,   # -21 이하 = Bearish
    # -20 ~ +20 = Neutral
}
```

### 6-2. Market Data 스코어 (Andy의 5-Layer 엔진)
> ⚠️ v3의 단순 `calculate_market_sentiment()` 공식은 **삭제**.
> Andy의 `market_sentiment_engine.py` (1235줄)의 `compute_composite_score()`가 대체.
>
> 5개 레이어: Price Signals → Market Breadth → Options Market → Macro/FRED → Sentiment Surveys
> 내부적으로 0-100 → -100~+100으로 선형 매핑 (`(score - 50) * 2`)
>
> Central Hub에서 `from market_sentiment_engine import MarketSentimentEngine`으로 내장 호출.

### 6-3. 소스 내부 가중치 (Gemini 프롬프트로 위임)
프롬프트에 다음 지침 포함:
- **인물 가중치**: 현직 대통령, Fed 의장 발언은 일반 의원보다 가중치 3배
- **팩트 필터**: `fact_check` == "Fake" → `sentiment_score`를 0으로
- **키워드 가중치**: Sky News에서 Fed/금리/인플레이션/GDP/고용 키워드 → 높은 점수
- **중복 방지**: 여러 소스가 동일 이벤트를 가리키면 중복 반영 X → confidence 상향
- **시간 가중치**: 최근 5분 이내 데이터 > 5-30분 데이터 > 30분 이상 데이터

---

## 7. Fishjam / Smelter 역할 확정

### 7-1. Fishjam (오디오→AI 파이프라인)
```
Bloomberg / Sky News YouTube Live
     │
     ▼
  youtube_resolver.py (Bloomberg 우선, Sky News fallback)
     │
     ▼
  Fishjam (WebRTC로 오디오 스트림 수집)
     │
     ├──→ 오디오 트랙 → Gemini Live API 세션 A (실시간 STT + 감성분석)
     │
     └──→ 영상 트랙 → Smelter (오버레이 합성) → 프론트엔드 재생
```

**뉴스 소스 우선순위:**
```python
def get_live_url():
    bloomberg = try_bloomberg()  # Bloomberg TV 라이브 탐지
    if bloomberg:
        return bloomberg, "bloomberg"
    return SKY_NEWS_URL, "sky_news"  # 24시간 무중단 fallback

SKY_NEWS_URL = "https://www.youtube.com/watch?v=YDvsBbKfLPA"
```

**핵심 포인트:** Fishjam ↔ Gemini Live API 공식 연동 가이드 활용
→ "SWM 기술을 핵심적으로 활용했다"고 심사위원에게 어필 가능

### 7-2. Smelter (비디오 오버레이 합성)
대시보드 하단 좌측 "Live News" 위젯에서 사용:
- Bloomberg/Sky News 영상 프레임 위에 **Gemini가 분석한 결과를 직접 합성**
- CSS 오버레이가 아닌 **실제 비디오 컴포지팅** (프레임 자체에 베이킹)
- 합성 내용: [BULLISH +72] 게이지, 키워드 하이라이트, 팩트체크 상태
- Smelter React 컴포넌트 활용 (`@swmansion/smelter`)

---

## 8. 대시보드 레이아웃 확정

### 와이어프레임 (6영역 구조)

```
┌─────────────────────────────────────────────────────────────┐
│                  LIVE MARKET PULSE             🔴 LIVE  UTC │ ← Header
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│  [영역 1] 2D World Map       │  [영역 2] Sentiment Score    │
│  (GDELT 이벤트 마커)          │  + Confidence Level         │
│                              │  + 시계열 그래프 (Time-series)│
│  • 관세/제재 → 🔴 High Alert │  + AI Analysis (Reasoning)  │
│  • 정치 긴장 → 🟠 Elevated   │                              │
│  • 경제 발표 → 🟢 Monitoring │  • 반원 게이지 (중앙 대형)    │
│  • 레이어 토글 (worldmonitor) │  • 변곡점 Hover → AI 설명    │
│          ~50%                │          ~50%                │
│                              │                              │
├───────────────┬──────────────┴──────────────┬───────────────┤
│               │                             │               │
│  [영역 3]      │  [영역 4] Market Drivers     │  [영역 5]      │
│  Live News    │  (핵심 지표 차트)              │  Political    │
│  Sky News     │                             │  News / AI    │
│  (Fishjam +   │  • S&P 500 스파크라인         │  Signal Feed  │
│   Smelter     │  • NASDAQ 스파크라인          │               │
│   오버레이)    │  • VIX 게이지                │  • 팩트체크 카드│
│               │  • Gold / Oil               │  • 시간순 스크롤│
│     ~25%      │  • 10Y Yield                │     ~25%      │
│               │         ~50%                │               │
├───────────────┴─────────────────────────────┴───────────────┤
│  [영역 6] 📰 Headlines Ticker: 최근 24시간 뉴스 전광판 스크롤   │
└─────────────────────────────────────────────────────────────┘
```

### 각 영역 상세

| # | 영역 | 콘텐츠 | 데이터 소스 | 담당 |
|---|------|--------|-----------|------|
| 1 | 2D World Map | GDELT 이벤트 마커 (위도/경도) + 레이어 토글 | Tim의 `event_location` + Tamas GDELT | Jun |
| 2 | Sentiment + 시계열 | 반원 게이지 + 꺾은선 그래프 + Gemini reasoning | Central Hub 최종 출력 | Andy |
| 3 | Live News | Sky News 영상 (Fishjam Player + Smelter 오버레이) | Fishjam WebRTC 스트림 | Tamas+Jun |
| 4 | Market Drivers | S&P, NASDAQ, VIX, Gold, Oil, 10Y 스파크라인 차트 (2x3 격자) | Andy 5-Layer 엔진 | Andy |
| 5 | AI Signal Feed | 팩트체크 카드 + 뉴스 시그널 (시간순 스크롤) | Tim + Tamas driver 데이터 | Andy |
| 6 | Headlines Ticker | 전광판 형태 좌→우 스크롤 (최근 24시간 GDELT 헤드라인) | GDELT | Jun |

### 디자인 가이드
- **Dark Mode** 필수 (배경 #0D1117, 테두리 #30363D)
- 데이터 포인트: 네온 컬러 (Bullish=#00FF88, Bearish=#FF4444, Neutral=#FFAA00)
- 참고: https://github.com/koala73/worldmonitor (레이어 토글, 지도 스타일)
- 글래스모피즘 카드 (backdrop-filter: blur)

---

## 9. Gemini API 호출 구조

| 세션 | API | 담당 | 용도 |
|------|-----|------|------|
| 세션 A | **Gemini Live API** | Tamas | Sky News 오디오 → 실시간 STT + 감성분석 (Fishjam 공식 연동) |
| 세션 B | **Gemini Live API** | Jun | 종합 추론 (연속 세션, 컨텍스트 유지, 이벤트 기반 주입) |
| 단건 호출 | Gemini API (일반) | Tim | 정치 뉴스 팩트체크 (GDELT 기사 → 팩트체크 → sentiment_score) |

**핵심**: 세션 A는 Fishjam × Gemini Live API 공식 연동으로 자동 파이프라인 구축.

---

## 10. GDELT 활용 가이드 (Tamas & Tim 공유)

### Tamas용: 경제/비즈니스 필터
```python
from gdeltdoc import GdeltDoc, Filters

def fetch_economic_news():
    gd = GdeltDoc()
    f = Filters(
        keyword=["market", "Fed", "interest rate", "inflation", "GDP", "earnings"],
        start_date="2026-03-28",
        end_date="2026-03-28",
        country=["US"],
        theme=["ECON_", "MARKET_", "TRADE_"]
    )
    return gd.article_search(f)  # → pandas DataFrame (title, url, domain, language, seendate)
```

### Tim용: 정치 필터 + Gemini 위치 추출
```python
def fetch_political_news():
    gd = GdeltDoc()
    f = Filters(
        keyword=["tariff", "sanctions", "executive order", "trade war", "regulation"],
        start_date="2026-03-28",
        end_date="2026-03-28",
        country=["US"],
        theme=["TAX_POLICY", "SANCTION", "ELECTION", "GOV_"]
    )
    articles = gd.article_search(f)
    return articles

# Gemini 팩트체크 프롬프트에 위치 추출도 포함 (GKG 불필요!)
# → Gemini가 기사 내용을 분석하여 관련 도시명과 lat/lon 좌표를 직접 반환
# → 별도 CITY_COORDS 딕셔너리 불필요 — Gemini가 전 세계 도시 좌표를 알고 있음
```

### GDELT 특성
- 15분마다 업데이트 → 30초마다 체크해도 새 데이터는 15분 단위
- API 키 불필요, rate limit 없음
- 위치 데이터: **Gemini가 기사에서 관련 도시 + 좌표를 직접 추출** (GKG/CITY_COORDS 불필요)
- Telethon(Telegram)은 **Nice to Have** — GDELT만으로 충분

---

## 11. 토요일 데모 전략 (시장 휴장 대응)

> **⚠️ 해커톤 당일 = 토요일 = 시장 휴장. yfinance는 금요일 마감 데이터만 반환.**

### 전략: 금요일 2시간 데이터 녹화 + 데모 트리거 버튼

**1. 금요일 사전 준비 (코딩 전):**
- Andy 엔진으로 금요일 장중 2시간 데이터를 `data/fallback/friday_session.json`에 저장
- GDELT 정치/경제 뉴스도 2시간분 저장
- 시계열 그래프에 넣을 실제 sentiment 변동 데이터 확보

**2. 토요일 데모 구성:**
- **라이브 요소 (실제 동작):** Sky News 영상 스트리밍 + GDELT 뉴스 수집 (뉴스는 24/7)
- **녹화 요소 (리플레이):** 금요일 시장 데이터 → 시계열 그래프에 실제 데이터로 표시
- **시뮬레이션 요소:** 데모 트리거 버튼
  ```
  [Inject: Fed Rate Cut]    → 즉시 Bullish +80 시그널
  [Inject: Trade War]       → 즉시 Bearish -70 시그널
  [Reset to Neutral]        → 초기화
  ```

**3. 발표 멘트:**
> "현재 토요일이라 미국 시장은 휴장입니다. 화면의 시장 데이터는 어제 금요일 실제 장중 데이터이며,
> 뉴스 스트림은 지금 라이브로 분석 중입니다. 버튼으로 시장 이벤트를 시뮬레이션하여
> 대시보드가 실시간으로 반응하는 모습을 보여드리겠습니다."

---

## 12. 실행 타임라인 (해커톤 당일 — 6시간)

> **규칙**: 모든 코딩은 해커톤 당일에 진행. 사전 준비는 설계/문서/키 발급까지만.

### Hour 0-1: 환경 세팅 & 골격 (전원)
- [ ] Git clone + `.env` 실제 키 입력
- [ ] `pip install -r requirements.txt` + `npm install`
- [ ] FastAPI 서버 골격 (`main.py`, `config.py`, `models.py`)
- [ ] React + Vite 프로젝트 초기화 + 레이아웃 Grid 잡기
- [ ] Fishjam Cloud 연결 테스트

### Hour 1-3: 각자 모듈 병렬 구현
**Tamas:**
- [ ] Sky News 라이브 URL 자동 탐지 (`youtube_resolver.py`)
- [ ] Fishjam → Gemini Live API 오디오 파이프라인
- [ ] GDELT 경제 뉴스 수집 (`gdelt_econ_collector.py`)
- [ ] sentiment_score JSON → `POST /api/signal`

**Tim:**
- [ ] GDELT 정치 뉴스 수집 (`gdelt_political_collector.py`)
- [ ] Gemini 팩트체크 모듈 (`politician_checker.py`)
- [ ] event_location 추출 → 지도 마커 데이터
- [ ] sentiment_score JSON → `POST /api/signal`

**Andy:**
- [ ] `backend/market_engine.py` Central Hub 내장 연동 (`from market_engine import MarketSentimentEngine`)
- [ ] 프론트엔드 6영역 레이아웃 (CSS Grid)
- [ ] Sentiment 게이지 + 시계열 차트 컴포넌트
- [ ] Market Drivers 스파크라인 6개

**Jun:**
- [ ] Central Hub 핵심 로직 (`signal_queue.py`, `scheduler.py`)
- [ ] Gemini Live API 세션 B (종합 추론)
- [ ] WebSocket 서버 (`sentiment_update` emit)
- [ ] 2D Map 컴포넌트 (Leaflet + GDELT 이벤트 마커)

### Hour 3-4: 통합 & Smelter
- [ ] 각 파이프라인 → Central Hub 연결 테스트
- [ ] WebSocket → 프론트엔드 실시간 렌더링 확인
- [ ] Smelter 오버레이 (Bloomberg/Sky News 영상에 sentiment 합성)
- [ ] Fallback 데이터 준비 (금요일 녹화 데이터 + 데모 트리거 버튼)

### Hour 4-5: UI 폴리싱 & 데모 준비
- [ ] 다크 모드 테마 적용 (금융 터미널 스타일)
- [ ] 애니메이션/트랜지션 미세 조정
- [ ] Headlines Ticker (하단 전광판)
- [ ] AI Signal Feed 카드 디자인

### Hour 5-6: 발표 준비 & 리허설
- [ ] 발표 자료 (문제 → 솔루션 → 아키텍처 → 데모 → 기술 스택)
- [ ] 데모 시나리오 (토요일 대응):
  1. 초기 상태: 금요일 마감 데이터 + 라이브 뉴스 스트리밍 (Sky News는 주말에도 라이브)
  2. [Inject: Fed Rate Cut] → 즉시 Bullish → 게이지/차트 반응 시연
  3. [Inject: Trade War] → 즉시 Bearish → GDELT 이벤트 마커 동시 표시
  4. Smelter 오버레이로 뉴스 영상 위 AI 분석 결과 합성 시연
  5. 시계열 그래프에서 금요일 실제 데이터 변동 보여주기
- [ ] 데모 리허설 3회
- [ ] Fallback 시나리오 대비 (라이브 실패 시 전체 녹화 데이터로 전환)

---

## 12. MVP 우선순위 (시간 부족 시 컷라인)

```
Must Have (없으면 데모 불가)
  ✅ Central Hub + Gemini Live API 종합 추론
  ✅ Andy 5-Layer 시장 엔진 연동
  ✅ 프론트엔드 Sentiment 게이지 + 시계열 차트
  ✅ Bloomberg/Sky News STT + 감성분석 (Fishjam → Gemini Live)
  ✅ Fishjam 스트림 수집 + 영상 재생
  ✅ Smelter 비디오 오버레이
  ✅ GDELT 정치 뉴스 팩트체크
  ✅ Fallback 데이터 + 데모 트리거

Should Have (시간 되면)
  🟡 GDELT 경제 뉴스 (Tamas 보조 소스)
  🟡 2D Map 이벤트 마커
  🟡 Market Drivers 스파크라인 6개
  🟡 Headlines Ticker (하단 전광판)

Nice to Have (시간 남으면)
  ⚪ Telethon (Telegram 정치인 채널 모니터링)
  ⚪ 음성 Q&A (심사위원 ↔ Gemini)
  ⚪ 알림 시스템 (급격한 sentiment 변화)
  ⚪ 레이어 토글 (worldmonitor 스타일)
```

---

## 13. 리스크 & 대응

| # | 리스크 | 대응 |
|---|--------|------|
| 1 | Sky News 유튜브 라이브 끊김 | CNBC/Bloomberg 자동 전환 + fallback 데이터 |
| 2 | Gemini API rate limit | 30초 배치로 최소화 + 응답 캐싱 |
| 3 | Fishjam 연동 실패 | YouTube iframe 직접 embed fallback |
| 4 | Smelter 렌더링 실패 | CSS position:absolute 오버레이 fallback |
| 5 | GDELT 15분 지연 | 허용 가능 — 정치 뉴스는 15분 지연도 충분 |
| 6 | 시장 휴장 | 마지막 거래일 데이터 + 시뮬레이션 모드 |
| 7 | 팀원 모듈 미완성 | fallback 샘플 데이터 즉시 대체 |
| 8 | WebSocket 끊김 | 자동 재연결 + 마지막 상태 유지 |

---

## 14. Gemini 프롬프트 (확정판)

### 14-1. 종합 추론 프롬프트 (Jun — Central Hub)

```
You are a senior financial market analyst. Analyze the following 3 real-time data sources 
and determine the overall market sentiment.

[SOURCE WEIGHTS]
- Real-time Market Indicators (40%): Most objective baseline — prices don't lie
- News Stream Analysis (35%): Sky News broadcast + GDELT economic news
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

### 14-2. Sky News 감성분석 프롬프트 (Tamas)

```
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

### 14-3. 팩트체크 프롬프트 (Tim)

```
You are a political fact-checker specializing in financial market impact. 
Verify the following political news and assess its potential market impact.

[NEWS ARTICLE]
Source: GDELT
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
  "platform": "gdelt",
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

## 15. 디렉토리 구조 (확정)

```
Hackathon/
├── backend/
│   ├── main.py                        # FastAPI 서버 진입점 + 라우터
│   ├── config.py                      # SOURCE_WEIGHTS, FALLBACK_WEIGHTS, 상수
│   ├── models.py                      # Pydantic 스키마
│   ├── gemini_live_engine.py          # Gemini Live API 세션 B (종합 추론)
│   ├── signal_queue.py                # 소스별 시그널 큐 관리
│   ├── scheduler.py                   # 30초 배치 스케줄러
│   ├── youtube_resolver.py            # Sky News 라이브 URL 자동 탐지
│   ├── gdelt_econ_collector.py        # Tamas: GDELT 경제 뉴스 수집
│   ├── gdelt_political_collector.py   # Tim: GDELT 정치 뉴스 수집
│   ├── politician_checker.py          # Tim: Gemini 팩트체크 모듈
│   ├── fallback_manager.py            # Fallback 데이터 자동 전환
│   ├── websocket_server.py            # socket.io 서버
│   ├── requirements.txt
│   └── .env                           # API 키 (gitignore)
│
│   ├── market_engine.py               # Andy: 5-Layer 시장 분석 엔진 (Central Hub에서 import)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # 메인 앱 + 6영역 Grid 레이아웃
│   │   ├── theme.ts                   # 다크 모드 금융 터미널 테마
│   │   ├── components/
│   │   │   ├── SentimentGauge.tsx      # 반원 게이지 (Bullish/Neutral/Bearish)
│   │   │   ├── SentimentHistory.tsx    # Recharts 시계열 차트
│   │   │   ├── DriverFeed.tsx         # AI Signal Feed (팩트체크 카드)
│   │   │   ├── MarketDrivers.tsx      # S&P/NASDAQ/VIX 스파크라인 (2x3 격자)
│   │   │   ├── LiveNewsPlayer.tsx     # Fishjam Player + Smelter 오버레이
│   │   │   ├── WorldMap.tsx           # Leaflet 2D 지도 + GDELT 이벤트 마커
│   │   │   ├── HeadlinesTicker.tsx    # 하단 전광판 스크롤
│   │   │   ├── DemoControls.tsx       # 데모 트리거 버튼 패널
│   │   │   └── StatusBar.tsx          # 연결 상태 + 마지막 업데이트
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        # socket.io 연결 관리
│   │   │   └── useSentiment.ts        # sentiment 상태 관리
│   │   └── types/
│   │       └── index.ts               # TypeScript 타입 정의
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── data/
│   └── fallback/
│       ├── sample_news.json           # Sky News 샘플 10건
│       ├── sample_politicians.json    # 정치 뉴스 샘플 10건
│       └── sample_timeline.json       # 5분 시뮬레이션 시나리오
│
├── .env.example
├── .gitignore
├── EXECUTION_PLAN.md                  # 이 파일
└── README.md
```

---

## 16. 참조 문서

| 문서 | URL | 용도 |
|------|-----|------|
| Fishjam 공식 문서 | https://docs.fishjam.io | WebRTC 스트림 수집/재생 |
| Fishjam × Gemini Live 연동 | https://docs.fishjam.io/tutorials/gemini-live-integration | 세션 A 파이프라인 핵심 |
| Smelter 공식 문서 | https://smelter.dev | 비디오 컴포지팅 오버레이 |
| Smelter GitHub | https://github.com/software-mansion/smelter | 소스 코드 + 설치 |
| Gemini Live API 문서 | https://ai.google.dev/docs/gemini-api/live | Live API 세션 관리 |
| GDELT Project | https://www.gdeltproject.org | 글로벌 뉴스/정치 이벤트 DB |
| gdeltdoc (Python) | https://github.com/alex9smith/gdelt-doc-api | GDELT Python 클라이언트 |
| worldmonitor (참고) | https://github.com/koala73/worldmonitor | 2D Map 레이어 토글 참고 |
| FastAPI 문서 | https://fastapi.tiangolo.com | Python 백엔드 |
| yfinance 문서 | https://github.com/ranaroussi/yfinance | 시장 데이터 (Andy 엔진) |
