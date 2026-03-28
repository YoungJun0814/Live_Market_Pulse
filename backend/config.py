import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SOURCE_WEIGHTS = {
    "market_data": 0.40,
    "news_stream": 0.35,
    "politician": 0.25,
}

FALLBACK_WEIGHTS = {
    "no_news": {"market_data": 0.55, "politician": 0.45},
    "no_politician": {"market_data": 0.55, "news_stream": 0.45},
    "only_market": {"market_data": 1.0},
}

SENTIMENT_THRESHOLDS = {
    "bullish": 21,
    "bearish": -21,
}

AUTOPILOT_THRESHOLD = 20
AUTOPILOT_COOLDOWN_SEC = 12
SCHEDULER_INTERVAL_SECONDS = 30
RSS_POLL_INTERVAL_SECONDS = int(os.getenv("RSS_POLL_INTERVAL_SECONDS", "180"))
# Keep RSS-derived signals alive slightly longer than the polling cadence
# so freshness badges do not drop to "No update" between feed refreshes.
QUEUE_TTL_SECONDS = max(90, RSS_POLL_INTERVAL_SECONDS + 30)

FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CENTRAL_HUB_SIGNAL_URL = os.getenv(
    "CENTRAL_HUB_SIGNAL_URL",
    "http://localhost:8000/api/signal",
)
TAMAS_ECON_RSS_URL = os.getenv(
    "TAMAS_ECON_RSS_URL",
    "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen",
)
TIM_POLITICAL_RSS_URL = os.getenv(
    "TIM_POLITICAL_RSS_URL",
    "https://rss.app/feeds/tA3pNMK5UFhgzWBe.xml",
)
TIM_GEMINI_MODEL = os.getenv("TIM_GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_LIVE_MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "gemini-2.5-flash-native-audio-preview-12-2025",
)
FISHJAM_ID = os.getenv("FISHJAM_ID", "")
FISHJAM_MANAGEMENT_TOKEN = os.getenv("FISHJAM_MANAGEMENT_TOKEN", "")
FISHJAM_ROOM_ID = os.getenv("FISHJAM_ROOM_ID", "")
FISHJAM_WHIP_ENDPOINT = os.getenv("FISHJAM_WHIP_ENDPOINT", "")
FISHJAM_WHEP_ENDPOINT = os.getenv("FISHJAM_WHEP_ENDPOINT", "")
FISHJAM_STREAMER_TOKEN = os.getenv("FISHJAM_STREAMER_TOKEN", "")
LIVE_NEWS_SOURCE_URL = os.getenv(
    "LIVE_NEWS_SOURCE_URL",
    "https://www.youtube.com/watch?v=YDvsBbKfLPA",
)

COUNTRY_PROFILE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "country_profiles.json"
)
