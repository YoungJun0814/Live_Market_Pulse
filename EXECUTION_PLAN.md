# Live Market Pulse — 실행계획서 (v3 확정)

> **변경 이력**:
> v1 → v2 (2026-03-26): Fishjam/Smelter 승격, 사전 MVP 전체 기능 포함, 세션 설명 추가
> v2 → v3 (2026-03-26): 통일 sentiment_score(-100~+100), 역할 재배정, Neutral 추가, 시장데이터 공식, Telethon+GDELT

---

## 프로젝트 개요

실시간 멀티모달 대시보드. Bloomberg 방송 + 정치인 SNS + 시장 데이터를 융합해 금융 시장 심리(Bullish/Neutral/Bearish, -100~+100)를 예측.

**핵심 차별점**: Fishjam으로 Bloomberg 스트림을 수집하고, Smelter가 그 위에 Sentiment 오버레이를 실시간 렌더링하는 것이 데모의 핵심 비주얼.

---

## 1. 팀 구성 & 역할

| 이름 | 역할 | 담당 | 보내는 것 |
|------|------|------|----------|
| **Jun** | Team Lead / Architecture | 백엔드 Central Hub, Gemini 추론 엔진, 선박/항공 대시보드 통합, 파이프라인 통합 | 최종 sentiment_score (종합) |
| **Tamas** | Bloomberg Stream | Fishjam 스트림 수집 → Gemini STT + 감성분석 → **sentiment_score 계산** | `sentiment_score: -100~+100` |
| **Tim** | Politicians SNS | Telethon/GDELT 수집 → Gemini 팩트체크 → **sentiment_score 계산** | `sentiment_score: -100~+100` |
| **Andy** | Market Data + Frontend | yfinance 시장 데이터 수집 → **sentiment_score 공식 계산** + 프론트엔드 전체 구축 | `sentiment_score: -100~+100` |

---

## 2. 핵심 개념 설명

### "세션(Session)"이란?

| 구분 | 비유 | 작동 방식 |
|------|------|-----------|
| **일반 Gemini API** | 📮 편지 | 요청 1건 보냄 → 응답 1건 받음 → 끝. 다음 질문은 새 편지. 이전 대화 기억 못 함. |
| **Gemini Live API 세션** | 📞 전화 통화 | 전화 걸음(세션 열림) → 계속 말함 → 상대가 계속 대답함 → 끊기 전까지 대화 유지. 이전에 한 말 기억. |

**왜 세션 2개?**
- **세션 A (Tamas 담당)**: Bloomberg 오디오를 계속 흘려보내면서 실시간 STT + 감성분석 받는 "전화"
- **세션 B (Jun 담당)**: 모든 데이터를 계속 주입하면서 종합 판단 받는 "전화"

### 사전 MVP vs 해커톤 당일 API 전략

| | 사전 MVP (해커톤 전) | 해커톤 당일 |
|---|---|---|
| **API** | 무료 Gemini API (google-generativeai) | Gemini Live API (해커톤 제공 키) |
| **방식** | 30초 배치 → 편지 방식 요청 | 실시간 스트리밍 → 전화 방식 |
| **목적** | 전체 로직 검증 + 프로덕션급 완성 | API만 교체 (프롬프트/스키마 동일) |
| **비용** | 무료 (Google AI Studio 키) | 무료 (해커톤 제공) |

핵심 프롬프트와 JSON 스키마가 동일하므로 전환 비용 최소.

---

## 3. 최종 시스템 아키텍처

### 3-1. 사전 MVP 아키텍처 (무료 Gemini API 기반)

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
├──────────────────┬──────────────────┬────────────────────────┤
│ Bloomberg Live   │ Politicians SNS  │ Market Data APIs       │
│ (Tamas)          │ (Tim)            │ (Jun)                  │
└────────┬─────────┴────────┬─────────┴────────┬───────────────┘
         │                  │                  │
         ▼                  ▼                  │
┌──────────────────┐ ┌──────────────┐          │
│ Fishjam          │ │ Telegram Bot │          │
│ (WebRTC Ingest)  │ │ / SNS API    │          │
│ 영상+오디오 수집  │ └──────┬───────┘          │
└───┬──────────┬───┘        │                  │
    │          │             │                  │
    │     오디오 추출        │                  │
    │          │             │                  │
    │          ▼             ▼                  │
    │  ┌───────────────┐ ┌──────────────┐      │
    │  │ Gemini API    │ │ Gemini API   │      │
    │  │ (STT+감성분석)│ │ (팩트체크)    │      │
    │  │ ≪일반 API≫   │ │ ≪일반 API≫   │      │
    │  └───────┬───────┘ └──────┬───────┘      │
    │          │                │               │
    │          ▼                ▼               ▼
    │  ┌──────────────────────────────────────────────────┐
    │  │           CENTRAL HUB (Python FastAPI)            │
    │  │                                                    │
    │  │  Source Weights: market(0.40) bloom(0.35) pol(0.25)│
    │  │                      │                             │
    │  │          ┌───────────┴───────────┐                 │
    │  │          │  30초 배치 스케줄러    │                 │
    │  │          │  (데이터 수렴 → 추론)  │                 │
    │  │          └───────────┬───────────┘                 │
    │  │                      ▼                             │
    │  │           Gemini Reasoning Engine                  │
    │  │           (종합 추론 + JSON 출력)                    │
    │  │           ≪일반 API≫                               │
    │  └──────────────┬───────────────────────────────────┘
    │                 │ WebSocket (socket.io)
    │                 ▼
    │  ┌──────────────────────────────────────────────────┐
    │  │            FRONTEND (React + Vite)                 │
    │  │                                                    │
    │  │  ┌──────────────────┐  ┌─────────────────────┐   │
    │  │  │ Bloomberg 영상   │  │ Sentiment 게이지     │   │
    │  │  │ Fishjam Player  │  │ Bullish/Bearish %    │   │
    │  │  ├──────────────────┤  ├─────────────────────┤   │
    │  │  │ Smelter Overlay  │  │ Sentiment 히스토리   │   │
    │  │  │ Sentiment 오버레이│  │ 차트 (시간축)        │   │
    │  │  ├──────────────────┤  ├─────────────────────┤   │
    │  │  │ Driver Feed      │  │ Market Data 바      │   │
    │  │  │ (근거 리스트)     │  │ S&P, VIX, Oil      │   │
    │  │  ├──────────────────┤  ├─────────────────────┤   │
    │  │  │                  │  │ 3D Globe (globe.gl) │   │
    │  │  │                  │  │ 선박/항공 시각화     │   │
    │  │  └──────────────────┘  └─────────────────────┘   │
    │  └──────────────────────────────────────────────────┘
    │          ▲
    └──────────┘ (Fishjam WebRTC 영상 직접 전달)
