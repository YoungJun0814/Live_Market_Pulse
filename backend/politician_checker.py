from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

from backend.config import TIM_GEMINI_MODEL
from backend.models import EventLocation, PoliticianSignal

load_dotenv()

LOCATION_LOOKUP: dict[str, EventLocation] = {
    "israel": EventLocation(lat=31.7683, lon=35.2137, city="Jerusalem", country="IL"),
    "iran": EventLocation(lat=35.6892, lon=51.3890, city="Tehran", country="IR"),
    "tel aviv": EventLocation(lat=32.0853, lon=34.7818, city="Tel Aviv", country="IL"),
    "yemen": EventLocation(lat=15.3694, lon=44.1910, city="Sanaa", country="YE"),
    "houthi": EventLocation(lat=15.3694, lon=44.1910, city="Sanaa", country="YE"),
    "red sea": EventLocation(lat=15.0000, lon=41.0000, city="Red Sea", country="YE"),
    "hormuz": EventLocation(lat=26.5660, lon=56.2490, city="Strait of Hormuz", country="OM"),
    "lebanon": EventLocation(lat=33.8938, lon=35.5018, city="Beirut", country="LB"),
    "beirut": EventLocation(lat=33.8938, lon=35.5018, city="Beirut", country="LB"),
    "syria": EventLocation(lat=33.5138, lon=36.2765, city="Damascus", country="SY"),
    "damascus": EventLocation(lat=33.5138, lon=36.2765, city="Damascus", country="SY"),
    "washington": EventLocation(lat=38.9072, lon=-77.0369, city="Washington DC", country="US"),
    "united states": EventLocation(lat=38.9072, lon=-77.0369, city="Washington DC", country="US"),
    "u.s.": EventLocation(lat=38.9072, lon=-77.0369, city="Washington DC", country="US"),
    "white house": EventLocation(lat=38.8977, lon=-77.0365, city="Washington DC", country="US"),
    "beijing": EventLocation(lat=39.9042, lon=116.4074, city="Beijing", country="CN"),
    "moscow": EventLocation(lat=55.7558, lon=37.6176, city="Moscow", country="RU"),
    "kyiv": EventLocation(lat=50.4501, lon=30.5234, city="Kyiv", country="UA"),
    "brussels": EventLocation(lat=50.8503, lon=4.3517, city="Brussels", country="BE"),
    "tehran": EventLocation(lat=35.6892, lon=51.3890, city="Tehran", country="IR"),
    "gaza": EventLocation(lat=31.5017, lon=34.4668, city="Gaza", country="PS"),
}


@dataclass(slots=True)
class PoliticalArticle:
    title: str
    summary: str
    link: str
    published: datetime
    source: str | None = None
    author: str | None = None


