from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TERMINAL_STAGES = {
    "group_stage",
    "round_of_32",
    "round_of_16",
    "quarterfinal",
    "semifinal",
    "runner_up",
    "winner",
}

ACTIVE_STATUS = "active"
LONDON_TZ = ZoneInfo("Europe/London")
KNOCKOUT_STAGES = ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "third_place", "final"]
STAGE_PROGRESS = {
    "group_stage": 0,
    "round_of_32": 1,
    "round_of_16": 2,
    "quarterfinal": 3,
    "semifinal": 4,
    "third_place": 4,
    "runner_up": 5,
    "final": 5,
    "winner": 6,
}

MODEL_CONFIGS = {
    "rank_performance": {
        "label": "Knockout-adjusted rank/performance model",
        "description": "Uses confirmed team status, knockout draw position, group performance, seed rank, and manual title overrides.",
    },
    # Placeholder for future experimentation: market odds, Elo/SPI imports, Monte Carlo simulations,
    # or provider-driven probabilities can be added behind this registry without changing the API shape.
}

DEFAULT_SEED_RANKS = {
    "Argentina": 1,
    "France": 2,
    "Spain": 3,
    "England": 4,
    "Brazil": 5,
    "Portugal": 6,
    "Netherlands": 7,
    "Belgium": 8,
    "Germany": 9,
    "Uruguay": 10,
    "Croatia": 11,
    "Morocco": 12,
    "Colombia": 13,
    "Mexico": 14,
    "United States": 15,
    "Switzerland": 16,
    "Japan": 17,
    "Senegal": 18,
    "Ecuador": 19,
    "Austria": 20,
    "South Korea": 21,
    "Australia": 22,
    "Iran": 23,
    "Canada": 24,
    "Qatar": 25,
    "Tunisia": 26,
    "Egypt": 27,
    "Norway": 28,
    "Turkiye": 29,
    "Cote d'Ivoire": 30,
    "Ghana": 31,
    "Scotland": 32,
    "Sweden": 33,
    "Paraguay": 34,
    "Saudi Arabia": 35,
    "Algeria": 36,
    "Panama": 37,
    "Czechia": 38,
    "South Africa": 39,
    "Uzbekistan": 40,
    "New Zealand": 41,
    "Jordan": 42,
    "Iraq": 43,
    "Haiti": 44,
    "Cape Verde": 45,
    "Congo DR": 46,
    "Bosnia and Herzegovina": 47,
    "Curacao": 48,
}

TEAM_FLAGS = {
    "Algeria": "🇩🇿",
    "Argentina": "🇦🇷",
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Belgium": "🇧🇪",
    "Bosnia and Herzegovina": "🇧🇦",
    "Brazil": "🇧🇷",
    "Canada": "🇨🇦",
    "Cape Verde": "🇨🇻",
    "Colombia": "🇨🇴",
    "Congo DR": "🇨🇩",
    "Cote d'Ivoire": "🇨🇮",
    "Croatia": "🇭🇷",
    "Curacao": "🇨🇼",
    "Czechia": "🇨🇿",
    "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬",
    "England": "🏴",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Ghana": "🇬🇭",
    "Haiti": "🇭🇹",
    "Iran": "🇮🇷",
    "Iraq": "🇮🇶",
    "Japan": "🇯🇵",
    "Jordan": "🇯🇴",
    "Mexico": "🇲🇽",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿",
    "Norway": "🇳🇴",
    "Panama": "🇵🇦",
    "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹",
    "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦",
    "Scotland": "🏴",
    "Senegal": "🇸🇳",
    "South Africa": "🇿🇦",
    "South Korea": "🇰🇷",
    "Spain": "🇪🇸",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Tunisia": "🇹🇳",
    "Turkiye": "🇹🇷",
    "United States": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
}


def money(value: float) -> float:
    return round(float(value), 2)