```

### 3-2. 해커톤 당일 아키텍처 변경점

```
변경 1: Fishjam → Gemini Live API 공식 연동 활용
  사전: Bloomberg → Fishjam → 오디오 추출 → 일반 Gemini API
  당일: Bloomberg → Fishjam → Gemini Live API (공식 파이프라인, 자동 연결)
  참조: https://docs.fishjam.io/tutorials/gemini-live-integration

변경 2: 종합 추론 → Gemini Live API 세션
  사전: 30초 배치 → 일반 Gemini API (편지 방식)
  당일: 이벤트 기반 → Gemini Live API 세션 (전화 방식, 컨텍스트 유지)

변경 3: 팩트체크는 그대로
  Tim의 정치인 팩트체크 = 일반 Gemini API 유지 (스트리밍 불필요)
```

---

## 4. 기술 스택

### Backend (Python)
| 기술 | 용도 | 비고 |
|------|------|------|
| **Python 3.11+** | 메인 언어 | 확정 |
| **FastAPI** | Central Hub API 서버 | 비동기 지원 |
| **uvicorn** | ASGI 서버 | FastAPI 실행 |
| **python-socketio** | WebSocket 서버 (프론트엔드 push) | socket.io 프로토콜 |
| **yfinance** | 시장 데이터 수집 | API 키 불필요, 15분 지연 |
| **google-generativeai** | Gemini API 클라이언트 | 사전 MVP: 무료 티어 |
| **google-genai (Live)** | Gemini Live API 클라이언트 | 당일 전환용 |
| **yt-dlp** | YouTube 오디오 추출 | Bloomberg 스트림용 |
| **apscheduler** | 30초 배치 스케줄러 | 데이터 수렴 타이밍 |
| **pydantic** | 데이터 검증/스키마 | JSON 인터페이스 보장 |
| **python-dotenv** | 환경변수 관리 | API 키 보안 |
| **Telethon** | Telegram 공개 채널 모니터링 | userbot 방식 (Bot API로는 공개 채널 읽기 불가) |
| **gdeltPyR** | GDELT 글로벌 뉴스/정치 이벤트 수집 | 15분 업데이트, API 키 불필요 |

### Frontend (React)
| 기술 | 용도 | 비고 |
|------|------|------|
| **React 18 + Vite** | 프론트엔드 프레임워크 | TypeScript |
| **socket.io-client** | 백엔드 WebSocket 수신 | 실시간 업데이트 |
| **Recharts** | Sentiment 히스토리 차트 | React 네이티브 차트 |
| **globe.gl** | 3D Globe 시각화 | 선박/항공 표시 |
| **@fishjam-cloud/react-client** | Fishjam WebRTC 스트림 재생 | Bloomberg 영상 표시 |
| **@swmansion/smelter** | 비디오 컴포지팅 오버레이 | ✅ 완전 오픈소스 (self-hosted) |
| **framer-motion** | UI 애니메이션 | 게이지/트랜지션 |

### 외부 API & 서비스
| API | 키 필요 | 비용 | 용도 | 사전/당일 | 비고 |
|-----|---------|------|------|-----------|------|
| Gemini API (gemini-2.0-flash) | O | 무료 티어 | STT, 감성분석, 팩트체크, 종합 추론 | 사전 MVP | Google AI Studio |
| Gemini Live API | O | 해커톤 제공 | 실시간 Bloomberg STT + 종합 추론 세션 | 당일 전환 | |
| YouTube Data API v3 | O | 무료 (쿼터) | Bloomberg 라이브 스트림 URL 자동 탐지 | 사전+당일 | `search` endpoint + `eventType=live` |
| yfinance | X | 무료 | S&P500, VIX, Oil, DXY | 사전+당일 | |
| Telethon (Telegram) | O | 무료 | 정치인 공개 채널 실시간 모니터링 | 사전+당일 | api_id + api_hash 필요 (my.telegram.org) |
| GDELT 2.0 API | X | 무료 | 글로벌 뉴스/정치 이벤트 수집 | 사전+당일 | 15분마다 업데이트, API 키 불필요 |
| ADS-B Exchange | O | 무료 티어 | 항공 위치 데이터 (시각화) | 사전+당일 | |
| Fishjam Cloud | O | **무료 티어 있음** | WebRTC 스트림 수집/재생 | **사전+당일 모두 사용** | 관리형 서비스 (원본 OSS는 아카이브됨) |
| Smelter | X | **완전 무료** | 비디오 컴포지팅 오버레이 | **사전+당일 모두 사용** | ✅ 오픈소스 self-hosted |

---

## 5. 데이터 인터페이스 스키마 (팀원 간 JSON 약속)

> 모든 팀원은 **통일된 `sentiment_score` (-100 ~ +100)** 를 계산해서 Central Hub에 POST.
> 엔드포인트: `POST /api/signal`
>
> **스코어 규칙**: `+100` = 극도 Bullish, `0` = Neutral, `-100` = 극도 Bearish

### 5-1. Tamas → Central Hub (Bloomberg 분석)
```json
{
  "source": "bloomberg",
  "sentiment_score": 72,
  "confidence": 85,
  "signal": "Fed hints at rate pause in June meeting",
  "keywords": ["Fed", "rate", "pause"],
  "segment_duration_sec": 30,
  "timestamp": "2026-03-25T14:32:00Z"
}
```
**필드 설명:**
- `sentiment_score`: **-100 ~ +100** (Gemini가 직접 산출 — 프롬프트에 지시)
- `confidence`: 0-100 (이 판단에 대한 확신도)
- `signal`: 핵심 정보 1문장 요약
- `keywords`: 핵심 키워드 배열 (최대 5개)

### 5-2. Tim → Central Hub (정치인 SNS)
```json
{
  "source": "politician",
  "sentiment_score": -78,
  "confidence": 94,
  "signal": "Trump announces 50% tariffs on China starting Monday",
  "author": "Donald Trump",
  "platform": "truth_social",
  "tier": "president",
  "fact_check": "Real",
  "fact_check_reasoning": "Official White House schedule confirms meeting with trade advisors",
  "affected_sectors": ["trade", "manufacturing"],
  "timestamp": "2026-03-25T14:33:00Z"
}
```
**필드 설명:**
- `sentiment_score`: **-100 ~ +100** (Gemini가 팩트체크+영향도 반영해서 산출. Fake면 0)
- `tier`: "president" | "fed_chair" | "cabinet" | "senator" | "representative" | "other"
- `fact_check`: "Real" | "Fake" | "Unverified" | "Misleading"

### 5-3. Andy → Central Hub (Market Data)
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
  "timestamp": "2026-03-25T14:30:00Z"
}
```
**필드 설명:**
- `sentiment_score`: **-100 ~ +100** (공식 기반 자동 계산 — 아래 §6-2 참조)
- `market_status`: "open" | "closed" | "pre_market" | "after_hours"

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
      "source": "bloomberg",
      "sentiment_score": 72,
      "signal": "Fed hints at rate pause — Powell tone notably dovish",
      "weight": 0.35,
      "timestamp": "2026-03-25T14:32:00Z"
    },
    {
      "source": "politician",
      "sentiment_score": -78,
      "signal": "Trump announces 50% tariffs on China",
      "weight": 0.25,
      "fact_check": "Real (94%)",
      "timestamp": "2026-03-25T14:31:00Z"
    },
    {
      "source": "market_data",
      "sentiment_score": 10,
      "signal": "VIX drops 3.1%, S&P500 up 0.8%",
      "weight": 0.40,
      "timestamp": "2026-03-25T14:30:00Z"
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
    "bloomberg_last": "2026-03-25T14:32:00Z",
    "politician_last": "2026-03-25T14:31:00Z",
    "market_last": "2026-03-25T14:30:00Z"
  },
  "timestamp": "2026-03-25T14:32:30Z"
}
```
**프론트엔드 게이지 매핑:**
- `sentiment_score` → 게이지 위치 (-100 ~ +100)
- `bullish_pct` = `(sentiment_score + 100) / 2` → 퍼센트 표시
- 판정 구간: `+21~+100` = 🟢 Bullish, `-20~+20` = 🟡 Neutral, `-100~-21` = 🔴 Bearish
```

