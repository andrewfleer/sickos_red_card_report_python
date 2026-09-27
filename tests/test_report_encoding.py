import os
import tempfile
import unittest

from main import generate_report


class GenerateReportEncodingTest(unittest.TestCase):
    def test_report_writes_utf8_unicode_characters(self):
        class Team:
            def __init__(self, name):
                self.name = name

        class Event:
            def __init__(self):
                self.time = 45
                self.extraTime = 0
                self.team = Team("Team A")
                self.player = "Player One"
                self.assist = "Player Two"
                self.eventType = "Card"
                self.eventDetail = "Red Card"

        class Match:
            def __init__(self):
                self.homeTeam = Team("Home")
                self.awayTeam = Team("Away")
                self.league = type("League", (), {"name": "League", "country": "Country"})()
                self.homeScore = 1
                self.awayScore = 0
                self.redCards = 1
                self.events = [Event()]

        match = Match()
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            path = tmp.name

        try:
            generate_report([match], "2026-09-25", path)
            with open(path, "r", encoding="utf-8") as report:
                contents = report.read()
            self.assertIn("🟥", contents)
            self.assertIn("⏱️", contents)
            self.assertIn("Team A", contents)
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
