from datetime import datetime, timedelta
import time
import requests
import os
from dotenv import load_dotenv

########################
####### CLASSES ########
########################
class Team:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class League:
    def __init__(self, id, name, country):
        self.id = id
        self.name = name
        self.country = country

class Match:
    def __init__(self, id,homeTeam, awayTeam, homeScore, awayScore, league):
        self.id = id
        self.homeTeam = homeTeam
        self.awayTeam = awayTeam
        self.homeScore = homeScore
        self.awayScore = awayScore
        self.league = league
        self.events = []
        self.redCards = 0

class Event:
    def __init__(self, time, extraTime, team, player, assist, eventType, eventDetail):
        self.time = time
        self.extraTime = extraTime
        self.team = team
        self.player = player
        self.assist = assist
        self.eventType = eventType
        self.eventDetail = eventDetail
########################
##### END CLASSES ######
########################


def generate_report(matches, report_date, file_name, matches_with_red_cards=0, total_red_cards=0):
    with open(file_name, "w", encoding="utf-8") as report_file:
        report_file.write("="*60 + "\n")
        report_file.write(f"Red Card Report for {report_date}\n")
        report_file.write("="*60 + "\n\n")
        report_file.write(f"Total Matches with Red Cards: {matches_with_red_cards}\n")
        report_file.write(f"Total Red Cards: {total_red_cards}\n\n")
        for match in matches:
            if match.redCards > 0:
                report_file.write(f"Match: {match.homeTeam.name} vs {match.awayTeam.name} ({match.league.name}, {match.league.country})\n")
                report_file.write(f"Score: {match.homeScore} - {match.awayScore}\n")
                report_file.write(f"Total Red Cards: {match.redCards}\n")
                report_file.write("Notable Events:\n")
                for event in match.events:
                    event_emoji = ""
                    if event.eventType == "Goal":
                        event_emoji = "⚽"
                    elif event.eventType == "Card":
                        if event.eventDetail == "Red Card":
                            event_emoji = "🟥"
                        elif event.eventDetail == "Yellow Card":
                            event_emoji = "🟨"
                    if event.eventType == "Goal" or event.eventType == "Card":
                        event_time = event.time if event.time is not None else "N/A"
                        event_extra_time = event.extraTime if event.extraTime is not None else 0
                        report_file.write(
                            f"  ⏱️ Time: {event_time}' (Extra: {event_extra_time}') | "
                            f"{event_emoji} {event.eventType} - {event.eventDetail} | "
                            f"Team: {event.team.name} | Player: {event.player} | "
                            f"Assist: {event.assist}\n"
                        )
                report_file.write("\n")

def send_report_to_discord(file_name, discord_url):
    with open(file_name, "rb") as f:
        file_data = f.read()
        response = requests.post(
            discord_url,
            files={"file": (file_name, file_data)},
        )
        if response.status_code == 200 or response.status_code == 204:
            print(f"Report successfully sent to Discord.")
        else:
            print(f"Failed to send report to Discord. Status code: {response.status_code}, Response: {response.text}")
              


def main():
    load_dotenv(dotenv_path="secrets.env")  # Load local secrets when running on a dev machine
    api_key = os.getenv("api_key") or os.getenv("API_KEY")
    discord_url = os.getenv("discord_url") or os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_URL")

    if not api_key:
        raise ValueError("Missing api_key / API_KEY environment variable")
    if not discord_url:
        raise ValueError("Missing discord_url / DISCORD_WEBHOOK_URL / DISCORD_URL environment variable")

    start_time = time.perf_counter()
    api_counter = 0

    # get yesterday's date formatted as YYYY-MM-DD
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # api sports url
    base_url = "https://v3.football.api-sports.io/"

    all_matches = []

    fixtures_url = f"{base_url}fixtures?date={yesterday}"
    fixtures_response = requests.get(fixtures_url, headers={"x-apisports-key": api_key})
    api_counter += 1
    if fixtures_response.status_code != 200:
        print("Error fetching fixtures:", fixtures_response.status_code)
        exit()

    matches_with_red_cards = 0
    total_red_cards = 0
    fixtures_data = fixtures_response.json()
    fixtures = fixtures_data.get("response", [])
    for fixture in fixtures:
        fixture_id = fixture.get("fixture", {}).get("id")
        leauge_data = fixture.get("league", {})
        league = League(leauge_data.get("id"), leauge_data.get("name"), leauge_data.get("country"))
        home_team_data = fixture.get("teams", {}).get("home", {})
        away_team_data = fixture.get("teams", {}).get("away", {})
        home_team = Team(home_team_data.get("id"), home_team_data.get("name"))
        away_team = Team(away_team_data.get("id"), away_team_data.get("name"))
        home_score = fixture.get("goals", {}).get("home")
        away_score = fixture.get("goals", {}).get("away")

        match = Match(fixture_id, home_team, away_team, home_score, away_score, league)
        all_matches.append(match)

    print(f"Fetched {len(all_matches)} matches from {yesterday}. API calls made: {api_counter}")
    match_number = 1
    for match in all_matches:
        print(f"Getting events for match {match_number}/{len(all_matches)}: {match.homeTeam.name} vs {match.awayTeam.name}")
        events_url = f"{base_url}fixtures/events?fixture={match.id}"
        events_response = requests.get(events_url, headers={"x-apisports-key": api_key})
        api_counter += 1
        if events_response.status_code != 200:
            print("Error fetching events:", events_response.status_code)
            exit()

        events_data = events_response.json()
        events = events_data.get("response", [])
        for event in events:
            event_time = event.get("time", {}).get("elapsed")
            event_extra_time = event.get("time", {}).get("extra")
            event_team_data = event.get("team", {})
            event_team = Team(event_team_data.get("id"), event_team_data.get("name"))
            event_player_data = event.get("player", {})
            event_player = event_player_data.get("name")
            event_assist_data = event.get("assist", {})
            event_assist = event_assist_data.get("name")

            event_type = event.get("type")
            event_detail = event.get("detail")

            if event_type == "Card" and event_detail == "Red Card":
                match.redCards += 1
                total_red_cards += 1

            match_event = Event(event_time, event_extra_time, event_team, event_player, event_assist, event_type, event_detail)
            match.events.append(match_event)
        if match.redCards > 0:
            matches_with_red_cards += 1
        match_number += 1

    file_name = f"red_card_report_{yesterday}.txt"
    generate_report(all_matches, yesterday, file_name, matches_with_red_cards, total_red_cards)

    send_report_to_discord(file_name, discord_url)

    end_time = time.perf_counter()
    elapsed = end_time - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = elapsed % 60
    print(f"Report generated in {hours}h {minutes}m {seconds:.2f}s. Total API calls made: {api_counter}. Report saved to {file_name}.")


if __name__ == "__main__":
    main()