---

## 6. 가중치 & 스코어 설계

### 6-1. 소스 간 가중치 (하드코딩 — `config.py`)
```python
SOURCE_WEIGHTS = {
    "market_data": 0.40,   # 가장 객관적 — 가격은 거짓말 안 함
    "bloomberg": 0.35,     # 전문가 분석 + 속보
    "politician": 0.25     # 정책 시그널 (팩트체크 필터링 후)
}

# 데이터 누락 시 fallback 가중치 재분배
FALLBACK_WEIGHTS = {
    "no_bloomberg": {"market_data": 0.55, "politician": 0.45},
    "no_politician": {"market_data": 0.55, "bloomberg": 0.45},
    "only_market": {"market_data": 1.0}
}

# Sentiment 판정 구간
SENTIMENT_THRESHOLDS = {
    "bullish": 21,    # +21 이상 = Bullish
    "bearish": -21,   # -21 이하 = Bearish
    # -20 ~ +20 = Neutral
}
```

### 6-2. Market Data 스코어 자동 계산 (Andy 담당)
```python
def calculate_market_sentiment(indicators: dict) -> int:
    """시장 지표를 종합해 -100 ~ +100 점수 산출 (Gemini 불필요)"""
    signals = {
        "sp500": indicators["sp500"]["change_pct"] * 15,     # S&P 상승 = Bullish
        "vix":  -indicators["vix"]["change_pct"] * 10,       # VIX 하락 = Bullish
        "oil":  -abs(indicators["oil"]["change_pct"]) * 3,   # 급변 = 불안
        "dxy":  -indicators["dxy"]["change_pct"] * 5,        # 달러 약세 = Bullish
        "gold": -indicators["gold"]["change_pct"] * 5,       # 금 상승 = 불안
        "us10y":-indicators["us10y"]["change_bps"] * 0.8,    # 금리 하락 = Bullish
    }
    weights = {"sp500": 0.30, "vix": 0.25, "oil": 0.15, "dxy": 0.10, "gold": 0.10, "us10y": 0.10}
    raw = sum(signals[k] * weights[k] for k in signals)
    return max(-100, min(100, int(raw)))
```

### 6-3. 소스 내부 가중치 (Gemini 프롬프트로 위임)
프롬프트에 다음 지침 포함:
- **인물 가중치**: 현직 대통령, Fed 의장 발언은 일반 의원보다 가중치 3배
- **팩트 필터**: `fact_check` == "Fake" → `sentiment_score`를 0으로
- **키워드 가중치**: Bloomberg에서 Fed/금리/인플레이션/GDP/고용 키워드 → 높은 점수
- **중복 방지**: 여러 소스가 동일 이벤트를 가리키면 중복 반영 X → confidence 상향
- **시간 가중치**: 최근 5분 이내 데이터 > 5-30분 데이터 > 30분 이상 데이터

---

## 7. Gemini API 호출 구조

### 사전 MVP (무료 일반 Gemini API)

| 호출 | API | 담당 | 용도 | 호출 빈도 |
|------|-----|------|------|-----------|
| 호출 1 | Gemini API (gemini-2.0-flash) | Tamas | Bloomberg 오디오 → 텍스트 요약 + 감성분석 | 30초마다 |
| 호출 2 | Gemini API (gemini-2.0-flash) | Tim | 정치인 발언 팩트체크 | 새 발언 감지 시 |
| 호출 3 | Gemini API (gemini-2.0-flash) | Jun | 종합 추론 (3개 소스 수렴 → 최종 판단) | 30초마다 |

### 해커톤 당일 (Gemini Live API 전환)

| 세션 | API | 담당 | 용도 | 변경점 |
|------|-----|------|------|--------|
| 세션 A | **Gemini Live API** | Tamas | Bloomberg 오디오 → 실시간 STT + 감성분석 | 배치→스트리밍 |
| 세션 B | **Gemini Live API** | Jun | 종합 추론 (연속 세션, 컨텍스트 유지) | 배치→이벤트 기반 |
| 단건 호출 | Gemini API (일반) | Tim | 정치인 팩트체크 (변경 없음) | 유지 |

**핵심**: 세션 A는 Fishjam x Gemini Live API 공식 연동으로 자동 파이프라인 구축 가능.