def payout_for_team(team: dict, settings: dict) -> float:
    if team.get("status") != "eliminated" and team.get("exit_stage") != "winner":
        return 0.0
    stage = team.get("exit_stage")
    return money(settings["payouts"].get(stage, 0))


def possible_payout(team: dict, settings: dict) -> float:
    if team.get("status") == "eliminated":
        return payout_for_team(team, settings)
    return money(settings["payouts"]["winner"])


def flag_for(team_name: str | None) -> str:
    if not team_name:
        return ""
    return TEAM_FLAGS.get(team_name, "")


def title_probabilities(
    teams: list[dict],
    standings: list[dict] | None = None,
    matches: list[dict] | None = None,
) -> dict[str, float]:
    active = [team for team in teams if team.get("status") == ACTIVE_STATUS]
    manual_total = sum(
        float(team.get("manual_title_probability") or 0)
        for team in active
    )
    unset = [team for team in active if team.get("manual_title_probability") is None]
    remaining = max(0.0, 1.0 - manual_total)
    model_weights = rank_performance_weights(unset, standings or [], matches or [])
    total_weight = sum(model_weights.values())

    probabilities: dict[str, float] = {}
    for team in teams:
        if team.get("status") != ACTIVE_STATUS:
            probabilities[team["name"]] = 0.0
            continue
        manual = team.get("manual_title_probability")
        if manual is not None:
            probabilities[team["name"]] = float(manual)
        elif total_weight:
            probabilities[team["name"]] = remaining * model_weights.get(team["name"], 0.0) / total_weight
        else:
            probabilities[team["name"]] = remaining / len(unset) if unset else 0.0
    return probabilities


def payout_pool(settings: dict) -> float:
    payouts = settings["payouts"]
    return money(
        8 * payouts["round_of_16"]
        + 4 * payouts["quarterfinal"]
        + 2 * payouts["semifinal"]
        + payouts["runner_up"]
        + payouts["winner"]
    )


def expected_value_for_team(
    team: dict,
    settings: dict,
    probabilities: dict[str, float],
    remaining_pool: float,
) -> float:
    confirmed = payout_for_team(team, settings)
    if team.get("status") != ACTIVE_STATUS:
        return confirmed
    return money(probabilities.get(team["name"], 0.0) * remaining_pool)


def enrich_teams(
    teams: list[dict],
    settings: dict,
    standings: list[dict] | None = None,
    matches: list[dict] | None = None,
) -> list[dict]:
    probabilities = title_probabilities(teams, standings, matches)
    survival = survival_probabilities(teams, standings or [], matches or [])
    confirmed_total = sum(payout_for_team(team, settings) for team in teams)
    remaining_pool = max(0.0, payout_pool(settings) - confirmed_total)
    enriched = []
    for team in teams:
        copy = dict(team)
        copy["title_probability"] = probabilities[team["name"]]
        copy["survival_probability"] = survival.get(team["name"], 0.0)
        copy["seed_rank"] = DEFAULT_SEED_RANKS.get(team["name"], 48)
        copy["confirmed_payout"] = payout_for_team(team, settings)
        copy["possible_payout"] = possible_payout(team, settings)
        copy["expected_value"] = expected_value_for_team(team, settings, probabilities, remaining_pool)
        copy["flag"] = flag_for(team["name"])
        enriched.append(copy)
    return enriched


