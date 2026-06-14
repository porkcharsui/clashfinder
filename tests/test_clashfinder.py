import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from click.testing import CliRunner


MODULE_PATH = Path(__file__).parents[1] / "bin" / "clashfinder.py"
SPEC = importlib.util.spec_from_file_location("clashfinder_cli", MODULE_PATH)
clashfinder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clashfinder)


EDIT_HTML = """
<script>var cg = { isLoggedIn: true };</script>
<form action="" method="post">
  <textarea id="jq-input0" name="input0">maintitle = Test</textarea>
  <textarea id="jq-input1" name="input1">old data</textarea>
  <input type="text" id="revNote" name="revNote" value="">
  <input type="checkbox" name="checked" value="yes" checked>
  <input type="checkbox" name="unchecked" value="no">
  <select name="choice"><option value="a">A</option><option value="b" selected>B</option></select>
  <input type="submit" name="otherSubmit" value="Other">
  <input type="submit" name="entData" value="Update">
</form>
"""


def response(url, text, status=200):
    result = requests.Response()
    result.url = url
    result.status_code = status
    result._content = text.encode()
    return result


class RevisionTests(unittest.TestCase):
    @patch.object(clashfinder, "Repo")
    def test_git_revision_uses_repository_api(self, repo_class):
        repo_class.return_value.head.commit.hexsha = "a" * 40
        repo_class.return_value.working_tree_dir = "/repo"
        repo_class.return_value.index.entries = {("clashfinder.txt", 0): Mock()}
        repo_class.return_value.is_dirty.return_value = False
        with patch.object(
            clashfinder.Path,
            "resolve",
            side_effect=[Path("/repo/clashfinder.txt"), Path("/repo")],
        ):
            with patch.object(clashfinder.Path, "is_file", return_value=True):
                self.assertEqual(
                    clashfinder.get_git_revision("clashfinder.txt"),
                    ("a" * 40, "aaaaaaa"),
                )

    @patch.object(clashfinder, "Repo")
    def test_git_revision_rejects_dirty_file(self, repo_class):
        repo_class.return_value.working_tree_dir = "/repo"
        repo_class.return_value.index.entries = {("clashfinder.txt", 0): Mock()}
        repo_class.return_value.is_dirty.return_value = True
        with patch.object(
            clashfinder.Path,
            "resolve",
            side_effect=[Path("/repo/clashfinder.txt"), Path("/repo")],
        ):
            with patch.object(clashfinder.Path, "is_file", return_value=True):
                with self.assertRaisesRegex(clashfinder.ClashfinderError, "uncommitted"):
                    clashfinder.get_git_revision("clashfinder.txt")

    @patch.object(clashfinder, "Repo")
    def test_git_revision_rejects_untracked_file(self, repo_class):
        repo_class.return_value.working_tree_dir = "/repo"
        repo_class.return_value.index.entries = {}
        with patch.object(
            clashfinder.Path,
            "resolve",
            side_effect=[Path("/repo/clashfinder.txt"), Path("/repo")],
        ):
            with patch.object(clashfinder.Path, "is_file", return_value=True):
                with self.assertRaisesRegex(clashfinder.ClashfinderError, "not tracked"):
                    clashfinder.get_git_revision("clashfinder.txt")

    def test_revision_note_links_to_commit(self):
        note = clashfinder.build_revision_note("a" * 40, "aaaaaaa")
        self.assertEqual(
            note,
            "Festival schedule intel dispatch · aaaaaaa · "
            f"{clashfinder.REPOSITORY_URL}/commit/{'a' * 40}",
        )

    def test_force_revision_note_adds_local_timestamp(self):
        now = datetime(2026, 6, 12, 14, 30, tzinfo=timezone.utc)
        note = clashfinder.build_revision_note("a" * 40, "aaaaaaa", force=True, now=now)
        self.assertTrue(note.endswith("· forced 2026-06-12T14:30:00+00:00"))