---

## 8. 데이터 동기화 방식

### 사전 MVP: 30초 배치 (Polling)
```python
# 의사코드 — 30초 배치 스케줄러
async def batch_cycle():
    """매 30초마다 실행"""
    # 1. 최근 30초간 수집된 Bloomberg 분석 결과를 큐에서 꺼냄
    bloomberg_signals = signal_queue.drain("bloomberg")
    
    # 2. 최근 30초간 새 정치인 발언 꺼냄 (없으면 빈 리스트)
    politician_signals = signal_queue.drain("politician")
    
    # 3. 현재 시장 데이터 스냅샷 (yfinance)
    market_data = await fetch_market_data()
    
    # 4. 3개를 묶어서 Gemini Reasoning에 전달
    result = await gemini_engine.reason(
        bloomberg=bloomberg_signals,
        politicians=politician_signals,
        market=market_data
    )
    
    # 5. 결과 JSON을 WebSocket으로 프론트에 push
    await sio.emit("sentiment_update", result.dict())
    
    # 6. 히스토리 저장 (인메모리 deque, 최대 120개 = 1시간)
    history.append(result)
```

### 해커톤 당일: 이벤트 기반 실시간
```
Gemini Live API 세션 B에 데이터를 연속 주입:
  - Bloomberg 감성 변화 감지 → 즉시 세션에 주입
  - 정치인 새 발언 → 즉시 세션에 주입
  - 시장 데이터 → 30초마다 주입 (이건 동일)
  → Gemini가 컨텍스트를 유지하며 실시간 판단 업데이트
  → 30초 기다릴 필요 없이 즉각 반응
```

---

## 9. 실행 타임라인

### ⚡ Phase 1: 사전 MVP 완성 (해커톤 전) — 완성도 목표 90%

> 사전 MVP에서 **모든 기능**을 구현. 해커톤 당일에는 API 교체 + 폴리싱만.

#### Step 1 — 환경 세팅 & API 키 확보 (Day 1)
- [ ] Python 3.11+ 프로젝트 초기화
  - `backend/` 디렉토리 생성
  - `requirements.txt` 작성
  - 가상환경 생성 (`python -m venv .venv`)
- [ ] React + Vite + TypeScript 프로젝트 초기화
  - `npx create-vite frontend --template react-ts`
