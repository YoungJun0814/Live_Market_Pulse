# 🎯 에이전트 프롬프팅 전략 — 해커톤 당일 배틀 플랜

> **목적**: 6시간 해커톤에서 AI 코딩 에이전트를 **최대 효율**로 활용하기 위한 전략
> **핵심**: 프롬프트를 "언제, 어떤 순서로, 어떤 세션에서" 날릴지가 승부를 가른다

---

## 🚨 절대 규칙 (모든 세션에 적용)

```
1. 모든 세션의 첫 프롬프트: "먼저 EXECUTION_PLAN_EN.md를 읽어줘"
2. 한 세션 = 한 모듈 (backend/frontend/smelter 절대 섞지 않기)
3. 에이전트한테 "대시보드 만들어줘" 같은 한 줄 프롬프트 금지
4. 프롬프트에 반드시 [Context] + [Task] + [완료 조건] 3계층 포함
5. 이전 세션 결과물이 필요한 프롬프트는 → 검증 후에만 다음 진행
```

---

## 📋 전체 흐름 요약

```
Wave 1 (Hour 0-1)        Wave 2 (Hour 1-3)           Wave 3 (Hour 3-5)        Hour 5-6
 ┌─────────┐        ┌──────────────────────┐     ┌─────────────────┐     ┌──────────┐
 │ 환경 셋업 │   ──→  │ 4개 세션 동시 가동     │ ──→ │ 통합 + Smelter   │ ──→ │ 데모 준비 │
 │ (수동)    │        │                      │     │ + Map/Panel      │     │ (수동)    │
 └─────────┘        │ S1: Jun 백엔드        │     └─────────────────┘     └──────────┘
                     │ S2: Andy 프론트엔드   │
                     │ S3: Tamas Fishjam    │
                     │ S4: Tim RSS          │
                     └──────────────────────┘
```

---

## Wave 1: 환경 셋업 (Hour 0-1) — 에이전트 안 씀

> ⚠️ 이 단계는 **수동으로** 진행. 에이전트에게 맡기면 시간 낭비.

### 체크리스트
```bash
# 1. Git clone + 환경 설정
git clone <repo-url>
cd Hackathon
cp .env.example backend/.env
# .env에 실제 API 키 입력 (GOOGLE_API_KEY, FISHJAM_ID, MGMT_TOKEN 등)

# 2. Backend 의존성
cd backend
pip install -r requirements.txt

# 3. Frontend 초기화 → Wave 2의 세션 S2에서 에이전트가 처리

# 4. Smelter 초기화
cd ../smelter
npm install

# 5. Fishjam Cloud 연결 테스트
python -c "from fishjam import FishjamClient; print('OK')"
```

### Wave 1 → Wave 2 게이트 조건
- [ ] `.env` 키 전부 입력됨
- [ ] `pip install` 성공
- [ ] `import fishjam` 성공
- [ ] 팀원 4명 모두 Git clone 완료

---

## Wave 2: 병렬 모듈 개발 (Hour 1-3) — 🔥 핵심

> **4개 세션을 동시에 가동.** 각 팀원이 자기 에이전트 세션을 운영.
> 서로 독립적이므로 간섭 없음. JSON 스키마는 EXECUTION_PLAN에 이미 확정.

### 세션 배치

```
┌─────────────────────────────────────────────────────────┐
│  Jun의 에이전트          Andy의 에이전트                   │
│  [세션 S1: 백엔드]       [세션 S2: 프론트엔드]              │
│                                                         │
│  Tamas의 에이전트        Tim의 에이전트                    │
│  [세션 S3: Fishjam]     [세션 S4: RSS]                   │
└─────────────────────────────────────────────────────────┘
         ↓ 모두 완료되면 (Hour 3)
┌─────────────────────────────────────────────────────────┐
│  [세션 S5: 통합 + Smelter]  [세션 S6: Map + Panel]       │
└─────────────────────────────────────────────────────────┘
```

---

### 세션 S1: Jun — Central Hub 백엔드

**프롬프트 순서: 1개 대형 프롬프트로 한 번에**