class ValidationTests(unittest.TestCase):
    def test_valid_data(self):
        clashfinder.validate_schedule_data(
            'timezone = US/Pacific\nact = {"start": "2026-01-01 12:00"}\n'
        )

    def test_rejects_empty_or_incomplete_data(self):
        for data in ("", "timezone = US/Pacific\n", 'act = {"act": "Test"}\n'):
            with self.subTest(data=data), self.assertRaises(clashfinder.ClashfinderError):
                clashfinder.validate_schedule_data(data)


class ClientTests(unittest.TestCase):
    def test_client_strips_set_cookie_attributes(self):
        session = Mock()
        session.headers = {}
        cookie = (
            "userLogin=jamessmith%1234; expires=Thu, 12 Jun 2036 21:43:41 GMT; "
            "Max-Age=315619200; path=/"
        )

        clashfinder.ClashfinderClient(cookie, session=session)

        self.assertEqual(session.headers["Cookie"], "userLogin=jamessmith%1234")

    def test_latest_revision_note_reads_first_note(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = response(
            "https://clashfinder.com/l/test/?revs",
            '<span class="revNote">Newest</span><span class="revNote">Older</span>',
        )
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)
        self.assertEqual(client.latest_revision_note("test"), "Newest")

    def test_latest_revision_note_preserves_spacing_before_links(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = response(
            "https://clashfinder.com/l/test/?revs",
            '<span class="revNote">Festival schedule intel dispatch · aaaaaaa · '
            '<a href="https://github.com/porkcharsui/clashfinder/commit/aaaaaaaa">'
            "https://github.com/porkcharsui/clashfinder/commit/aaaaaaaa</a></span>",
        )
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)

        self.assertEqual(
            client.latest_revision_note("test"),
            "Festival schedule intel dispatch · aaaaaaa · "
            "https://github.com/porkcharsui/clashfinder/commit/aaaaaaaa",
        )

    def test_prepare_update_preserves_controls_and_replaces_data(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = response(
            "https://clashfinder.com/s/test/?edit", EDIT_HTML
        )
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)

        action, controls = client.prepare_update("test", "new data", "new note")

        self.assertEqual(action, "https://clashfinder.com/s/test/?edit")
        self.assertIn(("input0", "maintitle = Test"), controls)
        self.assertIn(("input1", "new data"), controls)
        self.assertIn(("revNote", "new note"), controls)
        self.assertIn(("checked", "yes"), controls)
        self.assertNotIn(("unchecked", "no"), controls)
        self.assertIn(("choice", "b"), controls)
        self.assertIn(("entData", "Update"), controls)
        self.assertFalse(any(name == "otherSubmit" for name, _ in controls))

    def test_prepare_update_rejects_expired_authentication(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = response(
            "https://clashfinder.com/s/test/?edit",
            EDIT_HTML.replace("isLoggedIn: true", "isLoggedIn: false"),
        )
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)
        with self.assertRaisesRegex(clashfinder.ClashfinderError, "authentication"):
            client.prepare_update("test", "new data", "new note")

    def test_prepare_update_rejects_missing_schedule_field(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = response(
            "https://clashfinder.com/s/test/?edit",
            '<script>var cg = { isLoggedIn: true };</script><form></form>',
        )
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)
        with self.assertRaisesRegex(clashfinder.ClashfinderError, "jq-input1"):
            client.prepare_update("test", "new data", "new note")

    def test_update_posts_and_verifies_revision(self):
        session = Mock()
        session.headers = {}
        session.get.side_effect = [
            response("https://clashfinder.com/s/test/?edit", EDIT_HTML),
            response(
                "https://clashfinder.com/l/test/?revs",
                '<span class="revNote">new note</span>',
            ),
        ]
        session.post.return_value = response("https://clashfinder.com/s/test/?edit", "ok")
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)

        client.update("test", "new data", "new note")

        posted = session.post.call_args.kwargs["data"]
        self.assertIn(("input1", "new data"), posted)
        self.assertIn(("revNote", "new note"), posted)

    def test_update_rejects_unverified_revision(self):
        session = Mock()
        session.headers = {}
        session.get.side_effect = [
            response("https://clashfinder.com/s/test/?edit", EDIT_HTML),
            response(
                "https://clashfinder.com/l/test/?revs",
                '<span class="revNote">different note</span>',
            ),
        ]
        session.post.return_value = response("https://clashfinder.com/s/test/?edit", "ok")
        client = clashfinder.ClashfinderClient("userLogin=secret", session=session)
        with self.assertRaises(clashfinder.ClashfinderError) as raised:
            client.update("test", "new data", "new note")
        message = str(raised.exception)
        self.assertIn("Expected latest note: new note", message)
        self.assertIn("Actual latest note: different note", message)
        self.assertIn("Inspect revisions: https://clashfinder.com/l/test/?revs", message)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.data = 'timezone = US/Pacific\nact = {"act": "Test"}\n'

    @patch.dict("os.environ", {"CLASHFINDER_COOKIE": "secret"}, clear=True)
    @patch.object(clashfinder, "get_git_revision", return_value=("a" * 40, "aaaaaaa"))
    @patch.object(clashfinder, "ClashfinderClient")
    def test_matching_revision_skips_upload(self, client_class, _git):
        note = clashfinder.build_revision_note("a" * 40, "aaaaaaa")
        client_class.return_value.latest_revision_note.return_value = note

        with self.runner.isolated_filesystem():
            Path("clashfinder.txt").write_text(self.data)
            result = self.runner.invoke(
                clashfinder.update, ["--name", "test", "--path", "clashfinder.txt"]
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("nothing to do", result.output)
        client_class.return_value.update.assert_not_called()

    @patch.dict("os.environ", {"CLASHFINDER_COOKIE": "secret"}, clear=True)
    @patch.object(clashfinder, "get_git_revision", return_value=("a" * 40, "aaaaaaa"))
    @patch.object(clashfinder, "ClashfinderClient")
    def test_dry_run_does_not_upload(self, client_class, _git):
        client_class.return_value.latest_revision_note.return_value = "old"
        client_class.return_value.prepare_update.return_value = (
            "https://clashfinder.com/s/test/?edit",
            [],
        )

        with self.runner.isolated_filesystem():
            Path("clashfinder.txt").write_text(self.data)
            result = self.runner.invoke(
                clashfinder.update,
                ["--name", "test", "--path", "clashfinder.txt", "--dry-run"],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Dry run", result.output)
        client_class.return_value.prepare_update.assert_called_once()
        client_class.return_value.update.assert_not_called()

    @patch.dict("os.environ", {"CLASHFINDER_COOKIE": "secret"}, clear=True)
    @patch.object(clashfinder, "get_git_revision", return_value=("a" * 40, "aaaaaaa"))
    @patch.object(clashfinder, "ClashfinderClient")
    def test_new_revision_uploads(self, client_class, _git):
        client_class.return_value.latest_revision_note.return_value = "old"

        with self.runner.isolated_filesystem():
            Path("clashfinder.txt").write_text(self.data)
            result = self.runner.invoke(
                clashfinder.update, ["--name", "test", "--path", "clashfinder.txt"]
            )

        self.assertEqual(result.exit_code, 0, result.output)
        client_class.return_value.update.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    @patch.object(clashfinder, "load_dotenv")
    def test_missing_cookie_fails(self, _load_dotenv):
        with self.runner.isolated_filesystem():
            Path("clashfinder.txt").write_text(self.data)
            result = self.runner.invoke(
                clashfinder.update, ["--name", "test", "--path", "clashfinder.txt"]
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("CLASHFINDER_COOKIE is unset", result.output)


if __name__ == "__main__":
    unittest.main()
