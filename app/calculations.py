from __future__ import annotations

from collections import defaultdict

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


def title_probabilities(teams: list[dict]) -> dict[str, float]:
    active = [team for team in teams if team.get("status") == ACTIVE_STATUS]
    manual_total = sum(
        float(team.get("manual_title_probability") or 0)
        for team in active
    )
    unset = [team for team in active if team.get("manual_title_probability") is None]
    remaining = max(0.0, 1.0 - manual_total)
    fallback = remaining / len(unset) if unset else 0.0

    probabilities: dict[str, float] = {}
    for team in teams:
        if team.get("status") != ACTIVE_STATUS:
            probabilities[team["name"]] = 0.0
            continue
        manual = team.get("manual_title_probability")
        probabilities[team["name"]] = float(manual) if manual is not None else fallback
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


def enrich_teams(teams: list[dict], settings: dict) -> list[dict]:
    probabilities = title_probabilities(teams)
    confirmed_total = sum(payout_for_team(team, settings) for team in teams)
    remaining_pool = max(0.0, payout_pool(settings) - confirmed_total)
    enriched = []
    for team in teams:
        copy = dict(team)
        copy["title_probability"] = probabilities[team["name"]]
        copy["confirmed_payout"] = payout_for_team(team, settings)
        copy["possible_payout"] = possible_payout(team, settings)
        copy["expected_value"] = expected_value_for_team(team, settings, probabilities, remaining_pool)
        enriched.append(copy)
    return enriched


def player_summaries(teams: list[dict], settings: dict) -> list[dict]:
    enriched = enrich_teams(teams, settings)
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


def dashboard_payload(state: dict) -> dict:
    teams = enrich_teams(state["teams"], state["settings"])
    return {
        "settings": state["settings"],
        "players": player_summaries(state["teams"], state["settings"]),
        "teams": teams,
        "matches": state["matches"],
        "alerts": state["alerts"],
        "cache": state["cache"],
    }
