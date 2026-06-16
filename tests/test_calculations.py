from app.calculations import (
    dashboard_payload,
    enrich_teams,
    generate_match_alert,
    group_standings,
    payout_for_team,
    player_summaries,
    title_probabilities,
)
from app.seed import SETTINGS, initial_cache, initial_matches, initial_teams


def test_player_totals_are_12_teams_each():
    summaries = player_summaries(initial_teams(), SETTINGS)
    assert {summary["name"]: summary["team_count"] for summary in summaries} == {
        "Aman": 12,
        "Chris": 12,
        "Antonie": 12,
        "Neesha": 12,
    }
    assert all(summary["invested"] == 12 for summary in summaries)
    assert sum(summary["expected_value"] for summary in summaries) == 48
    assert len({summary["expected_value"] for summary in summaries}) > 1


def test_payout_ladder_for_terminal_stages():
    team = {"status": "eliminated", "exit_stage": "round_of_16"}
    assert payout_for_team(team, SETTINGS) == 1
    team["exit_stage"] = "quarterfinal"
    assert payout_for_team(team, SETTINGS) == 2
    team["exit_stage"] = "semifinal"
    assert payout_for_team(team, SETTINGS) == 4
    team["exit_stage"] = "runner_up"
    assert payout_for_team(team, SETTINGS) == 8
    team["exit_stage"] = "winner"
    assert payout_for_team(team, SETTINGS) == 16


def test_rank_performance_title_probability_still_sums_to_one():
    teams = initial_teams()
    probabilities = title_probabilities(teams)
    assert round(sum(probabilities.values()), 6) == 1
    assert probabilities["Argentina"] > probabilities["Curacao"]


def test_manual_probability_uses_remaining_pool_for_unset_teams():
    teams = initial_teams()
    teams[0]["manual_title_probability"] = 0.25
    probabilities = title_probabilities(teams)
    assert probabilities[teams[0]["name"]] == 0.25
    assert round(sum(probabilities.values()), 6) == 1


def test_enriched_team_has_money_fields():
    team = enrich_teams(initial_teams(), SETTINGS)[0]
    assert "confirmed_payout" in team
    assert "possible_payout" in team
    assert "expected_value" in team
    assert "flag" in team
    assert "survival_probability" in team
    assert "seed_rank" in team
    assert team["expected_value"] >= 0


def test_finished_match_generates_alert():
    teams = initial_teams()
    for team in teams:
        if team["name"] == "Algeria":
            team["status"] = "eliminated"
            team["exit_stage"] = "group_stage"
    match = {
        "id": "m999",
        "home_team": "Argentina",
        "away_team": "Algeria",
        "home_score": 3,
        "away_score": 1,
        "winner": "Argentina",
        "status": "finished",
    }
    alert = generate_match_alert(match, teams, SETTINGS)
    assert alert is not None
    assert "Argentina 3-1 Algeria" in alert["title"]
    assert "Aman" in alert["body"]


def test_group_standings_include_points_goal_difference_and_position():
    teams = initial_teams()
    matches = initial_matches()
    match = next(item for item in matches if item["home_team"] == "Mexico" and item["away_team"] == "South Africa")
    match["status"] = "finished"
    match["home_score"] = 2
    match["away_score"] = 0
    standings = group_standings(matches, teams)
    mexico = next(row for row in standings if row["team"] == "Mexico")
    south_africa = next(row for row in standings if row["team"] == "South Africa")
    assert mexico["points"] == 3
    assert mexico["gd"] == 2
    assert mexico["position"] == 1
    assert south_africa["lost"] == 1


def test_dashboard_payload_adds_bst_schedule_standings_and_draw():
    payload = dashboard_payload(
        {
            "teams": initial_teams(),
            "matches": initial_matches(),
            "settings": SETTINGS,
            "cache": initial_cache(),
            "alerts": [],
        }
    )
    assert payload["probability_model"]["id"] == "rank_performance"
    assert payload["matches"][0]["display_date"]
    assert payload["matches"] == sorted(payload["matches"], key=lambda item: (item["date"], item["id"]))
    assert len(payload["standings"]) == 48
    assert payload["knockout_draw"][0]["stage"] == "round_of_32"
