from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

from app.seed import now_iso
from app.storage import save_alerts, save_cache, save_matches, save_teams
from app.calculations import apply_tournament_results, match_sort_key, rebuild_alerts

NAME_ALIASES = {
    "bosnia herzegovina": "bosnia and herzegovina",
    "côte divoire": "cote divoire",
    "cote d ivoire": "cote divoire",
    "côte d ivoire": "cote divoire",
    "ivory coast": "cote divoire",
    "usa": "united states",
    "united states of america": "united states",
    "czech republic": "czechia",
    "turkey": "turkiye",
    "türkiye": "turkiye",
    "dr congo": "congo dr",
    "democratic republic of the congo": "congo dr",
    "iran": "iran",
    "ir iran": "iran",
    "korea republic": "south korea",
}


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
        if provider == "manual" and cache.get("message"):
            cache["provider"] = provider
            cache["last_sync"] = cache.get("last_sync") or now_iso()
            save_cache(cache)
            state["cache"] = cache
            return cache
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
        updated = merge_football_data_matches(state, payload.get("matches", []))
        cache = {
            "provider": "football-data",
            "last_sync": now_iso(),
            "message": f"Live sync complete. Updated {updated} matches.",
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


def merge_football_data_matches(state: dict, api_matches: list[dict], persist: bool = True) -> int:
    local_matches = state["matches"]
    updated = 0
    for api_match in api_matches:
        home = canonical_name(team_name(api_match, "homeTeam"))
        away = canonical_name(team_name(api_match, "awayTeam"))
        if not home or not away:
            continue
        local = find_local_match(local_matches, home, away, api_match.get("utcDate"))
        if not local:
            continue

        score = api_match.get("score", {}).get("fullTime", {})
        status = api_match.get("status", "SCHEDULED")
        local["status"] = map_status(status)
        local["date"] = api_match.get("utcDate") or local.get("date") or ""
        local["location"] = match_location(api_match) or local.get("location") or ""
        local["source"] = "football-data"
        local["home_score"] = score.get("home") if score.get("home") is not None else local.get("home_score")
        local["away_score"] = score.get("away") if score.get("away") is not None else local.get("away_score")
        if local["status"] == "finished":
            local["winner"] = infer_winner(local)
        updated += 1

    if updated and persist:
        apply_tournament_results(local_matches, state["teams"])
        save_matches(local_matches)
        save_teams(state["teams"])
        alerts = rebuild_alerts(local_matches, state["teams"], state["settings"])
        save_alerts(alerts)
    return updated


def find_local_match(matches: list[dict], home: str, away: str, utc_date: str | None = None) -> dict | None:
    candidates = []
    for match in matches:
        local_home = canonical_name(match.get("home_team", ""))
        local_away = canonical_name(match.get("away_team", ""))
        if {local_home, local_away} == {home, away}:
            candidates.append(match)
    if not candidates:
        return None
    if len(candidates) == 1 or not utc_date:
        return candidates[0]

    api_time = parse_api_datetime(utc_date)
    if not api_time:
        return candidates[0]
    return min(candidates, key=lambda match: abs(match_sort_key(match) - api_time))


def parse_api_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def team_name(api_match: dict, side: str) -> str | None:
    team = api_match.get(side) or {}
    return team.get("name")


def match_location(api_match: dict) -> str:
    venue = api_match.get("venue")
    if isinstance(venue, str):
        return venue
    if isinstance(venue, dict):
        parts = [venue.get("name"), venue.get("city")]
        return ", ".join(part for part in parts if part)
    return api_match.get("stadium") or ""


def canonical_name(name: str | None) -> str:
    if not name:
        return ""
    value = (
        name.lower()
        .replace("fc", "")
        .replace(".", "")
        .replace("'", "")
        .replace("-", " ")
        .replace("’", "")
    )
    value = " ".join(value.split())
    return NAME_ALIASES.get(value, value)


def map_status(status: str) -> str:
    if status in {"FINISHED", "AWARDED"}:
        return "finished"
    if status in {"IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT"}:
        return "live"
    return "scheduled"


def infer_winner(match: dict) -> str | None:
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None or home_score == away_score:
        return match.get("winner")
    return match["home_team"] if int(home_score) > int(away_score) else match["away_team"]
