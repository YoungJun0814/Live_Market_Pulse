from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class ResolvedStream:
    source_url: str
    stream_url: str
    format_id: str | None = None
    protocol: str | None = None
    is_live: bool = False


def resolve_youtube_stream(url: str, prefer_hls: bool = True) -> ResolvedStream:
    """
    Uses yt-dlp metadata output to resolve a direct live transport URL that can
    be handed to FFmpeg, Smelter, or another ingest pipeline.
    """
    command = [
        "yt-dlp",
        "--no-warnings",
        "--skip-download",
        "-J",
        url,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    formats = payload.get("formats") or []

    chosen = _pick_format(formats, prefer_hls=prefer_hls)
    if chosen is None:
        direct_url = payload.get("url")
        if not direct_url:
            raise RuntimeError("yt-dlp did not return a playable stream URL")
        chosen = {
            "url": direct_url,
            "format_id": payload.get("format_id"),
            "protocol": payload.get("protocol"),
        }

    return ResolvedStream(
        source_url=url,
        stream_url=chosen["url"],
        format_id=chosen.get("format_id"),
        protocol=chosen.get("protocol"),
        is_live=bool(payload.get("is_live") or payload.get("live_status") == "is_live"),
    )


def _pick_format(
    formats: list[dict],
    prefer_hls: bool,
) -> dict | None:
    if prefer_hls:
        for item in formats:
            protocol = (item.get("protocol") or "").lower()
            if "m3u8" in protocol and item.get("url"):
                return item

    for item in formats:
        if item.get("url"):
            return item
    return None


if __name__ == "__main__":
    resolved = resolve_youtube_stream("https://www.youtube.com/watch?v=YDvsBbKfLPA")
    print(resolved)
