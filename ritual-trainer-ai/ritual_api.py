"""Small, polite client for the community-operated Deadlock API."""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.deadlock-api.com"


class DeadlockApiError(RuntimeError):
    pass


class DeadlockClient:
    def __init__(self, api_key: str = ""):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "RitualTrainerAI/0.1 (student-project)", "Accept": "application/json"})
        key = api_key or os.getenv("DEADLOCK_API_KEY", "")
        if key:
            self.session.headers["X-API-Key"] = key
        retry = Retry(total=2, backoff_factor=1.2, status_forcelist=[429, 502, 503, 504],
                      allowed_methods=["GET"], respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get(self, path: str, params: dict | None = None) -> Any:
        try:
            result = self.session.get(BASE_URL + path, params=params, timeout=(6, 25))
            result.raise_for_status()
            return result.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 404:
                raise DeadlockApiError("Match or resource not found. It may not be available in the API yet.") from exc
            if status in (429, 503):
                raise DeadlockApiError("The community API is busy or rate-limiting requests. Try again later or use Demo Mode.") from exc
            raise DeadlockApiError(f"Deadlock API returned HTTP {status}.") from exc
        except (requests.RequestException, ValueError) as exc:
            raise DeadlockApiError(f"Could not retrieve valid API data: {exc}") from exc

    def match(self, match_id: int) -> dict:
        if match_id <= 0:
            raise ValueError("Match ID must be positive.")
        return self.get(f"/v1/matches/{match_id}/metadata")

    def heroes(self) -> dict[int, str]:
        data = self.get("/v1/assets/heroes")
        values = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        return {int(x["id"]): str(x.get("name") or x.get("localized_name") or f"Hero {x['id']}")
                for x in values if isinstance(x, dict) and str(x.get("id", "")).isdigit()}

    def items(self) -> dict[int, str]:
        data = self.get("/v1/assets/items")
        values = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        return {int(x["id"]): str(x.get("name") or f"Item {x['id']}")
                for x in values if isinstance(x, dict) and str(x.get("id", "")).isdigit()}

    def high_rank_curve(self, hero_id: int, min_badge: int, days: int = 30) -> list[dict]:
        return self.get("/v1/analytics/player-performance-curve", {
            "resolution": 0,
            "game_mode": "normal",
            "match_mode": "ranked",
            "hero_ids": str(hero_id),
            "min_average_badge": int(min_badge),
            "min_unix_timestamp": int(time.time()) - 86400 * days,
        })

    def hero_item_meta(self, hero_id: int, min_badge: int, days: int = 30) -> list[dict]:
        return self.get("/v1/analytics/item-stats", {
            "bucket": "no_bucket",
            "game_mode": "normal",
            "match_mode": "ranked",
            "hero_ids": str(hero_id),
            "min_average_badge": int(min_badge),
            "min_matches": 20,
            "min_unix_timestamp": int(time.time()) - 86400 * days,
        })

    def demo_schema(self, match_id: int) -> dict:
        """Check whether a replay is queryable; does not fetch movements or replay events."""
        if not isinstance(match_id, int) or match_id <= 0:
            raise ValueError("A valid match ID is needed for replay inspection.")
        result = self.get("/v1/matches/demo/schema", {"match_id": match_id})
        if not isinstance(result, (dict, list)):
            raise DeadlockApiError("Replay endpoint did not return a recognizable schema.")
        return result

    def recent_patches(self, limit: int = 3) -> list[dict]:
        feed = self.get("/v2/patches")
        if not isinstance(feed, list):
            return []
        cleaned = []
        for entry in feed[: max(1, limit)]:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or entry.get("name") or "Patch update")[:160]
            url = entry.get("url") or entry.get("link")
            published = entry.get("pub_date") or entry.get("published_at") or entry.get("date") or entry.get("created_at")
            content = entry.get("content") or entry.get("description") or ""
            content = re.sub(r"<[^>]*>", " ", str(content))
            content = re.sub(r"\s+", " ", content).strip()[:900]
            cleaned.append({"title": title, "date": str(published)[:80] if published else None,
                            "url": url if isinstance(url, str) and url.startswith("https://") else None,
                            "summary_excerpt": content})
        return cleaned