```
먼저 EXECUTION_PLAN_EN.md를 읽어줘.

[Context]
- 기존 코드: backend/ 디렉토리에 market_engine.py (Andy의 5-Layer 엔진, 수정 금지),
  .env, requirements.txt가 있음
- 아키텍처: FastAPI + python-socketio + Gemini Live API

[Task]
EXECUTION_PLAN_EN.md의 Section 3 (Architecture), Section 5 (Data Schema),
Section 6 (Weights)을 기반으로 다음 백엔드 파일들을 생성해줘:

1. backend/main.py — FastAPI 서버 진입점
   - POST /api/signal (Pydantic 검증)
   - GET /health
   - CORS 허용 (localhost:5173)
   - socket.io 마운트

2. backend/config.py — 상수 (Section 6의 값 그대로)
   - SOURCE_WEIGHTS, FALLBACK_WEIGHTS, SENTIMENT_THRESHOLDS
   - AUTOPILOT_THRESHOLD=60, AUTOPILOT_COOLDOWN_SEC=30

3. backend/models.py — Section 5-1 ~ 5-5 JSON을 Pydantic BaseModel로

4. backend/signal_queue.py — dict[str, deque], 30초 만료

5. backend/websocket_server.py — socket.io
   - "sentiment_update" (Section 5-4), "focus_region" (Section 5-5)
   - should_trigger_autopilot() 포함

6. backend/scheduler.py — apscheduler 30초 배치

[완료 조건]
- uvicorn backend.main:app --reload 실행 가능
- /health → 200 OK
- /docs → Swagger UI 확인 가능
```

**✅ 검증**: `uvicorn backend.main:app --reload` → `/health` 200 확인

---

### 세션 S2: Andy — 프론트엔드

**프롬프트 순서: 2단계로 나눔 (레이아웃 먼저 → 컴포넌트)**

#### S2 Step 1: 프로젝트 초기화 + 레이아웃

```
먼저 EXECUTION_PLAN_EN.md를 읽어줘.

[Context]
- React 18 + Vite + TypeScript 프로젝트를 frontend/ 디렉토리에 생성
- 디자인: Dark Mode 금융 터미널 (배경 #0D1117, 테두리 #30363D)
- 데이터 색상: Bullish=#00FF88, Bearish=#FF4444, Neutral=#FFAA00
- 글래스모피즘: backdrop-filter: blur(12px)
- CSS Framework: Vanilla CSS (TailwindCSS 사용하지 않음)
- ⚠️ Zone 3의 LiveNewsPlayer는 Fishjam WHEP Player임 (CSS 오버레이 아님)

[Task]
1. frontend/에 React + Vite + TypeScript 초기화
2. Section 8 와이어프레임 기준 CSS Grid 6영역 레이아웃
3. types/index.ts: Section 5-4 스키마를 TypeScript interface로
4. hooks: useWebSocket.ts + useSentiment.ts

[완료 조건]
- npm run dev → localhost:5173에서 6영역 그리드 표시
```

**✅ 검증**: `npm run dev` → 브라우저에서 6영역 그리드 확인 → Step 2

#### S2 Step 2: 컴포넌트 구현

```
이전 작업에 이어서 진행해줘.

[Task]
다음 컴포넌트들을 구현해줘:
1. SentimentGauge.tsx: 반원 게이지 (-100~+100), framer-motion 애니메이션
2. SentimentHistory.tsx: Recharts 꺾은선 그래프 (최근 30분)
3. MarketDrivers.tsx: 2x3 스파크라인 격자
4. DriverFeed.tsx: 팩트체크 카드 시간순 스크롤
5. LiveNewsPlayer.tsx: Fishjam WHEP Player (Section 7-2 하단 코드 참조)
6. HeadlinesTicker.tsx: 하단 마퀴 스크롤

모든 컴포넌트에 다크 모드 스타일 적용

[완료 조건]
- 각 Zone에 실제 컴포넌트가 렌더링 (더미 데이터로)
```

---

### 세션 S3: Tamas — Fishjam Agent SDK

**프롬프트: 1개 대형 프롬프트**

