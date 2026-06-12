from app.calculations import (
    enrich_teams,
    generate_match_alert,
    payout_for_team,
    player_summaries,
    title_probabilities,
)
from app.seed import SETTINGS, initial_teams


def test_player_totals_are_12_teams_each():
    summaries = player_summaries(initial_teams(), SETTINGS)
    assert {summary["name"]: summary["team_count"] for summary in summaries} == {
        "Aman": 12,
        "Chris": 12,
        "Antonie": 12,
        "Neesha": 12,
    }
    assert all(summary["invested"] == 12 for summary in summaries)
    assert all(summary["expected_value"] == 12 for summary in summaries)


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


def test_equal_title_probability_defaults_to_active_teams():
    teams = initial_teams()
    probabilities = title_probabilities(teams)
    assert round(sum(probabilities.values()), 6) == 1
    assert probabilities["Argentina"] == probabilities["Brazil"]


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
    assert team["expected_value"] == 1


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
