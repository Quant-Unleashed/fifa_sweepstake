from __future__ import annotations

from datetime import datetime, timezone

PLAYERS = {
    "Aman": [
        "Argentina",
        "Portugal",
        "Colombia",
        "Mexico",
        "Turkiye",
        "Australia",
        "Algeria",
        "Sweden",
        "Czechia",
        "South Africa",
        "Saudi Arabia",
        "New Zealand",
    ],
    "Chris": [
        "England",
        "Brazil",
        "Belgium",
        "Uruguay",
        "Switzerland",
        "Ecuador",
        "Norway",
        "Panama",
        "Congo DR",
        "Uzbekistan",
        "Cape Verde",
        "Haiti",
    ],
    "Antonie": [
        "France",
        "Morocco",
        "Germany",
        "Senegal",
        "Japan",
        "Austria",
        "Canada",
        "Tunisia",
        "Qatar",
        "Bosnia and Herzegovina",
        "Ghana",
        "Paraguay",
    ],
    "Neesha": [
        "Spain",
        "Netherlands",
        "Croatia",
        "United States",
        "Iran",
        "South Korea",
        "Egypt",
        "Cote d'Ivoire",
        "Scotland",
        "Iraq",
        "Jordan",
        "Curacao",
    ],
}

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Cote d'Ivoire", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "Congo DR"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

MATCH_DATES = {
    "A": ["2026-06-11", "2026-06-18", "2026-06-24"],
    "B": ["2026-06-12", "2026-06-18", "2026-06-24"],
    "C": ["2026-06-13", "2026-06-19", "2026-06-24"],
    "D": ["2026-06-12", "2026-06-19", "2026-06-25"],
    "E": ["2026-06-14", "2026-06-20", "2026-06-25"],
    "F": ["2026-06-14", "2026-06-20", "2026-06-25"],
    "G": ["2026-06-15", "2026-06-21", "2026-06-26"],
    "H": ["2026-06-15", "2026-06-21", "2026-06-26"],
    "I": ["2026-06-16", "2026-06-22", "2026-06-27"],
    "J": ["2026-06-16", "2026-06-22", "2026-06-27"],
    "K": ["2026-06-17", "2026-06-23", "2026-06-27"],
    "L": ["2026-06-17", "2026-06-23", "2026-06-27"],
}

SETTINGS = {
    "title": "Welcome to Aman's FIFA Sweepstake",
    "stake_per_team": 1,
    "currency": "GBP",
    "sync_interval_minutes": 10,
    "payouts": {
        "group_stage": 0,
        "round_of_32": 0,
        "round_of_16": 1,
        "quarterfinal": 2,
        "semifinal": 4,
        "runner_up": 8,
        "winner": 16,
    },
}

KNOCKOUT_PLACEHOLDERS = [
    ("round_of_16", "Round of 16", "2026-07-04", 8),
    ("quarterfinal", "Quarterfinal", "2026-07-09", 4),
    ("semifinal", "Semifinal", "2026-07-14", 2),
    ("third_place", "Third-place match", "2026-07-18", 1),
    ("final", "Final", "2026-07-19", 1),
]

ROUND_OF_32_FIXTURES = [
    ("2026-06-28T19:00:00Z", "South Africa", "Canada", "Los Angeles Stadium"),
    ("2026-06-29T17:00:00Z", "Brazil", "Japan", "Houston Stadium"),
    ("2026-06-29T20:30:00Z", "Germany", "Paraguay", "Boston Stadium"),
    ("2026-06-30T01:00:00Z", "Netherlands", "Morocco", "Monterrey Stadium"),
    ("2026-06-30T17:00:00Z", "Cote d'Ivoire", "Norway", "Dallas Stadium"),
    ("2026-06-30T21:00:00Z", "France", "Sweden", "New York/New Jersey Stadium"),
    ("2026-07-01T01:00:00Z", "Mexico", "Ecuador", "Mexico City Stadium"),
    ("2026-07-01T16:00:00Z", "England", "Congo DR", "Atlanta Stadium"),
    ("2026-07-01T20:00:00Z", "Belgium", "Senegal", "Seattle Stadium"),
    ("2026-07-02T00:00:00Z", "United States", "Bosnia and Herzegovina", "San Francisco Bay Stadium"),
    ("2026-07-02T19:00:00Z", "Spain", "Austria", "Los Angeles Stadium"),
    ("2026-07-02T23:00:00Z", "Portugal", "Croatia", "Toronto Stadium"),
    ("2026-07-03T03:00:00Z", "Switzerland", "Algeria", "BC Place Vancouver"),
    ("2026-07-03T18:00:00Z", "Australia", "Egypt", "Dallas Stadium"),
    ("2026-07-03T22:00:00Z", "Argentina", "Cape Verde", "Miami Stadium"),
    ("2026-07-04T01:30:00Z", "Colombia", "Ghana", "Kansas City Stadium"),
]


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("'", "")
        .replace(" ", "-")
        .replace(".", "")
    )


