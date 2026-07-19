import importlib.util
import json
import unittest
from pathlib import Path

from click.testing import CliRunner


MODULE_PATH = Path(__file__).parents[1] / "bin" / "appmiral_transform.py"
SPEC = importlib.util.spec_from_file_location("appmiral_transform", MODULE_PATH)
appmiral_transform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(appmiral_transform)


class AppmiralTransformTests(unittest.TestCase):
    def test_activity_uses_performance_name_body_and_preserves_host(self):
        artist = {
            "name": "Damian Williams and Jayeson",
            "show_in_artists": False,
        }
        performance = {
            "name": "Wire Wrapping with Wizards",
            "body": "<p>Learn the fundamentals of wire wrapping.</p>",
        }

        self.assertEqual(
            appmiral_transform.performance_name(artist, performance),
            "Wire Wrapping with Wizards",
        )
        self.assertEqual(
            appmiral_transform.performance_blurb(artist, performance),
            "Hosted by Damian Williams and Jayeson\n\n"
            "Learn the fundamentals of wire wrapping.",
        )

    def test_blurb_html_is_converted_to_plain_text(self):
        body = (
            "<P>First line<BR>\n  Second line &amp; more</P>"
            "<p><span>Next paragraph</span></p>"
        )

        self.assertEqual(
            appmiral_transform.plain_text(body),
            "First line\nSecond line & more\n\nNext paragraph",
        )

    def test_lineup_artist_keeps_artist_name_and_biography(self):
        artist = {
            "name": "Simula",
            "body": "Artist biography",
            "show_in_artists": True,
        }
        performance = {
            "name": "Simula w/ Jakes (140 Set)",
            "body": "Set description",
        }

        self.assertEqual(
            appmiral_transform.performance_name(artist, performance),
            "Simula",
        )
        self.assertEqual(
            appmiral_transform.performance_blurb(artist, performance),
            "Artist biography",
        )

    def test_artist_values_are_fallbacks_for_older_feeds(self):
        artist = {"name": "Artist", "body": "Artist biography"}

        self.assertEqual(
            appmiral_transform.performance_name(artist, {}),
            "Artist",
        )
        self.assertEqual(
            appmiral_transform.performance_blurb(artist, {}),
            "Artist biography",
        )


class AppmiralTransformCliTests(unittest.TestCase):
    def test_cli_emits_transformed_activity(self):
        artists = {
            "data": [
                {
                    "id": 2110023,
                    "name": "Damian Williams and Jayeson",
                    "show_in_artists": False,
                    "links": {"instagram_user": "snailwizardtreasures"},
                    "performances": [
                        {
                            "name": "Wire Wrapping with Wizards",
                            "body": "Workshop details",
                            "start_time": "2026-07-21T21:00:00+00:00",
                            "end_time": "2026-07-22T00:00:00+00:00",
                            "stage_id": 18201,
                        }
                    ],
                }
            ]
        }
        stages = {"data": [{"id": 18201, "name": "Culture Canopy"}]}
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("artists.json").write_text(json.dumps(artists))
            Path("stages.json").write_text(json.dumps(stages))
            result = runner.invoke(
                appmiral_transform.transform,
                [
                    "--artists",
                    "artists.json",
                    "--stages",
                    "stages.json",
                    "--tz",
                    "US/Pacific",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('"act": "Wire Wrapping with Wizards"', result.output)
        self.assertIn(
            '"blurb": "Hosted by Damian Williams and Jayeson\\n\\n'
            'Workshop details"',
            result.output,
        )


if __name__ == "__main__":
    unittest.main()