- [ ] API 키 확보
  - Gemini API 키: Google AI Studio (https://aistudio.google.com) → 무료
  - YouTube Data API v3 키: Google Cloud Console
  - Telegram API: my.telegram.org → api_id + api_hash 발급 (Telethon용)
  - GDELT: 키 불필요 (공개 API)
- [ ] `.env` 파일 구조 확정
  ```
  GEMINI_API_KEY=your_key_here
  YOUTUBE_API_KEY=your_key_here
  TELEGRAM_API_ID=your_api_id
  TELEGRAM_API_HASH=your_api_hash
  TELEGRAM_PHONE=your_phone_number
  FISHJAM_API_KEY=your_fishjam_key
  ```
- [ ] Fishjam Cloud 계정 생성 (https://fishjam.io) → 무료 티어 API 키 확보
- [ ] Git repo 생성 + 팀원 초대 + `.gitignore` 설정
- [ ] yfinance 동작 확인 (`pip install yfinance && python -c "import yfinance"`)

#### Step 2 — 백엔드 Central Hub 구축 (Jun, Day 1-2)
- [ ] FastAPI 서버 골격 생성 (`main.py`)
  - `POST /api/signal` — 팀원 데이터 수신 (Pydantic 모델 검증)
  - `GET /api/health` — 헬스체크
  - `GET /api/history` — Sentiment 히스토리 조회
- [ ] `config.py` — 가중치, fallback 가중치, 상수 정의
- [ ] `models.py` — Pydantic 모델 (§5의 JSON 스키마 그대로)
  - `BloombergSignal`, `PoliticianSignal`, `MarketData`, `SentimentResult`
- [ ] WebSocket 서버 (`python-socketio`)
  - `sentiment_update` 이벤트 emit
  - `history_request` 이벤트 핸들링
- [ ] `market_data.py` — yfinance 시장 데이터 수집 모듈
  - S&P500 (^GSPC), VIX (^VIX), Oil (CL=F), DXY (DX-Y.NYB)
  - Gold (GC=F), US 10Y (^TNX)
  - 30초 폴링 루프 (apscheduler)
  - 시장 휴장 감지 → `market_status: "closed"` + 마지막 거래일 데이터
- [ ] `signal_queue.py` — 소스별 시그널 큐 관리
  - 인메모리 큐 (deque) → 30초마다 drain
  - 소스별 분리: bloomberg_queue, politician_queue
- [ ] `gemini_engine.py` — Gemini 종합 추론 모듈
  - 프롬프트 템플릿 (§11 프롬프트 사용)
  - JSON 출력 파싱 + 검증
  - fallback 가중치 자동 적용 (데이터 누락 시)
  - 에러 핸들링 (API 타임아웃, rate limit)
- [ ] `scheduler.py` — 30초 배치 스케줄러
  - 데이터 수렴 → 추론 → WebSocket push 사이클
  - 히스토리 저장 (인메모리 deque, 최대 120개)

#### Step 3 — Bloomberg 파이프라인 (Tamas, Day 2-3)
- [ ] `youtube_resolver.py` — Bloomberg 라이브 스트림 URL 자동 탐지
  ```python
  # YouTube Data API v3 search endpoint로 현재 라이브 스트림 자동 탐지
  # URL이 매번 바뀌어도 항상 현재 라이브 찾음
  import requests
  
  BLOOMBERG_CHANNEL_ID = "UCIALMKvObZNtJ68-rmLjXhA"  # Bloomberg TV
  
  def get_live_stream_url(api_key: str) -> str | None:
      """Bloomberg 채널에서 현재 라이브 중인 영상 URL을 자동 탐지"""
      url = "https://www.googleapis.com/youtube/v3/search"
      params = {
          "part": "snippet",
          "channelId": BLOOMBERG_CHANNEL_ID,
          "eventType": "live",       # 핵심: 현재 라이브만 필터
          "type": "video",
          "maxResults": 1,
          "key": api_key
      }
      resp = requests.get(url, params=params).json()
      if resp.get("items"):
          video_id = resp["items"][0]["id"]["videoId"]
          return f"https://www.youtube.com/watch?v={video_id}"
      return None  # 라이브 없음 → fallback 트리거
  ```
  - 5분마다 URL 갱신 (라이브 스트림이 바뀔 수 있으므로)
  - 라이브 없을 시: 최근 VOD 검색 (`eventType=completed`) 또는 fallback 데이터
- [ ] 오디오 추출 로직
  - `yt-dlp`로 오디오 스트림 추출 → 30초 chunk 분할
  - `yt-dlp -f bestaudio --no-playlist -o - {url} | ffmpeg ...`
- [ ] Gemini API로 오디오/텍스트 분석 (사전 MVP: **일반 API**)
  - 30초 오디오 chunk → Gemini에 전송
  - STT + 감성분석을 한 번에 요청
  - JSON 출력 (§5-1 스키마)
- [ ] `bloomberg_processor.py` — 파이프라인 오케스트레이션
  - URL 탐지 → 오디오 추출 → 분석 → Central Hub POST 루프
  - URL 변경 감지 → 자동 재연결
- [ ] 결과를 Central Hub `POST /api/signal` 로 자동 전송

#### Step 4 — 정치인 SNS 파이프라인 (Tim, Day 2-3)

> **⚠️ 중요**: Telegram **Bot API**로는 공개 채널 메시지를 읽을 수 없음.
> **Telethon** (userbot 라이브러리)을 사용해야 공개 채널 모니터링 가능.
> 추가로 **GDELT**를 병행 수집하여 뉴스 기반 정치 이벤트도 잡아냄.

**소스 A: Telethon으로 Telegram 공개 채널 실시간 모니터링**
- [ ] Telegram API 키 발급 (my.telegram.org → api_id, api_hash)
- [ ] `telegram_monitor.py` — Telethon 기반 채널 모니터링
  ```python
  from telethon import TelegramClient, events
  
  # 모니터링 대상 채널 (username 또는 채널 ID)
  MONITORED_CHANNELS = [
      "@realDonaldTrump",      # Truth Social → Telegram 미러 or 공식
      "@WhiteHouse",
      "@FedReserve",
      "@CNBCnow",
      "@BBCBreaking",
      # ... 정치/경제 주요 채널
  ]
  
  client = TelegramClient('session', api_id, api_hash)
  
  @client.on(events.NewMessage(chats=MONITORED_CHANNELS))
  async def handler(event):
      """새 메시지 감지 → 팩트체크 → Central Hub 전송"""
      text = event.message.text
      channel = event.chat.username
      # → Gemini 팩트체크 → POST /api/signal
  ```
  - 첫 실행 시 전화번호 인증 필요 (1회)
  - 이후 세션 파일로 자동 로그인
  - ⚠️ Rate limit 주의: 과도한 요청 시 일시 차단 가능

**소스 B: GDELT로 글로벌 뉴스/정치 이벤트 보조 수집**
- [ ] `gdelt_collector.py` — GDELT 2.0 뉴스 이벤트 수집
  ```python
  from gdeltdoc import GdeltDoc, Filters
  
  def fetch_political_events():
      """최근 정치/경제 관련 글로벌 뉴스 수집"""
      gd = GdeltDoc()
      f = Filters(
          keyword=["tariff", "Fed", "interest rate", "sanctions", "trade war"],
          start_date="2026-03-26",
          end_date="2026-03-26",
          country=["US"],
          theme=["ECON_", "GOV_"]
      )
      articles = gd.article_search(f)  # → pandas DataFrame
      return articles
  ```
  - 15분마다 업데이트 (배치 폴링으로 30초마다 체크)
  - API 키 불필요, 완전 무료
  - Telegram에서 못 잡는 뉴스/성명서/기자회견 보완

**팩트체크 & 영향도 분석**
- [ ] Gemini API로 팩트체크 모듈 (`politician_checker.py`)
  - 입력: 정치인 발언 텍스트 + author + tier + source(telegram/gdelt)
  - 출력: fact_check 결과 + reasoning + estimated_impact
  - JSON 출력 (§5-2 스키마)
- [ ] 정치인 tier 매핑 테이블
  ```python
  POLITICIAN_TIERS = {
      "Donald Trump": "president",
      "Jerome Powell": "fed_chair",
      "Janet Yellen": "cabinet",
      "Chuck Schumer": "senator",
      "Nancy Pelosi": "representative",
      # ... 시장 영향력 기준 상위 20명
  }
  ```
- [ ] 중복 감지: Telegram + GDELT 동일 이벤트 dedup (키워드 유사도)
- [ ] 결과를 Central Hub `POST /api/signal` 로 자동 전송

#### Step 5 — Fishjam 스트림 수집 연동 (Tamas + Jun, Day 3-4)

> **📌 Fishjam 현황 (2026년 기준)**
> - 원본 OSS(Elixir 미디어 서버)는 **아카이브됨** (더 이상 유지보수 안 함)
> - 현재는 **Fishjam Cloud** = 관리형 서비스 (Software Mansion 호스팅)
> - **무료 티어 있음** → 사전 MVP에서도 사용 가능!
> - Client SDK는 그대로 오픈소스 (`@fishjam-cloud/react-client`)

- [ ] Fishjam Cloud 계정 생성 (https://fishjam.io) → 무료 티어 API 키 확보
- [ ] Fishjam SDK로 Bloomberg WebRTC 스트림 수집
  - 영상 + 오디오 동시 수집
  - 오디오 트랙을 Bloomberg 분석 파이프라인에 연결
- [ ] 프론트엔드 Fishjam Player 컴포넌트
  - `@fishjam-cloud/react-client` 사용
  - Bloomberg 영상을 대시보드 좌측 패널에 실시간 재생
- [ ] 참조 문서: https://docs.fishjam.io

#### Step 6 — Smelter 비디오 오버레이 연동 (Andy + Jun, Day 4-5)

> **📌 Smelter 현황 (2026년 기준)**
> - ✅ **완전 오픈소스** (GitHub: software-mansion/smelter)
> - 이전 이름: Live Compositor
> - self-hosted로 아무 제한 없이 사용 가능
> - React 컴포넌트 제공 (`@swmansion/smelter`)
> - 문서: https://smelter.dev

- [ ] Smelter 로컬 설치 (완전 무료, self-hosted)
  - `npm install @swmansion/smelter` (React 컴포넌트)
  - Smelter server 로컬 실행 (Docker 또는 직접 빌드)
- [ ] Bloomberg 영상 위에 오버레이 렌더링
  - Sentiment % 게이지 (Bullish/Bearish)
  - 주요 Driver 텍스트 밴드 (하단 크롤)
  - 리스크 알림 CG 스타일 팝업
- [ ] Fishjam 스트림 → Smelter 컴포지팅 → 프론트엔드 출력 파이프라인
- [ ] 참조: https://github.com/software-mansion/smelter + https://smelter.dev

#### Step 7 — 프론트엔드 전체 구축 (Andy + Jun, Day 3-5)
- [ ] 레이아웃 설계 (2열 그리드)
  - **좌측 열**: Bloomberg 영상 (Fishjam Player + Smelter 오버레이)
  - **우측 열**: Sentiment 게이지, 차트, Driver Feed, Market Data
- [ ] **SentimentGauge 컴포넌트**
  - 반원 게이지 (Bullish 녹색 ↔ Bearish 빨간색)
  - confidence % 표시
  - 이전 → 현재 sentiment 변화 애니메이션
- [ ] **SentimentHistory 컴포넌트**
  - Recharts 기반 시계열 차트
  - X축: 시간, Y축: confidence (-100 Bearish ~ +100 Bullish)
  - 실시간 데이터 포인트 추가 (30초마다)
- [ ] **DriverFeed 컴포넌트**
  - 근거 리스트 (최근 5개 driver)
  - source별 아이콘 + 색상 구분
  - fact_check 배지 표시 (✅ Real / ❌ Fake / ❓ Unverified)
- [ ] **MarketDataBar 컴포넌트**
  - S&P500, VIX, Oil, DXY, Gold 실시간 표시
  - change_pct에 따라 녹색/빨간색 색상
  - 미니 스파크라인 차트
- [ ] **BloombergPlayer 컴포넌트**
  - Fishjam WebRTC 스트림 재생
  - Smelter 오버레이 적용
  - fallback: 정적 이미지 + "Stream Unavailable"
- [ ] **Globe 컴포넌트**
  - globe.gl 기반 3D 지구본
  - 선박/항공 위치 마커 렌더링
  - 마커 클릭 → 상세 정보 팝업
- [ ] **WebSocket Hook** (`useWebSocket.ts`)
  - socket.io-client 연결 관리
  - 자동 재연결 로직
  - `sentiment_update` 이벤트 핸들링
- [ ] **다크 모드 UI 테마**
  - 금융 대시보드 느낌 (Bloomberg Terminal 스타일)
  - 글래스모피즘 카드
  - 부드러운 애니메이션/트랜지션
- [ ] **"마지막 업데이트: T초 전"** 타임스탬프 표시

#### Step 8 — Fallback 데이터 준비 (Day 4-5)
- [ ] `data/fallback/sample_bloomberg.json`
  - 실제 Bloomberg 방송 시나리오 기반 샘플 10건
  - 다양한 sentiment (Bullish/Bearish/Neutral 혼합)
- [ ] `data/fallback/sample_politicians.json`
  - 정치인 발언 샘플 10건 (각 tier별 포함)
  - Real/Fake/Misleading 혼합
- [ ] `data/fallback/sample_timeline.json`
  - 5분 분량의 시뮬레이션 시나리오
  - sentiment 전환 시점 포함 (Bullish → Bearish 반전)
- [ ] Fallback 모드 자동 전환 로직
  - 30초간 Bloomberg 신호 없음 → fallback 데이터 주입
  - 프론트엔드에 "⚠️ Demo Mode" 배지 표시
- [ ] 데모용 트리거 버튼 구현
  - "Inject Fed Rate Cut News" → 즉시 Bullish 시그널
  - "Inject Trade War Escalation" → 즉시 Bearish 시그널
  - "Reset to Neutral" → 초기화

#### Step 9 — 사전 통합 테스트 (E2E) (Day 5-6)
- [ ] 각 팀원 파이프라인 → Central Hub 연결 확인
  - Tamas: Bloomberg → sentiment_score 포함 POST /api/signal → 수신 확인
  - Tim: Politician → sentiment_score 포함 POST /api/signal → 수신 확인
  - Andy: Market Data → sentiment_score 공식 계산 → POST /api/signal → 수신 확인
- [ ] Central Hub → Gemini 추론 → JSON 출력 검증
  - 프롬프트가 §11 형식으로 올바른 JSON 반환하는지
  - 가중치 계산 정확도 확인
  - fallback 가중치 자동 전환 확인
- [ ] WebSocket → 프론트엔드 실시간 렌더링 확인
  - 데이터 전달 지연 < 2초
  - 차트 실시간 업데이트 확인
- [ ] Fishjam 영상 재생 테스트
- [ ] Smelter 오버레이 렌더링 테스트
- [ ] Fallback 시나리오 전체 테스트
- [ ] 5분 연속 운영 안정성 테스트

---

### 🎯 Phase 2: 해커톤 당일 — 마무리 10%

> 사전 MVP가 완성되어 있으므로, 당일은 **전환 + 폴리싱 + 발표**에 집중.

#### Step 10 — Gemini Live API 전환 (당일 오전 1-2시간)
- [ ] 해커톤 제공 Gemini Live API 키 적용 (`.env` 교체)
- [ ] Tamas: Fishjam → Gemini Live API 공식 연동 활성화
  - 참조: https://docs.fishjam.io/tutorials/gemini-live-integration
  - 사전 MVP의 "오디오 추출 → 일반 API" 코드를 "Fishjam → Live API" 파이프라인으로 교체
- [ ] Jun: 종합 추론 → Gemini Live API 세션 전환
  - `gemini_engine.py`에 Live API 세션 모드 추가
  - 30초 배치 → 이벤트 기반 주입 전환
  - 세션 연결 유지 + 자동 재연결 로직
- [ ] Tim: 팩트체크는 일반 API 유지 (변경 없음)
- [ ] 전환 후 E2E 테스트 (30분)

#### Step 11 — UI/UX 폴리싱 (당일 2-3시간)
- [ ] 애니메이션 미세 조정 (게이지, 차트 트랜지션)
- [ ] 반응형 레이아웃 최종 확인
- [ ] 색상/타이포그래피 최종 조정
- [ ] 로딩 상태/에러 상태 UI 완성
- [ ] 데모 시나리오별 최적 화면 레이아웃

#### Step 12 — 추가 기능 (시간 남으면, 당일 1-2시간)
- [ ] 음성 Q&A — 심사위원이 Gemini에 직접 질문
  - 마이크 입력 → Gemini Live API 세션 → 음성 답변
  - "현재 왜 Bullish인가요?" → Gemini가 실시간 답변
- [ ] 알림 시스템 — 급격한 sentiment 변화 시 화면 플래시
- [ ] 과거 이벤트 리플레이 기능

#### Step 13 — 발표 준비 & 데모 리허설 (당일 2-3시간)
- [ ] 발표 자료 제작 (Google Slides / Figma)
  - 문제 정의 → 솔루션 → 아키텍처 → 데모 → 기술 스택
- [ ] 데모 시나리오 확정 (3분 데모)
  1. 초기 상태 (Neutral)
  2. Bloomberg: Fed 금리 동결 시사 → Bullish 반전
  3. SNS: 트럼프 관세 트윗 → 다시 Bearish
  4. Globe에서 선박 이동 시각화
  5. 음성 Q&A (선택)
- [ ] 데모 리허설 3회 이상
- [ ] Fallback 시나리오 대비 (라이브 실패 시 샘플 데이터 전환)

---

## 10. MVP 우선순위 (시간 부족 시 컷라인)

> ⚠️ v2 변경: Fishjam/Smelter가 **Must Have**로 승격됨 (SWM 해커톤 평가 핵심)

```
Must Have (없으면 데모 불가 — 사전 MVP에서 반드시 완성)
  ✅ Central Hub + Gemini 종합 추론 → Sentiment JSON
  ✅ 시장 데이터 연동 (yfinance)
  ✅ 프론트엔드 Sentiment 게이지 + Driver Feed + 히스토리 차트
  ✅ Bloomberg STT + 감성분석 (일반 Gemini API로)
  ✅ Fishjam 스트림 수집 + 영상 재생 ← 승격됨!
  ✅ Smelter 비디오 오버레이 (Sentiment 표시) ← 승격됨!
  ✅ 정치인 SNS 팩트체크 파이프라인
  ✅ Fallback 데이터 + 데모 트리거 버튼

Should Have (있으면 점수 크게 상승 — 사전 MVP에서 최대한 포함)
  🟡 Gemini Live API 전환 (당일)
  🟡 3D Globe 선박/항공 시각화
  🟡 다크 모드 금융 터미널 UI

Nice to Have (시간 남으면 — 당일 추가)
  ⚪ 음성 Q&A (심사위원 ↔ Gemini)
  ⚪ 알림 시스템 (급격한 sentiment 변화)
  ⚪ 과거 이벤트 리플레이
```

---

## 11. 리스크 & 대응

| # | 리스크 | 영향도 | 확률 | 대응 |
|---|--------|--------|------|------|
| 1 | Bloomberg 유튜브 라이브 미송출 | 치명적 | 중간 | CNBC 라이브 fallback + 녹화/샘플 데이터 자동 전환 |
| 2 | Gemini API rate limit / 할당량 초과 | 높음 | 낮음 | 30초 배치로 호출 최소화 + 응답 캐싱 (직전 결과 유지) |
| 3 | Fishjam 연동 실패 | 높음 | 낮음 | HTML5 Video + iframe으로 YouTube 직접 embed fallback |
| 4 | Smelter 오버레이 렌더링 실패 | 중간 | 중간 | 오버레이 없이 별도 HTML 패널로 Sentiment 표시 |
| 5 | 팀원 파이프라인 미완성 | 높음 | 중간 | fallback 샘플 데이터로 해당 소스 즉시 대체 |
| 6 | 시장 휴장 (주말/공휴일) | 중간 | 예측 | 마지막 거래일 데이터 + "시장 휴장" 표시 + 시뮬레이션 모드 |
| 7 | Gemini Live API 키 당일 수급 지연 | 높음 | 낮음 | 무료 일반 API로 계속 운영 (이미 동작하므로 데모 가능) |
| 8 | WebSocket 연결 끊김 | 중간 | 낮음 | 자동 재연결 + 마지막 상태 유지 + 재연결 UI 표시기 |

---

## 12. Gemini 종합 추론 프롬프트 (확정판)

### 12-1. 종합 추론 프롬프트 (Jun — Central Hub)

```
You are a senior financial market analyst. Analyze the following 3 real-time data sources 
and determine the overall market sentiment.

[SOURCE WEIGHTS]
- Real-time Market Indicators (40%): Most objective baseline — prices don't lie
- Bloomberg Broadcast Analysis (35%): Expert analysis + breaking news
- Politician Statements (25%): Policy signals (filtered by fact-check results)

[ANALYSIS RULES]
1. PERSON WEIGHT: Statements from sitting President and Fed Chair carry 3x weight vs regular legislators
2. FACT FILTER: If fact_check == "Fake", completely ignore that statement
3. KEYWORD WEIGHT: Bloomberg mentions of Fed, interest rate, inflation, GDP, employment → higher weight
4. DEDUP: If multiple sources point to the same event, don't double-count — raise confidence instead
5. TIME DECAY: Data < 5min old > 5-30min > 30min+
6. MARKET STATUS: If market_status == "closed", note this and weight recent news higher
7. If any source has no data, redistribute its weight proportionally to available sources

[INPUT DATA]
Bloomberg Analysis: {bloomberg_data}
Politician Statements: {politician_data}
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
      "source": "bloomberg" or "politician" or "market_data",
      "sentiment_score": integer -100 to +100 (source's individual score),
      "signal": "one-sentence summary of the key signal",
      "weight": float (0.25, 0.35, or 0.40)
    }}
  ],
  "reasoning": "2-3 sentence explanation of your overall judgment"
}}
```

### 12-2. Bloomberg 감성분석 프롬프트 (Tamas)

```
You are a financial media analyst. Analyze the following Bloomberg TV audio transcript segment
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
  "source": "bloomberg",
  "sentiment_score": integer -100 to +100,
  "confidence": integer 0-100,
  "signal": "one-sentence summary of the key information",
  "keywords": ["keyword1", "keyword2", ...],
  "segment_duration_sec": {duration}
}}
```

### 12-3. 팩트체크 프롬프트 (Tim)

```
You are a political fact-checker specializing in financial market impact. 
Verify the following politician's statement and assess its potential market impact.

[STATEMENT]
Author: {author}
Tier: {tier}
Platform: {platform}
Text: "{statement_text}"

[RULES]
1. Check if the statement is factually accurate based on your knowledge
2. Assess whether this could realistically move markets
3. Identify which sectors would be most affected
4. For unverifiable future claims (e.g., "I will impose tariffs"), mark as "Unverified" not "Fake"

[OUTPUT — respond ONLY with this JSON, no other text]
{{
  "source": "politician",
  "sentiment_score": integer -100 to +100 (if fact_check is Fake, must be 0),
  "confidence": integer 0-100,
  "signal": "one-sentence market impact summary",
  "author": "{author}",
  "platform": "{platform}",
  "tier": "{tier}",
  "fact_check": "Real" or "Fake" or "Unverified" or "Misleading",
  "fact_check_reasoning": "one-sentence explanation",
  "affected_sectors": ["sector1", "sector2"]
}}
```

---

## 13. 디렉토리 구조 (확정)

```
Hackathon/
├── backend/
│   ├── main.py                    # FastAPI 서버 진입점 + 라우터
│   ├── config.py                  # SOURCE_WEIGHTS, FALLBACK_WEIGHTS, 상수
│   ├── models.py                  # Pydantic 스키마 (BloombergSignal, etc.)
│   ├── market_data.py             # yfinance 시장 데이터 수집 (30초 폴링)
│   ├── gemini_engine.py           # Gemini 종합 추론 모듈 (일반 API)
│   ├── gemini_live_engine.py      # Gemini Live API 세션 모듈 (당일 전환용)
│   ├── signal_queue.py            # 소스별 시그널 큐 관리
│   ├── scheduler.py               # 30초 배치 스케줄러
│   ├── bloomberg_processor.py     # Tamas: Bloomberg 오디오 → STT → 감성분석
│   ├── youtube_resolver.py        # YouTube 라이브 스트림 URL 자동 탐지
│   ├── telegram_monitor.py        # Tim: Telethon 기반 Telegram 채널 모니터링
│   ├── gdelt_collector.py         # Tim: GDELT 글로벌 뉴스/정치 이벤트 수집
│   ├── politician_checker.py      # Tim: Gemini 팩트체크 모듈
│   ├── fallback_manager.py        # Fallback 데이터 자동 전환 관리
│   ├── websocket_server.py        # socket.io 서버 (프론트엔드 push)
│   ├── requirements.txt
│   └── .env                       # API 키 (gitignore)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # 메인 앱 + 레이아웃
│   │   ├── theme.ts               # 다크 모드 금융 터미널 테마
│   │   ├── components/
│   │   │   ├── SentimentGauge.tsx  # 반원 게이지 (Bullish/Bearish)
│   │   │   ├── SentimentHistory.tsx # Recharts 시계열 차트
│   │   │   ├── DriverFeed.tsx     # 근거/Driver 리스트
│   │   │   ├── MarketDataBar.tsx  # S&P/VIX/Oil 실시간 바
│   │   │   ├── BloombergPlayer.tsx # Fishjam 영상 + Smelter 오버레이
│   │   │   ├── Globe.tsx          # globe.gl 3D 지구본
│   │   │   ├── DemoControls.tsx   # 데모 트리거 버튼 패널
│   │   │   └── StatusBar.tsx      # 연결 상태 + 마지막 업데이트
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    # socket.io 연결 관리
│   │   │   └── useSentiment.ts    # sentiment 상태 관리
│   │   └── types/
│   │       └── index.ts           # TypeScript 타입 정의
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── data/
│   └── fallback/
│       ├── sample_bloomberg.json      # Bloomberg 샘플 10건
│       ├── sample_politicians.json    # 정치인 발언 샘플 10건
│       └── sample_timeline.json       # 5분 시뮬레이션 시나리오
│
├── .env.example                       # 환경변수 템플릿
├── .gitignore
├── EXECUTION_PLAN.md                  # 이 파일
└── README.md
```

---

## 14. 참조 문서 & Skills

### 필수 참조 문서
| 문서 | URL | 용도 |
|------|-----|------|
| Fishjam 공식 문서 | https://docs.fishjam.io | WebRTC 스트림 수집/재생 |
| Fishjam x Gemini Live 연동 | https://docs.fishjam.io/tutorials/gemini-live-integration | 당일 Live API 전환 핵심 |
| Smelter 공식 문서 | https://smelter.dev | 비디오 컴포지팅 오버레이 |
| Smelter GitHub | https://github.com/software-mansion/smelter | 소스 코드 + 설치 |
| Gemini API 문서 | https://ai.google.dev/docs | 일반 API 사용법 |
| Gemini Live API 문서 | https://ai.google.dev/docs/gemini-api/live | Live API 세션 관리 |
| yfinance 문서 | https://github.com/ranaroussi/yfinance | 시장 데이터 수집 |
| FastAPI 문서 | https://fastapi.tiangolo.com | Python 백엔드 |
| Telethon 문서 | https://docs.telethon.dev | Telegram 공개 채널 모니터링 |
| GDELT Project | https://www.gdeltproject.org | 글로벌 뉴스/정치 이벤트 DB |
| gdeltdoc (Python) | https://github.com/alex9smith/gdelt-doc-api | GDELT Doc API Python 클라이언트 |

### 활용 가능한 Skills
| 스킬 | 상태 | 용도 |
|------|------|------|
| `gemini-live-api-dev` | ✅ 이미 로드됨 | Gemini Live API 개발 가이드 + Fishjam 연동 링크 |

---

## 15. 체크리스트 요약 (사전 MVP 완성도 트래킹)

| 영역 | 완료 | 담당 | 상태 |
|------|------|------|------|
| 환경 세팅 & API 키 | ⬜ 0/7 | Jun | 미시작 |
| Central Hub 백엔드 | ⬜ 0/8 | Jun | 미시작 |
| Bloomberg 파이프라인 | ⬜ 0/5 | Tamas | 미시작 |
| 정치인 SNS 파이프라인 | ⬜ 0/7 | Tim | 미시작 |
| Fishjam 스트림 연동 | ⬜ 0/4 | Tamas+Jun | 미시작 |
| Smelter 오버레이 | ⬜ 0/4 | Andy+Jun | 미시작 |
| 프론트엔드 전체 | ⬜ 0/11 | Andy+Jun | 미시작 |
| Fallback 데이터 | ⬜ 0/5 | Jun | 미시작 |
| E2E 통합 테스트 | ⬜ 0/7 | 전원 | 미시작 |
| **합계** | **⬜ 0/58** | | |
