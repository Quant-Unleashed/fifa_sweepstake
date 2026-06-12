from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

from app.seed import now_iso
from app.storage import save_cache


def cache_is_fresh(cache: dict, interval_minutes: int) -> bool:
    last_sync = cache.get("last_sync")
    if not last_sync:
        return False
    try:
        synced_at = datetime.fromisoformat(last_sync)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - synced_at < timedelta(minutes=interval_minutes)


async def lazy_sync(state: dict, force: bool = False) -> dict:
    provider = os.getenv("FOOTBALL_PROVIDER", "manual").lower()
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    cache = state["cache"]
    interval = int(state["settings"].get("sync_interval_minutes", 10))

    if not force and cache_is_fresh(cache, interval):
        return cache

    if provider != "football-data" or not api_key:
        cache = {
            "provider": provider,
            "last_sync": now_iso(),
            "message": "Manual mode. Add FOOTBALL_PROVIDER=football-data and FOOTBALL_DATA_API_KEY for live sync.",
            "raw_count": 0,
        }
        save_cache(cache)
        state["cache"] = cache
        return cache

    url = "https://api.football-data.org/v4/competitions/WC/matches"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers={"X-Auth-Token": api_key})
            response.raise_for_status()
            payload = response.json()
        cache = {
            "provider": "football-data",
            "last_sync": now_iso(),
            "message": "Fetched latest World Cup match payload. Manual review may still be needed.",
            "raw_count": len(payload.get("matches", [])),
            "raw_sample": payload.get("matches", [])[:3],
        }
    except Exception as exc:  # pragma: no cover - defensive around provider/network failures
        cache = {
            "provider": "football-data",
            "last_sync": now_iso(),
            "message": f"Live sync failed: {exc}",
            "raw_count": 0,
        }
    save_cache(cache)
    state["cache"] = cache
    return cache