class PoliticianChecker:
    def __init__(
        self,
        model_name: str = TIM_GEMINI_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = self._build_model()

    def check_article(self, article: PoliticalArticle) -> PoliticianSignal:
        payload = self._check_with_gemini(article)
        if payload is None:
            payload = self._heuristic_payload(article)
        return self._normalize_payload(payload, article)

    def _build_model(self) -> Any | None:
        if not self.api_key:
            return None

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(self.model_name)
        except Exception:
            return None

    def _check_with_gemini(self, article: PoliticalArticle) -> dict[str, Any] | None:
        if self._model is None:
            return None

        prompt = f"""
You are a political fact-checker specializing in financial market impact.
Return only JSON following this schema:
{{
  "source": "politician",
  "sentiment_score": integer -100 to +100,
  "confidence": integer 0 to 100,
  "signal": "one-sentence market impact summary",
  "author": "speaker or outlet",
  "platform": "rss",
  "tier": "president" | "fed_chair" | "cabinet" | "senator" | "representative" | "other",
  "fact_check": "Real" | "Fake" | "Unverified" | "Misleading",
  "fact_check_reasoning": "one-sentence explanation",
  "affected_sectors": ["sector1", "sector2"],
  "event_location": {{
    "lat": float,
    "lon": float,
    "city": "city",
    "country": "country code"
  }}
}}

Rules:
1. If fact_check is Fake, set sentiment_score to 0.
2. Keep signal short and market-focused.
3. Infer the most relevant city and country for the event.

Article title: {article.title}
Article summary: {article.summary}
Article source: {article.source or "unknown"}
Article author: {article.author or "unknown"}
"""
        try:
            response = self._model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            return self._extract_json(text)
        except Exception:
            return None

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _heuristic_payload(self, article: PoliticalArticle) -> dict[str, Any]:
        text = f"{article.title} {article.summary}".lower()
        negative_hits = {
            "tariff": 24,
            "sanction": 20,
            "attack": 30,
            "missile": 34,
            "war": 36,
            "conflict": 22,
            "strike": 22,
            "oil spike": 18,
        }
        positive_hits = {
            "ceasefire": 34,
            "deal": 18,
            "talks": 14,
            "agreement": 18,
            "pause": 10,
            "stimulus": 16,
        }

        score = 0
        matched_terms: list[str] = []
        for term, weight in negative_hits.items():
            if term in text:
                score -= weight
                matched_terms.append(term)
        for term, weight in positive_hits.items():
            if term in text:
                score += weight
                matched_terms.append(term)

        fact_check = "Real"
        fact_reasoning = "Headline is plausible but was scored with heuristic fallback."
        if any(term in text for term in ["rumor", "reportedly", "unconfirmed"]):
            fact_check = "Unverified"
            fact_reasoning = "Article language suggests the claim is still unverified."
        if any(term in text for term in ["hoax", "fake", "fabricated", "debunked"]):
            fact_check = "Fake"
            fact_reasoning = "Article text indicates the claim is false or debunked."
            score = 0

        location = self._infer_location(text)
        affected_sectors = self._infer_sectors(text)
        author = article.author or self._infer_author(article.title)
        tier = self._infer_tier(author, text)
        confidence = min(90, 58 + len(matched_terms) * 7)

        return {
            "source": "politician",
            "sentiment_score": max(-100, min(100, score)),
            "confidence": confidence,
            "signal": article.title.strip(),
            "author": author,
            "platform": "rss",
            "tier": tier,
            "fact_check": fact_check,
            "fact_check_reasoning": fact_reasoning,
            "affected_sectors": affected_sectors,
            "event_location": location.model_dump(mode="json") if location else None,
        }

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        article: PoliticalArticle,
    ) -> PoliticianSignal:
        payload = dict(payload)
        payload["source"] = "politician"
        payload["platform"] = payload.get("platform") or "rss"
        payload["author"] = payload.get("author") or article.author or article.source or "RSS feed"
        payload["tier"] = payload.get("tier") or self._infer_tier(payload["author"], article.title)
        payload["signal"] = payload.get("signal") or article.title
        payload["confidence"] = int(max(0, min(100, payload.get("confidence", 60))))
        payload["sentiment_score"] = int(max(-100, min(100, payload.get("sentiment_score", 0))))
        payload["fact_check"] = payload.get("fact_check") or "Unverified"
        payload["fact_check_reasoning"] = (
            payload.get("fact_check_reasoning")
            or "No reasoning provided by upstream classifier."
        )
        payload["affected_sectors"] = payload.get("affected_sectors") or self._infer_sectors(
            f"{article.title} {article.summary}".lower()
        )
        payload["timestamp"] = article.published

        location_payload = payload.get("event_location")
        if location_payload:
            if isinstance(location_payload, dict):
                if "lat" not in location_payload or "lon" not in location_payload:
                    inferred = self._infer_location(
                        f"{article.title} {article.summary} {location_payload.get('city', '')}".lower()
                    )
                    if inferred is not None:
                        location_payload = inferred.model_dump(mode="json")
            payload["event_location"] = location_payload
        else:
            inferred = self._infer_location(f"{article.title} {article.summary}".lower())
            payload["event_location"] = inferred.model_dump(mode="json") if inferred else None

        if payload["fact_check"] == "Fake":
            payload["sentiment_score"] = 0

        return PoliticianSignal.model_validate(payload)

    def _infer_location(self, text: str) -> EventLocation | None:
        for keyword, location in LOCATION_LOOKUP.items():
            if keyword in text:
                return location
        return None

    def _infer_author(self, title: str) -> str:
        title_lower = title.lower()
        if "trump" in title_lower:
            return "Donald Trump"
        if "biden" in title_lower:
            return "Joe Biden"
        if "netanyahu" in title_lower:
            return "Benjamin Netanyahu"
        if "khamenei" in title_lower:
            return "Ali Khamenei"
        if "fed" in title_lower or "powell" in title_lower:
            return "Jerome Powell"
        return "RSS political desk"

    def _infer_tier(self, author: str, text: str) -> str:
        combined = f"{author} {text}".lower()
        if any(term in combined for term in ["president", "prime minister", "trump", "biden", "netanyahu", "khamenei"]):
            return "president"
        if any(term in combined for term in ["powell", "fed chair", "fomc"]):
            return "fed_chair"
        if any(term in combined for term in ["minister", "secretary", "cabinet"]):
            return "cabinet"
        if "senator" in combined:
            return "senator"
        if any(term in combined for term in ["representative", "house lawmaker", "mp "]):
            return "representative"
        return "other"

    def _infer_sectors(self, text: str) -> list[str]:
        sectors: list[str] = []
        if any(term in text for term in ["tariff", "trade", "china", "export"]):
            sectors.extend(["Industrials", "Semiconductors"])
        if any(term in text for term in ["oil", "iran", "israel", "middle east", "sanction"]):
            sectors.extend(["Energy", "Airlines"])
        if any(term in text for term in ["attack", "missile", "defense", "war"]):
            sectors.append("Defense")
        if any(term in text for term in ["bank", "treasury", "bond"]):
            sectors.append("Financials")
        if not sectors:
            sectors.append("Global Equities")
        return list(dict.fromkeys(sectors))


__all__ = ["PoliticalArticle", "PoliticianChecker"]
