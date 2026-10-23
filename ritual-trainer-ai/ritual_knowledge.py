"""Compact, auditable current-game context for the selected Deadlock hero."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

ASSETS_BASE = "https://api.deadlock-api.com"


class KnowledgeUnavailable(RuntimeError):
    pass


class AssetClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "RitualTrainerAI/0.6.1 (student project)"})

    def get(self, path: str):
        try:
            response = self.session.get(ASSETS_BASE + path, timeout=(6, 24))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as exc:
            raise KnowledgeUnavailable(
                "Could not connect to the Deadlock community API (api.deadlock-api.com). "
                "Check that your internet/DNS is working and retry. You can still generate "
                "statistics-only coaching while game definitions are unavailable. "
                f"Technical detail: {exc}"
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            raise KnowledgeUnavailable(f"Could not retrieve valid current Deadlock hero/item definitions: {exc}") from exc

    def hero(self, hero_id: int):
        if hero_id <= 0:
            raise ValueError("Hero ID must be positive")
        return self.get(f"/v1/assets/heroes/{hero_id}")

    def all_items(self):
        return self.get("/v1/assets/items")


def _short(value: Any, limit: int = 300) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _item_list(items: Any) -> list[dict]:
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    if isinstance(items, dict):
        return [x for x in items.values() if isinstance(x, dict)]
    return []


def _id(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("id", ""))


def _definition(item: dict) -> dict:
    desc = _short(item.get("description"), 400)
    if not desc and isinstance(item.get("tooltip_details"), dict):
        desc = _short(item["tooltip_details"].get("info_section"), 250)
    out = {
        "name": _short(item.get("name"), 100),
        "type": _short(item.get("type"), 40),
        "description": desc,
    }
    if isinstance(item.get("cost"), (int, float)) and not isinstance(item.get("cost"), bool):
        out["cost"] = item["cost"]
    # Avoid injecting every raw attribute: an evidence reference, not the complete game database.
    return out


def build_knowledge_pack(hero: dict, all_items: Any, purchases: list[dict], *, fetched_at: str | None = None) -> dict:
    """Build a small hero- and purchase-specific reference, omitting unknown mechanics."""
    if not isinstance(hero, dict) or not hero.get("name") or not isinstance(hero.get("id"), int):
        raise ValueError("A valid hero definition is needed")
    description = hero.get("description") if isinstance(hero.get("description"), dict) else {}
    inventory = _item_list(all_items)
    by_id = {_id(item): item for item in inventory if _id(item)}
    by_class = {str(item["class_name"]): item for item in inventory if item.get("class_name")}
    bound = hero.get("items") if isinstance(hero.get("items"), dict) else {}
    hero_kit = []
    seen = set()
    for slot, asset_ref in bound.items():
        if not any(token in str(slot).lower() for token in ("ability", "signature", "innate", "ultimate")):
            continue
        entry = by_id.get(str(asset_ref)) or by_class.get(str(asset_ref))
        if entry:
            identity = _id(entry) or str(asset_ref)
            if identity not in seen:
                hero_kit.append({"slot": str(slot)[:65], **_definition(entry)})
                seen.add(identity)
    bought = []
    for purchase in (purchases or [])[:40]:
        if not isinstance(purchase, dict):
            continue
        entry = by_id.get(str(purchase.get("item_id")))
        if not entry:
            continue
        if len(bought) >= 16:
            break
        bought.append({**_definition(entry), "purchase_minute": purchase.get("minute")})
    return {
        "available": True,
        "hero": {"id": hero["id"], "name": _short(hero["name"], 100),
                 "official_role_description": _short(description.get("role"), 300),
                 "official_playstyle_description": _short(description.get("playstyle"), 700)},
        "hero_abilities": hero_kit[:10],
        "purchased_item_definitions": bought,
        "source": "Deadlock API /v1/assets (game-file-derived definitions)",
        "hero_url": f"{ASSETS_BASE}/v1/assets/heroes/{hero['id']}",
        "item_url": f"{ASSETS_BASE}/v1/assets/items",
        "retrieved_utc": fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limits": [
            "Hero abilities not linked by this asset snapshot are omitted; absence is not proof an ability does not exist.",
            "Item properties and mechanics may change after retrieval; fetch fresh data after a patch.",
            "Abilities and item descriptions do not reveal how the player used them during this match.",
        ],
    }