```
먼저 EXECUTION_PLAN_EN.md를 읽어줘.
⚠️ 반드시 Section 7-1의 "Fishjam Agent SDK + Gemini Built-in Integration" 코드와
Section 7-3의 "Tamas Pipeline Spec Modifications" 표를 확인해줘.

[Context]
- Fishjam Cloud (SaaS) 사용 — Docker self-hosted 아님
- fishjam-server-sdk[gemini] 빌트인 모듈 — 수동 WebSocket 아님
- Agent SDK가 오디오 샘플레이트 자동 매칭 (16kHz in / 24kHz out)
- Redis 불필요 — Agent가 직접 Gemini에 스트리밍
- Bloomberg 우선, Sky News 폴백

[Task]
1. backend/youtube_resolver.py: try_bloomberg() → SKY_NEWS_URL 폴백
2. backend/fishjam_audio_agent.py (핵심):
   - Section 7-1의 Agent SDK 코드 기반
   - FishjamClient → Room → Agent → GeminiIntegration
   - 양방향 브릿지: forward_audio_to_gemini() + forward_audio_to_fishjam()
   - sentiment JSON 추출 → POST /api/signal
3. backend/rss_econ_collector.py: Google News Finance/Econ RSS 폴링
   - RSS URL: https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen
4. 출력: Section 5-1 스키마, 프롬프트: Section 14-2

[완료 조건]
- Bloomberg/Sky News URL 자동 탐지
- Gemini가 오디오에서 감성 추출
- /api/signal에 JSON 도착
```

---

### 세션 S4: Tim — RSS + 팩트체크

**프롬프트: 1개 대형 프롬프트**

```
먼저 EXECUTION_PLAN_EN.md를 읽어줘.
Section 10 (RSS Feed Guide), Section 5-2 (Output Schema), Section 14-3 (Fact Check Prompt) 참조.

[Context]
- rss.app 정치/Twitter RSS 피드 사용
- RSS URL: https://rss.app/rss-feed?keyword=Iran%20Israel&region=US&lang=en
- Gemini API (Classic)로 팩트체크 + 도시 좌표 추출
- Section 14-3 프롬프트 정확히 사용

[Task]
1. backend/rss_political_collector.py: 정치/Twitter RSS 2~5분 폴링
2. backend/politician_checker.py: Gemini 팩트체크 + event_location
3. 출력: Section 5-2 정확히 준수

[완료 조건]
- RSS 뉴스 수집 + Gemini 팩트체크 + event_location 반환
- /api/signal에 JSON 도착
```

---

### ⛩️ Wave 2 → Wave 3 게이트

```
✅ 확인 항목:
  [ ] 백엔드: uvicorn 실행 + /api/signal POST 수신
  [ ] 프론트: npm run dev + 6영역 그리드 표시
  [ ] Fishjam: Agent → Gemini 오디오 전달 + JSON 응답
  [ ] RSS: 뉴스 수집 + 팩트체크 JSON 생성

→ 4개 모두 통과: Wave 3 시작
→ 실패 항목만 디버그 (나머지는 Wave 3 선진입)
```

---

## Wave 3: 통합 + Smelter + Map (Hour 3-5)

### 세션 S5: 통합 + Smelter

**Step 1: WebSocket 통합**
```
먼저 EXECUTION_PLAN_EN.md를 읽어줘.

[Task]
1. backend socket.io emit 테스트 스크립트 작성
2. curl POST /api/signal → 프론트 게이지 반응 확인
```

**Step 2: Smelter 서버**
```
EXECUTION_PLAN_EN.md Section 7-2 참고.

[Task]
1. smelter/scenes/MarketOverlayScene.tsx (Section 7-2 코드 기반)
2. smelter/server.ts (WebSocket 수신 + WHIP 출력)
```

### 세션 S6: Map + Panel + DemoControls

```
EXECUTION_PLAN_EN.md Section 8-1, 8-2 참고.

[Task]
1. WorldMap.tsx (react-leaflet + Pulse 마커)
2. CountryNewsPanel.tsx (글래스모피즘 slide-in)
3. DemoControls.tsx (3개 시뮬레이션 버튼)
4. data/country_profiles.json (10개국)
```

