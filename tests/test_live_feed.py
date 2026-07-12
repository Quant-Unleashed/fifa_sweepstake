from copy import deepcopy

from app.calculations import apply_tournament_results
from app.live_feed import find_local_match, merge_football_data_matches
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
            "venue": {"name": "Estadio Azteca", "city": "Mexico City"},
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
    assert match["date"] == "2026-06-11T19:00:00Z"
    assert match["location"] == "Estadio Azteca, Mexico City"


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


def test_find_local_match_prefers_closest_kickoff_for_duplicate_teams():
    matches = [
        {
            "id": "early",
            "date": "2026-07-01T00:00:00Z",
            "home_team": "United States",
            "away_team": "Bosnia and Herzegovina",
        },
        {
            "id": "midnight-uk",
            "date": "2026-07-02T00:00:00Z",
            "home_team": "Bosnia and Herzegovina",
            "away_team": "United States",
        },
    ]

    match = find_local_match(matches, "united states", "bosnia and herzegovina", "2026-07-02T00:00:00Z")

    assert match["id"] == "midnight-uk"


def test_round_of_32_winners_advance_to_confirmed_round_of_16_bracket():
    matches = initial_matches()
    teams = initial_teams()

    assert apply_tournament_results(matches, teams) is True

    round_of_16 = {match["id"]: match for match in matches if match["stage"] == "round_of_16"}
    assert (round_of_16["m089"]["home_team"], round_of_16["m089"]["away_team"]) == ("Canada", "Morocco")
    assert (round_of_16["m090"]["home_team"], round_of_16["m090"]["away_team"]) == ("Paraguay", "France")
    assert (round_of_16["m096"]["home_team"], round_of_16["m096"]["away_team"]) == ("Switzerland", "Colombia")


def test_seed_results_loaded_through_completed_july_11_quarterfinals():
    matches = {match["id"]: match for match in initial_matches()}

    assert matches["m082"]["home_score"] == 2
    assert matches["m082"]["away_score"] == 0
    assert matches["m088"]["winner"] == "Colombia"
    assert matches["m089"]["home_score"] == 0
    assert matches["m089"]["away_score"] == 3
    assert matches["m096"]["winner"] == "Switzerland"
    assert matches["m097"]["date"] == "2026-07-09T20:00:00Z"
    assert matches["m097"]["winner"] == "France"
    assert matches["m098"]["winner"] == "Spain"
    assert matches["m099"]["winner"] == "England"
    assert matches["m100"]["status"] == "scheduled"
    assert matches["m101"]["date"] == "2026-07-14T19:00:00Z"
    assert matches["m102"]["date"] == "2026-07-15T19:00:00Z"
    assert matches["m104"]["date"] == "2026-07-19T19:00:00Z"
