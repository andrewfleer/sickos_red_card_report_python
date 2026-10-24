import json
from pathlib import Path
import unittest

from playground import League, format_report, format_team_report


class FormatTopRedCardsReportTest(unittest.TestCase):
    def test_report_lists_all_players_and_requested_statistics(self):
        sample_path = (
            Path(__file__).parent.parent
            / "example_jsons"
            / "topRedCards.json"
        )
        with sample_path.open(encoding="utf-8") as sample_file:
            payload = json.load(sample_file)

        report = format_report(payload, 2026, League(id=254, name="NWSL"))
        report_rows = [
            tuple(value.strip() for value in line.split("|"))
            for line in report.splitlines()
            if "|" in line
        ]

        self.assertIn("Player", report)
        self.assertIn("Team", report)
        self.assertIn("Red Cards", report)
        self.assertIn("Goals", report)
        self.assertIn("Yellow Cards", report)
        self.assertIn(
            ("B. St-Georges", "Boston Legacy W", "2", "2", "3"),
            report_rows,
        )
        self.assertIn(
            ("Ana Tejada", "Utah Royals W", "1", "0", "9"),
            report_rows,
        )
        self.assertEqual(len(report.splitlines()), 24)

    def test_red_card_column_sums_direct_red_and_yellowred_cards(self):
        payload = {
            "response": [
                {
                    "player": {"name": "Example Player"},
                    "statistics": [
                        {
                            "team": {"name": "Example Team"},
                            "goals": {"total": 4},
                            "cards": {"yellowred": 2, "red": 6, "yellow": 3},
                        }
                    ],
                }
            ]
        }

        report = format_report(payload, 2026, League(id=254, name="NWSL"))
        report_rows = [
            tuple(value.strip() for value in line.split("|"))
            for line in report.splitlines()
            if "|" in line
        ]

        self.assertIn(
            ("Example Player", "Example Team", "8", "4", "3"),
            report_rows,
        )
        self.assertNotIn(
            ("Example Player", "Example Team", "2", "4", "3"),
            report_rows,
        )

    def test_empty_response_still_produces_a_header(self):
        report = format_report(
            {"response": []},
            2026,
            League(id=254, name="NWSL"),
        )

        self.assertIn("Player", report)
        self.assertIn("Yellow Cards", report)

    def test_team_report_sorts_by_red_cards_goals_then_yellow_cards(self):
        teams_payload = {
            "response": [
                {"team": {"id": 1, "name": "Team A"}},
                {"team": {"id": 2, "name": "Team B"}},
                {"team": {"id": 3, "name": "Team C"}},
                {"team": {"id": 4, "name": "Team D"}},
            ]
        }
        statistics_by_team_id = {
            1: self._team_statistics(goals=99, red=1, yellow=10),
            2: self._team_statistics(goals=50, red=2, yellow=4),
            3: self._team_statistics(goals=50, red=2, yellow=8),
            4: self._team_statistics(goals=75, red=2, yellow=1),
        }

        report = format_team_report(
            teams_payload,
            statistics_by_team_id,
            2026,
            League(id=254, name="NWSL"),
        )
        team_rows = [
            tuple(value.strip() for value in line.split("|"))
            for line in report.splitlines()
            if "|" in line
        ][1:]

        self.assertEqual(
            [row[1] for row in team_rows],
            ["Team D", "Team C", "Team B", "Team A"],
        )
        self.assertEqual(
            team_rows[0],
            ("1", "Team D", "2", "75", "1"),
        )

    def test_team_report_reads_card_buckets_from_sample_shape(self):
        root = Path(__file__).parent.parent
        with (root / "example_jsons" / "teams.json").open(encoding="utf-8") as teams_file:
            teams_payload = json.load(teams_file)
        with (root / "example_jsons" / "teamsStatistics.json").open(
            encoding="utf-8"
        ) as statistics_file:
            statistics_payload = json.load(statistics_file)

        team_id = teams_payload["response"][0]["team"]["id"]
        report = format_team_report(
            {"response": [teams_payload["response"][0]]},
            {team_id: statistics_payload},
            2026,
            League(id=254, name="NWSL"),
        )
        report_rows = [
            tuple(value.strip() for value in line.split("|"))
            for line in report.splitlines()
            if "|" in line
        ]

        self.assertIn("Chicago Red Stars W", report)
        self.assertIn(
            ("1", "Chicago Red Stars W", "0", "66", "73"),
            report_rows,
        )

    @staticmethod
    def _team_statistics(goals, red, yellow):
        return {
            "response": {
                "goals": {"for": {"total": {"total": goals}}},
                "cards": {
                    "red": {"0-15": {"total": red}},
                    "yellow": {"0-15": {"total": yellow}},
                },
            }
        }


if __name__ == "__main__":
    unittest.main()