def owner_for(team_name: str) -> str:
    for player, teams in PLAYERS.items():
        if team_name in teams:
            return player
    raise ValueError(f"No owner configured for {team_name}")


def initial_teams() -> list[dict]:
    active_teams = {team for fixture in ROUND_OF_32_FIXTURES for team in fixture[1:3]}
    teams = []
    for group, names in GROUPS.items():
        for position, name in enumerate(names, start=1):
            is_active = name in active_teams
            teams.append(
                {
                    "id": slugify(name),
                    "name": name,
                    "owner": owner_for(name),
                    "group": group,
                    "group_position": position,
                    "status": "active" if is_active else "eliminated",
                    "exit_stage": None if is_active else "group_stage",
                    "manual_title_probability": None,
                    "notes": "" if is_active else "Eliminated before the Round of 32.",
                }
            )
    return sorted(teams, key=lambda team: (team["owner"], team["name"]))


def initial_matches() -> list[dict]:
    matches = []
    match_number = 1
    pairings = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]
    for group, teams in GROUPS.items():
        dates = MATCH_DATES[group]
        for index, (home_index, away_index) in enumerate(pairings):
            matchday = index // 2
            matches.append(
                {
                    "id": f"m{match_number:03d}",
                    "stage": "group_stage",
                    "label": f"Group {group}",
                    "date": dates[matchday],
                    "home_team": teams[home_index],
                    "away_team": teams[away_index],
                    "home_score": None,
                    "away_score": None,
                    "status": "scheduled",
                    "winner": None,
                    "home_probability": 0.5,
                    "away_probability": 0.5,
                    "source": "seed",
                }
            )
            match_number += 1

    for index, (date, home_team, away_team, location) in enumerate(ROUND_OF_32_FIXTURES, start=1):
        matches.append(
            {
                "id": f"m{match_number:03d}",
                "stage": "round_of_32",
                "label": f"Match {match_number}",
                "date": date,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": None,
                "away_score": None,
                "status": "scheduled",
                "winner": None,
                "home_probability": 0.5,
                "away_probability": 0.5,
                "location": location,
                "source": "confirmed-bracket",
            }
        )
        match_number += 1

    for stage, label, date, count in KNOCKOUT_PLACEHOLDERS:
        for index in range(1, count + 1):
            matches.append(
                {
                    "id": f"m{match_number:03d}",
                    "stage": stage,
                    "label": label,
                    "date": date,
                    "home_team": f"{label} team {index}A",
                    "away_team": f"{label} team {index}B",
                    "home_score": None,
                    "away_score": None,
                    "status": "scheduled",
                    "winner": None,
                    "home_probability": 0.5,
                    "away_probability": 0.5,
                    "source": "placeholder",
                }
            )
            match_number += 1
    return matches


def initial_cache() -> dict:
    return {
        "provider": "manual",
        "last_sync": "2026-06-28T21:35:00+01:00",
        "message": "Manual Round of 32 bracket loaded. Missing most group-stage scorelines and live results unless FOOTBALL_PROVIDER=football-data is configured.",
        "raw_count": len(ROUND_OF_32_FIXTURES),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