def player_summaries(
    teams: list[dict],
    settings: dict,
    standings: list[dict] | None = None,
    matches: list[dict] | None = None,
) -> list[dict]:
    enriched = enrich_teams(teams, settings, standings, matches)
    by_owner: dict[str, list[dict]] = defaultdict(list)
    for team in enriched:
        by_owner[team["owner"]].append(team)

    summaries = []
    for owner in ["Aman", "Chris", "Antonie", "Neesha"]:
        owned = sorted(by_owner[owner], key=lambda team: team["name"])
        active = [team for team in owned if team["status"] == ACTIVE_STATUS]
        summaries.append(
            {
                "name": owner,
                "team_count": len(owned),
                "invested": money(len(owned) * settings["stake_per_team"]),
                "confirmed_winnings": money(sum(team["confirmed_payout"] for team in owned)),
                "expected_value": money(sum(team["expected_value"] for team in owned)),
                "actual_profit": money(sum(team["confirmed_payout"] for team in owned) - len(owned) * settings["stake_per_team"]),
                "ev_profit": money(sum(team["expected_value"] for team in owned) - len(owned) * settings["stake_per_team"]),
                "active_count": len(active),
                "eliminated_count": len(owned) - len(active),
                "teams": owned,
            }
        )
    return summaries


def generate_match_alert(match: dict, teams: list[dict], settings: dict) -> dict | None:
    if match.get("status") != "finished":
        return None
    team_by_name = {team["name"]: team for team in teams}
    names = [match.get("home_team"), match.get("away_team")]
    involved = [team_by_name[name] for name in names if name in team_by_name]
    if not involved:
        return None

    scores = score_text(match)
    bullets = []
    for team in involved:
        owner = team["owner"]
        if team.get("status") == "eliminated":
            payout = payout_for_team(team, settings)
            bullets.append(f"{owner}: {team['name']} eliminated, confirmed payout £{payout:g}.")
        elif match.get("winner") == team["name"]:
            bullets.append(f"{owner}: {team['name']} won and stays alive.")
        else:
            bullets.append(f"{owner}: {team['name']} is still marked active.")

    return {
        "id": f"alert-{match['id']}",
        "match_id": match["id"],
        "title": scores,
        "body": " ".join(bullets),
        "whatsapp_text": f"{scores}\n\nImpact:\n" + "\n".join(f"- {item}" for item in bullets),
    }


def score_text(match: dict) -> str:
    home = match.get("home_team", "TBD")
    away = match.get("away_team", "TBD")
    if match.get("home_score") is None or match.get("away_score") is None:
        return f"{home} vs {away}"
    return f"{home} {match['home_score']}-{match['away_score']} {away}"


def rebuild_alerts(matches: list[dict], teams: list[dict], settings: dict) -> list[dict]:
    alerts = []
    for match in matches:
        alert = generate_match_alert(match, teams, settings)
        if alert:
            alerts.append(alert)
    return list(reversed(alerts))


def group_standings(matches: list[dict], teams: list[dict]) -> list[dict]:
    # FIFA group ordering starts with points, goal difference, then goals scored.
    # Later tie-breakers such as head-to-head and fair-play are not available in v1 data,
    # so seed rank and original group position are only display-stable fallbacks.
    team_lookup = {team["name"]: team for team in teams}
    rows = {
        team["name"]: {
            "team": team["name"],
            "flag": flag_for(team["name"]),
            "owner": team["owner"],
            "group": team["group"],
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "gf": 0,
            "ga": 0,
            "gd": 0,
            "points": 0,
            "seed_rank": DEFAULT_SEED_RANKS.get(team["name"], 48),
        }
        for team in teams
    }
    for match in matches:
        if match.get("stage") != "group_stage" or match.get("status") != "finished":
            continue
        home = match.get("home_team")
        away = match.get("away_team")
        if home not in rows or away not in rows:
            continue
        home_score = match.get("home_score")
        away_score = match.get("away_score")
        if home_score is None or away_score is None:
            continue
        home_score = int(home_score)
        away_score = int(away_score)
        apply_group_result(rows[home], home_score, away_score)
        apply_group_result(rows[away], away_score, home_score)

    for row in rows.values():
        row["gd"] = row["gf"] - row["ga"]
        row["group_position"] = team_lookup[row["team"]].get("group_position", 99)

    ordered = []
    for group in sorted({team["group"] for team in teams}):
        group_rows = [row for row in rows.values() if row["group"] == group]
        group_rows.sort(
            key=lambda row: (
                -row["points"],
                -row["gd"],
                -row["gf"],
                row["seed_rank"],
                row["group_position"],
            )
        )
        for position, row in enumerate(group_rows, start=1):
            row["position"] = position
            row["qualification"] = qualification_label(position)
        ordered.extend(group_rows)
    return ordered