---

## 📊 시간별 세션 운용 맵

```
Hour  │ Jun              │ Andy             │ Tamas            │ Tim
──────┼──────────────────┼──────────────────┼──────────────────┼────────────────
 0-1  │ 환경 셋업 (수동)   │ 환경 셋업 (수동)   │ 환경 셋업 (수동)  │ 환경 셋업 (수동)
──────┼──────────────────┼──────────────────┼──────────────────┼────────────────
  1-2  │ S1: 백엔드        │ S2-1: 레이아웃    │ S3: Fishjam      │ S4: RSS
 2-3  │ S1: (이어서)      │ S2-2: 컴포넌트    │ S3: (이어서)     │ S4: (이어서)
──────┼──────────────────┼──────────────────┼──────────────────┼────────────────
 3-4  │ S5: 통합 테스트    │ (대기/지원)       │ S5: Smelter      │ (대기/지원)
      │ S6: Map+Panel    │                  │                  │
──────┼──────────────────┼──────────────────┼──────────────────┼────────────────
 4-5  │ S6: (디버그)      │ S2: Demo+폴리시   │ S5: (디버그)     │ (지원)
──────┼──────────────────┼──────────────────┼──────────────────┼────────────────
 5-6  │ 🎤 데모 리허설     │ 🎤 데모 리허설    │ 🎤 데모 리허설    │ 🎤 데모 리허설
```

---

## 🚑 트러블슈팅 의사결정 트리

### 에이전트가 잘못된 코드를 생성했을 때

```
├── 구조적 문제 (스키마 불일치)
│     → "EXECUTION_PLAN_EN.md Section X를 다시 읽고
│        [구체적 JSON 필드]를 확인한 후 수정해줘"
│
├── 사소한 버그 (import 에러, 타입)
│     → "에러 메시지: [복붙]. 이 에러를 수정해줘"
│
└── 완전히 방향이 틀림
      → 세션 새로 열고 처음부터 (기존 세션 컨텍스트 오염됨)
```

### ⏰ Hour 4 시점 — 시간 부족 판단

```
├── Smelter 안 됨
│     → CSS 오버레이 폴백 (Section 13 Risk #4)
│
├── Map 안 됨
│     → placeholder + "Coming Soon"
│
├── Fishjam Agent 안 됨
│     → DemoControls 버튼이 전체 시나리오 대체
│
└── 전부 성공
      → Hour 5-6 데모 리허설에 올인
```

---

## 💡 프롬프트 패턴 치트시트

| 상황 | ❌ 나쁜 프롬프트 | ✅ 좋은 프롬프트 |
|------|----------------|----------------|
| 전체 요청 | "대시보드 만들어줘" | "EXECUTION_PLAN_EN.md를 읽고 Section 8 기준으로..." |
| WebSocket | "WebSocket 추가해줘" | "socket.io 'sentiment_update' 이벤트, 스키마는 Section 5-4" |
| 디자인 | "예쁘게 만들어줘" | "배경 #0D1117, 네온 #00FF88, blur(12px), 폰트 Inter" |
| 이어서 | "이전에 만든 파일 수정해줘" | "SentimentGauge.tsx에서 게이지 색상을 값에 따라 변경해줘" |
| 에러 | "안 돼" | "에러: [복붙]. backend/main.py만 수정해줘" |
| 스키마 | 직접 JSON 설명 | "Section 5-4의 JSON 스키마를 정확히 따라" |

---

## ✅ 데모 전 최종 체크리스트 (Hour 5)

- [ ] `uvicorn` 실행 중
- [ ] `npm run dev` 실행 중
- [ ] WebSocket sentiment_update 수신 확인
- [ ] DemoControls 3개 버튼 동작
- [ ] [Trade War] → 6개 Zone 연쇄 반응
- [ ] [Fed Rate Cut] → 반전 시나리오
- [ ] Smelter 합성 영상 Zone 3 표시 (or CSS 폴백)
- [ ] Map 마커 + Panel 동작 (or placeholder)
- [ ] 발표 스크립트 3회 리허설 완료
