from copy import deepcopy

from app.live_feed import merge_football_data_matches
from app.seed import SETTINGS, initial_matches, initial_teams


def test_football_data_merge_updates_matching_result():
    state = {
        "matches": deepcopy(initial_matches()),
        "teams": initial_teams(),
        "settings": SETTINGS,
    }
    api_matches = [
        {
            "utcDate": "2026-06-11T19:00:00Z",
            "status": "FINISHED",
            "homeTeam": {"name": "Mexico"},
            "awayTeam": {"name": "South Africa"},
            "score": {"fullTime": {"home": 2, "away": 1}},
        }
    ]

    updated = merge_football_data_matches(state, api_matches, persist=False)

    assert updated == 1
    match = next(match for match in state["matches"] if match["home_team"] == "Mexico")
    assert match["status"] == "finished"
    assert match["home_score"] == 2
    assert match["away_score"] == 1
    assert match["winner"] == "Mexico"


def test_football_data_merge_handles_common_name_aliases():
    state = {
        "matches": deepcopy(initial_matches()),
        "teams": initial_teams(),
        "settings": SETTINGS,
    }
    api_matches = [
        {
            "utcDate": "2026-06-25T19:00:00Z",
            "status": "FINISHED",
            "homeTeam": {"name": "Korea Republic"},
            "awayTeam": {"name": "Czech Republic"},
            "score": {"fullTime": {"home": 0, "away": 0}},
        }
    ]

    assert merge_football_data_matches(state, api_matches, persist=False) == 1


def test_football_data_merge_skips_null_team_names():
    state = {
        "matches": deepcopy(initial_matches()),
        "teams": initial_teams(),
        "settings": SETTINGS,
    }
    api_matches = [
        {
            "utcDate": "2026-07-04T19:00:00Z",
            "status": "SCHEDULED",
            "homeTeam": {"name": None},
            "awayTeam": {"name": "France"},
            "score": {"fullTime": {"home": None, "away": None}},
        },
        {
            "utcDate": "2026-07-05T19:00:00Z",
            "status": "SCHEDULED",
            "homeTeam": None,
            "awayTeam": {"name": None},
            "score": {"fullTime": {"home": None, "away": None}},
        },
    ]

    assert merge_football_data_matches(state, api_matches, persist=False) == 0
