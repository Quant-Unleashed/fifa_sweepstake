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
    ("round_of_32", "Round of 32", "2026-06-28", 16),
    ("round_of_16", "Round of 16", "2026-07-04", 8),
    ("quarterfinal", "Quarterfinal", "2026-07-09", 4),
    ("semifinal", "Semifinal", "2026-07-14", 2),
    ("third_place", "Third-place match", "2026-07-18", 1),
    ("final", "Final", "2026-07-19", 1),
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
    teams = []
    for group, names in GROUPS.items():
        for position, name in enumerate(names, start=1):
            teams.append(
                {
                    "id": slugify(name),
                    "name": name,
                    "owner": owner_for(name),
                    "group": group,
                    "group_position": position,
                    "status": "active",
                    "exit_stage": None,
                    "manual_title_probability": None,
                    "notes": "",
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
        "provider": None,
        "last_sync": None,
        "message": "No live-feed provider configured yet.",
        "raw_count": 0,
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
