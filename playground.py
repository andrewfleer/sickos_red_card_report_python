from dataclasses import dataclass
import os
import time

import requests
from dotenv import load_dotenv


@dataclass
class League:
    id: int
    name: str


def format_report(payload, season, league):
    players = payload.get("response", [])
    headers = ("Player", "Team", "Red Cards", "Goals", "Yellow Cards")
    rows = []

    for result in players:
        player_name = result.get("player", {}).get("name") or "N/A"
        statistics = result.get("statistics") or [{}]
        for statistic in statistics:
            team_name = statistic.get("team", {}).get("name") or "N/A"
            goals = statistic.get("goals", {})
            cards = statistic.get("cards", {})
            direct_red_cards = cards.get("red")
            second_yellow_red_cards = cards.get("yellowred")
            red_cards = (
                None
                if direct_red_cards is None and second_yellow_red_cards is None
                else (direct_red_cards or 0) + (second_yellow_red_cards or 0)
            )
            rows.append(
                (
                    player_name,
                    team_name,
                    "N/A" if red_cards is None else str(red_cards),
                    "N/A" if goals.get("total") is None else str(goals["total"]),
                    "N/A" if cards.get("yellow") is None else str(cards["yellow"]),
                )
            )

    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]

    def format_row(values):
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    separator = "-+-".join("-" * width for width in widths)
    report_lines = [
        f"Top Red Cards Report - Season {season}, League {league.name}",
        "",
        format_row(headers),
        separator,
        *(format_row(row) for row in rows),
    ]
    return "\n".join(report_lines) + "\n"


def format_team_report(teams_payload, statistics_by_team_id, season, league):
    rows = []

    for team_entry in teams_payload.get("response", []):
        team = team_entry.get("team", {})
        team_id = team.get("id")
        team_name = team.get("name") or "N/A"
        statistics_payload = statistics_by_team_id.get(team_id, {})
        statistics = statistics_payload.get("response") or {}
        cards = statistics.get("cards", {})
        goals = statistics.get("goals", {}).get("for", {}).get("total", {})
        rows.append(
            (
                team_name,
                _sum_card_totals(cards.get("red", {})),
                goals.get("total") or 0,
                _sum_card_totals(cards.get("yellow", {})),
            )
        )

    rows.sort(key=lambda row: (-row[1], -row[2], -row[3], row[0].casefold()))
    headers = ("Rank", "Team", "Red Cards", "Goals", "Yellow Cards")
    table_rows = [
        (str(index), team, str(red), str(goals), str(yellow))
        for index, (team, red, goals, yellow) in enumerate(rows, start=1)
    ]
    widths = [
        max([len(header), *(len(row[index]) for row in table_rows)])
        for index, header in enumerate(headers)
    ]

    def format_row(values):
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    separator = "-+-".join("-" * width for width in widths)
    report_lines = [
        f"Team Red Card Report - Season {season}, League {league.name}",
        "",
        format_row(headers),
        separator,
        *(format_row(row) for row in table_rows),
    ]
    return "\n".join(report_lines) + "\n"


def _sum_card_totals(card_buckets):
    return sum(
        bucket.get("total") or 0
        for bucket in card_buckets.values()
    )


def main():
    load_dotenv(dotenv_path="secrets.env")
    api_key = os.getenv("api_key") or os.getenv("API_KEY")

    if not api_key:
        raise ValueError("Missing api_key / API_KEY environment variable")

    base_url = "https://v3.football.api-sports.io/"
    season = 2026

    league = League(id=254, name="NWSL")
    top_red_cards_url = f"{base_url}players/topredcards"
    response = requests.get(
        top_red_cards_url,
        headers={"x-apisports-key": api_key},
        params={"season": season, "league": league.id},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"API returned errors: {payload['errors']}")

    report = format_report(payload, season, league)
    file_name = f"top_red_cards_report_{season}_{league.id}.txt"
    with open(file_name, "w", encoding="utf-8") as report_file:
        report_file.write(report)

    print(report)
    print(f"Report saved to {file_name}.")

    teams_url = f"{base_url}teams"
    teams_response = requests.get(
        teams_url,
        headers={"x-apisports-key": api_key},
        params={"season": season, "league": league.id},
        timeout=30,
    )
    teams_response.raise_for_status()
    teams_payload = teams_response.json()
    if teams_payload.get("errors"):
        raise RuntimeError(f"API returned errors fetching teams: {teams_payload['errors']}")

    statistics_by_team_id = {}
    for team_entry in teams_payload.get("response", []):
        team = team_entry.get("team", {})
        team_id = team.get("id")
        if team_id is None:
            raise ValueError(f"Team response is missing an ID: {team_entry}")

        statistics_url = f"{base_url}teams/statistics"
        statistics_response = requests.get(
            statistics_url,
            headers={"x-apisports-key": api_key},
            params={"league": league.id, "team": team_id, "season": season},
            timeout=30,
        )
        statistics_response.raise_for_status()
        statistics_payload = statistics_response.json()
        if statistics_payload.get("errors"):
            raise RuntimeError(
                f"API returned errors fetching statistics for {team.get('name', team_id)}: "
                f"{statistics_payload['errors']}"
            )
        statistics_by_team_id[team_id] = statistics_payload
        time.sleep(0.25)

    team_report = format_team_report(
        teams_payload,
        statistics_by_team_id,
        season,
        league,
    )
    team_file_name = f"team_red_card_report_{season}_{league.id}.txt"
    with open(team_file_name, "w", encoding="utf-8") as report_file:
        report_file.write(team_report)

    print(team_report)
    print(f"Team report saved to {team_file_name}.")


if __name__ == "__main__":
    main()