def qualification_label(position: int) -> str:
    if position <= 2:
        return "Advancing"
    if position == 3:
        return "Third-place race"
    return "At risk"


def apply_group_result(row: dict, goals_for: int, goals_against: int) -> None:
    row["played"] += 1
    row["gf"] += goals_for
    row["ga"] += goals_against
    if goals_for > goals_against:
        row["won"] += 1
        row["points"] += 3
    elif goals_for == goals_against:
        row["drawn"] += 1
        row["points"] += 1
    else:
        row["lost"] += 1


def survival_probabilities(teams: list[dict], standings: list[dict], matches: list[dict] | None = None) -> dict[str, float]:
    standings_by_team = {row["team"]: row for row in standings}
    knockout_team_names = teams_in_knockout(matches or [])
    probabilities = {}
    for team in teams:
        if team.get("status") != ACTIVE_STATUS:
            probabilities[team["name"]] = 0.0
            continue
        if team["name"] in knockout_team_names:
            probabilities[team["name"]] = 1.0
            continue
        row = standings_by_team.get(team["name"], {})
        probabilities[team["name"]] = survival_probability(row)
    return probabilities


def survival_probability(row: dict) -> float:
    if not row:
        return 0.55
    played = int(row.get("played", 0))
    if played >= 3:
        return 1.0 if int(row.get("position", 99)) <= 2 else 0.18
    score = (
        0.22
        + 0.11 * int(row.get("points", 0))
        + 0.055 * int(row.get("gd", 0))
        + 0.025 * int(row.get("gf", 0))
        + max(0, 49 - int(row.get("seed_rank", 48))) / 220
        + max(0, 4 - int(row.get("position", 4))) * 0.08
    )
    return max(0.04, min(0.96, round(score, 4)))


def rank_performance_weights(teams: list[dict], standings: list[dict], matches: list[dict] | None = None) -> dict[str, float]:
    standings_by_team = {row["team"]: row for row in standings}
    stage_by_team = active_stage_by_team(matches or [])
    weights = {}
    for team in teams:
        row = standings_by_team.get(team["name"], {})
        seed_rank = DEFAULT_SEED_RANKS.get(team["name"], 48)
        survival = survival_probability(row)
        stage = stage_by_team.get(team["name"])
        if stage:
            survival = 1.0
        seed_strength = max(1, 55 - seed_rank) / 55
        stage_boost = 1 + STAGE_PROGRESS.get(stage or "group_stage", 0) * 0.18
        performance = (
            1
            + int(row.get("points", 0)) * 0.32
            + int(row.get("gd", 0)) * 0.12
            + int(row.get("gf", 0)) * 0.05
        )
        weights[team["name"]] = max(0.05, seed_strength * survival * stage_boost * max(0.2, performance))
    return weights


def teams_in_knockout(matches: list[dict]) -> set[str]:
    names = set()
    for match in matches:
        if match.get("stage") not in KNOCKOUT_STAGES:
            continue
        for side in ("home_team", "away_team"):
            name = match.get(side)
            if is_real_team_name(name):
                names.add(name)
    return names


def active_stage_by_team(matches: list[dict]) -> dict[str, str]:
    stages: dict[str, str] = {}
    for match in matches:
        stage = match.get("stage")
        if stage not in KNOCKOUT_STAGES:
            continue
        for side in ("home_team", "away_team"):
            name = match.get(side)
            if not is_real_team_name(name):
                continue
            current = stages.get(name)
            if current is None or STAGE_PROGRESS.get(stage, 0) > STAGE_PROGRESS.get(current, 0):
                stages[name] = stage
    return stages


