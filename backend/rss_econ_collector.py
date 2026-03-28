from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse

import feedparser
import requests

from backend.config import (
    CENTRAL_HUB_SIGNAL_URL,
    RSS_POLL_INTERVAL_SECONDS,
    TAMAS_ECON_RSS_URL,
)
from backend.models import NewsStreamSignal


@dataclass(slots=True)
class EconHeadline:
    title: str
    summary: str
    link: str
    published: datetime


class RssEconCollector:
    def __init__(
        self,
        feed_url: str = TAMAS_ECON_RSS_URL,
        hub_url: str = CENTRAL_HUB_SIGNAL_URL,
    ) -> None:
        self.feed_url = feed_url
        self.hub_url = hub_url
        self.session = requests.Session()
        self.seen_ids: set[str] = set()

    def collect_new_entries(self, limit: int = 5) -> list[EconHeadline]:
        parsed = self._load_feed()
        entries: list[EconHeadline] = []

        for item in parsed.entries[:limit]:
            entry = EconHeadline(
                title=self._clean_text(item.get("title", "")),
                summary=self._clean_text(item.get("summary", "") or item.get("description", "")),
                link=item.get("link", ""),
                published=self._published_at(item),
            )
            entry_id = entry.link or entry.title
            if not entry_id or entry_id in self.seen_ids:
                continue
            self.seen_ids.add(entry_id)
            entries.append(entry)

        return entries

    def build_signal(self, entry: EconHeadline) -> NewsStreamSignal:
        score, keywords = self._score_text(f"{entry.title} {entry.summary}")
        confidence = min(88, 58 + len(keywords) * 6)

        return NewsStreamSignal(
            source="news_stream",
            sentiment_score=score,
            confidence=confidence,
            signal=entry.title,
            timestamp=entry.published,
            keywords=keywords,
            data_origin="google_news_rss",
            segment_duration_sec=30,
        )

    def publish(self, signal: NewsStreamSignal) -> requests.Response:
        return self.session.post(
            self.hub_url,
            json=signal.model_dump(mode="json"),
            timeout=15,
        )

    def push_new_signals(self, limit: int = 5) -> int:
        count = 0
        for entry in self.collect_new_entries(limit=limit):
            response = self.publish(self.build_signal(entry))
            response.raise_for_status()
            count += 1
        return count

    def run_forever(self, interval_seconds: int = RSS_POLL_INTERVAL_SECONDS) -> None:
        while True:
            try:
                pushed = self.push_new_signals()
                print(
                    f"[rss_econ_collector] pushed={pushed} at {datetime.now(UTC).isoformat()}"
                )
            except Exception as exc:
                print(f"[rss_econ_collector] error: {exc}")
            time.sleep(interval_seconds)

    def _published_at(self, item: feedparser.FeedParserDict) -> datetime:
        parsed = item.get("published_parsed") or item.get("updated_parsed")
        if parsed is None:
            return datetime.now(UTC)
        return datetime(*parsed[:6], tzinfo=UTC)

    def _load_feed(self) -> feedparser.FeedParserDict:
        normalized_url = self._normalize_google_news_url(self.feed_url)
        response = self.session.get(
            normalized_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        return feedparser.parse(response.content)

    def _normalize_google_news_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc != "news.google.com" or parsed.path.startswith("/rss/"):
            return url

        normalized_path = parsed.path
        if normalized_path.startswith("/topics/"):
            normalized_path = "/rss" + normalized_path

        return urlunparse(parsed._replace(path=normalized_path))

    def _clean_text(self, value: str) -> str:
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _score_text(self, text: str) -> tuple[int, list[str]]:
        lowered = text.lower()
        positive = {
            "rate cut": 18,
            "soft landing": 22,
            "cooling inflation": 18,
            "beats expectations": 16,
            "jobs growth": 12,
            "stimulus": 14,
            "rebound": 14,
        }
        negative = {
            "recession": 28,
            "tariff": 18,
            "inflation spike": 24,
            "layoffs": 18,
            "default": 30,
            "downgrade": 20,
            "shutdown": 18,
        }

        score = 0
        hits: list[str] = []

        for keyword, weight in positive.items():
            if keyword in lowered:
                score += weight
                hits.append(keyword)
        for keyword, weight in negative.items():
            if keyword in lowered:
                score -= weight
                hits.append(keyword)

        score = max(-100, min(100, score))
        return score, hits or ["macro", "finance"]


if __name__ == "__main__":
    RssEconCollector().run_forever()
