from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.calculations import apply_tournament_results, dashboard_payload, rebuild_alerts
from app.live_feed import lazy_sync
from app.storage import (
    MATCHES_FILE,
    TEAMS_FILE,
    ensure_data_files,
    load_state,
    save_alerts,
    save_matches,
    save_teams,
)

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_data_files()
    yield


app = FastAPI(title="Aman's FIFA Sweepstake", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
async def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/dashboard")
async def dashboard() -> dict:
    state = load_state()
    await lazy_sync(state)
    state = load_state()
    reconcile_state(state)
    return dashboard_payload(load_state())


@app.post("/api/admin/sync")
async def sync(x_admin_password: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_password)
    state = load_state()
    cache = await lazy_sync(state, force=True)
    return {"ok": True, "cache": cache}


@app.post("/api/admin/matches/{match_id}")
async def update_match(
    match_id: str,
    payload: dict[str, Any],
    x_admin_password: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_password)
    state = load_state()
    matches = state["matches"]
    match = find_by_id(matches, match_id, "match")

    allowed = {
        "home_score",
        "away_score",
        "status",
        "winner",
        "home_probability",
        "away_probability",
        "home_team",
        "away_team",
        "date",
        "stage",
        "label",
    }
    for key, value in payload.items():
        if key in allowed:
            match[key] = normalize_blank(value)

    if match.get("status") == "finished" and not match.get("winner"):
        match["winner"] = infer_winner(match)

    apply_tournament_results(matches, state["teams"])
    save_matches(matches)
    save_teams(state["teams"])
    refresh_alerts()
    return {"ok": True, "match": match}


@app.post("/api/admin/teams/{team_id}")
async def update_team(
    team_id: str,
    payload: dict[str, Any],
    x_admin_password: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_password)
    state = load_state()
    teams = state["teams"]
    team = find_by_id(teams, team_id, "team")

    allowed = {"status", "exit_stage", "manual_title_probability", "notes"}
    for key, value in payload.items():
        if key in allowed:
            team[key] = normalize_probability(value) if key == "manual_title_probability" else normalize_blank(value)
    if team.get("status") == "active":
        team["exit_stage"] = None

    save_teams(teams)
    refresh_alerts()
    return {"ok": True, "team": team}


@app.get("/api/admin/export")
async def export_data(x_admin_password: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_password)
    return load_state()


@app.post("/api/admin/import")
async def import_data(
    payload: dict[str, Any],
    x_admin_password: str | None = Header(default=None),
) -> dict:
    require_admin(x_admin_password)
    if "teams" not in payload or "matches" not in payload:
        raise HTTPException(status_code=400, detail="Import must include teams and matches.")
    apply_tournament_results(payload["matches"], payload["teams"])
    save_teams(payload["teams"])
    save_matches(payload["matches"])
    refresh_alerts()
    return {"ok": True}


def require_admin(password: str | None) -> None:
    expected = os.getenv("ADMIN_PASSWORD", "change-me")
    if not password or password != expected:
        raise HTTPException(status_code=401, detail="Admin password required.")


def find_by_id(items: list[dict], item_id: str, label: str) -> dict:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"Unknown {label}: {item_id}")


def normalize_blank(value: Any) -> Any:
    return None if value == "" else value


def normalize_probability(value: Any) -> float | None:
    if value in ("", None):
        return None
    number = float(value)
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def infer_winner(match: dict) -> str | None:
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None or home_score == away_score:
        return None
    return match["home_team"] if int(home_score) > int(away_score) else match["away_team"]


def refresh_alerts() -> None:
    state = load_state()
    alerts = rebuild_alerts(state["matches"], state["teams"], state["settings"])
    save_alerts(alerts)


def reconcile_state(state: dict) -> None:
    if apply_tournament_results(state["matches"], state["teams"]):
        save_matches(state["matches"])
        save_teams(state["teams"])
        alerts = rebuild_alerts(state["matches"], state["teams"], state["settings"])
        save_alerts(alerts)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
