from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote_plus, urlparse

import feedparser
import requests

from backend.config import (
    CENTRAL_HUB_SIGNAL_URL,
    RSS_POLL_INTERVAL_SECONDS,
    TIM_POLITICAL_RSS_URL,
)
from backend.politician_checker import PoliticalArticle, PoliticianChecker


class RssPoliticalCollector:
    def __init__(
        self,
        feed_url: str = TIM_POLITICAL_RSS_URL,
        hub_url: str = CENTRAL_HUB_SIGNAL_URL,
        checker: PoliticianChecker | None = None,
    ) -> None:
        self.feed_url = feed_url
        self.hub_url = hub_url
        self.session = requests.Session()
        self.checker = checker or PoliticianChecker()
        self.seen_ids: set[str] = set()

    def collect_new_entries(self, limit: int = 5) -> list[PoliticalArticle]:
        parsed = self._load_feed()
        articles: list[PoliticalArticle] = []

        for item in parsed.entries[:limit]:
            link = item.get("link", "")
            title = self._clean_text(item.get("title", ""))
            entry_id = link or title
            if not entry_id or entry_id in self.seen_ids:
                continue

            summary = self._clean_text(item.get("summary", "") or item.get("description", ""))
            summary = self._expand_summary_if_needed(link, summary)
            article = PoliticalArticle(
                title=title,
                summary=summary,
                link=link,
                published=self._published_at(item),
                source=item.get("source", {}).get("title") if isinstance(item.get("source"), dict) else None,
                author=item.get("author"),
            )
            self.seen_ids.add(entry_id)
            articles.append(article)

        return articles

    def publish_signal(self, article: PoliticalArticle) -> requests.Response:
        signal = self.checker.check_article(article)
        return self.session.post(
            self.hub_url,
            json=signal.model_dump(mode="json"),
            timeout=15,
        )

    def push_new_signals(self, limit: int = 5) -> int:
        count = 0
        for article in self.collect_new_entries(limit=limit):
            response = self.publish_signal(article)
            response.raise_for_status()
            count += 1
        return count

    def run_forever(self, interval_seconds: int = RSS_POLL_INTERVAL_SECONDS) -> None:
        while True:
            try:
                pushed = self.push_new_signals()
                print(
                    f"[rss_political_collector] pushed={pushed} at {datetime.now(timezone.utc).isoformat()}"
                )
            except Exception as exc:
                print(f"[rss_political_collector] error: {exc}")
            time.sleep(interval_seconds)

    def _published_at(self, item: feedparser.FeedParserDict) -> datetime:
        parsed = item.get("published_parsed") or item.get("updated_parsed")
        if parsed is None:
            return datetime.now(timezone.utc)
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    def _load_feed(self) -> feedparser.FeedParserDict:
        response = self.session.get(
            self.feed_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        if response.text.lstrip().startswith("<?xml"):
            return feedparser.parse(response.content)

        fallback_url = self._build_keyword_fallback_url(self.feed_url)
        fallback = self.session.get(
            fallback_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        fallback.raise_for_status()
        return feedparser.parse(fallback.content)

    def _build_keyword_fallback_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        keywords = query.get("keyword", ["Iran Israel"])[0]
        q = quote_plus(keywords)
        return (
            "https://news.google.com/rss/search"
            f"?q={q}&hl=en-US&gl=US&ceid=US%3Aen"
        )

    def _clean_text(self, value: str) -> str:
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _expand_summary_if_needed(self, link: str, summary: str) -> str:
        if len(summary) >= 120 or not link:
            return summary

        try:
            response = self.session.get(link, timeout=10)
            response.raise_for_status()
        except Exception:
            return summary

        patterns = [
            r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"',
            r'<meta[^>]+name="description"[^>]+content="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                expanded = self._clean_text(match.group(1))
                if expanded:
                    return expanded
        return summary


if __name__ == "__main__":
    RssPoliticalCollector().run_forever()