def is_real_team_name(name: str | None) -> bool:
    if not name:
        return False
    return " team " not in name.lower()


def chronological_matches(matches: list[dict]) -> list[dict]:
    return sorted(matches, key=lambda match: (match_sort_key(match), match.get("id", "")))


def match_sort_key(match: dict) -> datetime:
    value = match.get("date") or "9999-12-31"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.fromisoformat(f"{value}T12:00:00+00:00")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_bst(value: str | None) -> str:
    if not value:
        return ""
    has_time = "T" in value
    parsed = match_sort_key({"date": value})
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    local = parsed.astimezone(LONDON_TZ)
    if not has_time:
        return local.strftime("%d %b %Y, time TBC BST")
    return local.strftime("%d %b %Y, %H:%M BST")


def needs_result(match: dict) -> bool:
    if match.get("status") in {"finished", "live"}:
        return False
    if match.get("home_score") is not None and match.get("away_score") is not None:
        return False
    parsed = match_sort_key(match)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed < datetime.now(timezone.utc)


def knockout_draw(matches: list[dict]) -> list[dict]:
    rounds = []
    labels = ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "third_place", "final"]
    for stage in labels:
        stage_matches = [match for match in chronological_matches(matches) if match.get("stage") == stage]
        if stage_matches:
            rounds.append(
                {
                    "stage": stage,
                    "label": stage_label(stage),
                    "matches": [
                        {
                            **match,
                            "display_date": format_bst(match.get("date")),
                            "needs_result": needs_result(match),
                            "home_flag": flag_for(match.get("home_team")),
                            "away_flag": flag_for(match.get("away_team")),
                            "home_probability": match_probability(match, "home"),
                            "away_probability": match_probability(match, "away"),
                        }
                        for match in stage_matches
                    ],
                }
            )
    return rounds


def stage_label(stage: str) -> str:
    return stage.replace("_", " ").title()


def match_probability(match: dict, side: str) -> float:
    stored = match.get(f"{side}_probability")
    other_side = "away" if side == "home" else "home"
    other_stored = match.get(f"{other_side}_probability")
    if stored is not None and other_stored is not None and (stored, other_stored) != (0.5, 0.5):
        return float(stored)

    home = match.get("home_team")
    away = match.get("away_team")
    if match.get("stage") not in KNOCKOUT_STAGES or not is_real_team_name(home) or not is_real_team_name(away):
        return float(stored if stored is not None else 0.5)

    home_weight = team_strength(home)
    away_weight = team_strength(away)
    total = home_weight + away_weight
    if not total:
        return 0.5
    home_probability = max(0.08, min(0.92, home_weight / total))
    return round(home_probability if side == "home" else 1 - home_probability, 4)


def team_strength(team_name: str) -> float:
    seed_rank = DEFAULT_SEED_RANKS.get(team_name, 48)
    return max(1, 55 - seed_rank)


def dashboard_payload(state: dict) -> dict:
    standings = group_standings(state["matches"], state["teams"])
    teams = enrich_teams(state["teams"], state["settings"], standings, state["matches"])
    team_flags = {team["name"]: team["flag"] for team in teams}
    return {
        "settings": state["settings"],
        "players": player_summaries(state["teams"], state["settings"], standings, state["matches"]),
        "teams": teams,
        "matches": [
            {
                **match,
                "display_date": format_bst(match.get("date")),
                "needs_result": needs_result(match),
                "home_flag": flag_for(match.get("home_team")),
                "away_flag": flag_for(match.get("away_team")),
                "home_probability": match_probability(match, "home"),
                "away_probability": match_probability(match, "away"),
            }
            for match in chronological_matches(state["matches"])
        ],
        "standings": standings,
        "knockout_draw": knockout_draw(state["matches"]),
        "probability_model": MODEL_CONFIGS["rank_performance"] | {"id": "rank_performance"},
        "alerts": state["alerts"],
        "cache": state["cache"],
        "team_flags": team_flags,
    }
