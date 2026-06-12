from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.seed import SETTINGS, initial_cache, initial_matches, initial_teams

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEAMS_FILE = DATA_DIR / "teams.json"
MATCHES_FILE = DATA_DIR / "matches.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
CACHE_FILE = DATA_DIR / "cache.json"
ALERTS_FILE = DATA_DIR / "alerts.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    defaults = {
        TEAMS_FILE: initial_teams(),
        MATCHES_FILE: initial_matches(),
        SETTINGS_FILE: SETTINGS,
        CACHE_FILE: initial_cache(),
        ALERTS_FILE: [],
    }
    for path, value in defaults.items():
        if not path.exists():
            save_json(path, value)


def load_json(path: Path) -> Any:
    ensure_data_files_without_recursion()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def ensure_data_files_without_recursion() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not TEAMS_FILE.exists():
        save_json(TEAMS_FILE, initial_teams())
    if not MATCHES_FILE.exists():
        save_json(MATCHES_FILE, initial_matches())
    if not SETTINGS_FILE.exists():
        save_json(SETTINGS_FILE, SETTINGS)
    if not CACHE_FILE.exists():
        save_json(CACHE_FILE, initial_cache())
    if not ALERTS_FILE.exists():
        save_json(ALERTS_FILE, [])


def load_state() -> dict:
    ensure_data_files()
    return {
        "teams": load_json(TEAMS_FILE),
        "matches": load_json(MATCHES_FILE),
        "settings": load_json(SETTINGS_FILE),
        "cache": load_json(CACHE_FILE),
        "alerts": load_json(ALERTS_FILE),
    }


def save_teams(teams: list[dict]) -> None:
    save_json(TEAMS_FILE, teams)


def save_matches(matches: list[dict]) -> None:
    save_json(MATCHES_FILE, matches)


def save_cache(cache: dict) -> None:
    save_json(CACHE_FILE, cache)


def save_alerts(alerts: list[dict]) -> None:
    save_json(ALERTS_FILE, alerts[:50])
