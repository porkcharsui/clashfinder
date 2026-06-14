#!/usr/bin/env python3
import os
import re
from datetime import datetime
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from urllib.parse import urljoin

import click
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from git import InvalidGitRepositoryError, NoSuchPathError, Repo


CLASHFINDER_BASE_URL = "https://clashfinder.com"
REPOSITORY_URL = "https://github.com/porkcharsui/clashfinder"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Safari/537.36"
)
REVISION_PREFIX = "Festival schedule intel dispatch"


class ClashfinderError(Exception):
    pass


def get_git_revision(path):
    try:
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise ClashfinderError(f"The Clashfinder data path is not a file: {path}")

        repo = Repo(file_path.parent, search_parent_directories=True)
        repo_root = Path(repo.working_tree_dir).resolve()
        try:
            relative_path = file_path.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise ClashfinderError(
                "The Clashfinder data file is outside the Git working tree."
            ) from exc

        tracked_paths = {entry[0] for entry in repo.index.entries}
        if relative_path not in tracked_paths:
            raise ClashfinderError(
                "The Clashfinder data file is not tracked by Git. Commit it before uploading."
            )
        if repo.is_dirty(path=relative_path, untracked_files=True):
            raise ClashfinderError(
                "The Clashfinder data file has uncommitted changes. "
                "Commit it before uploading."
            )

        latest_file_commit = next(
            repo.iter_commits(paths=relative_path, max_count=1), None
        )
        if latest_file_commit is None:
            raise ClashfinderError(
                "Unable to find a Git commit containing the Clashfinder data file."
            )

        full_sha = latest_file_commit.hexsha
        short_sha = full_sha[:7]
    except (InvalidGitRepositoryError, NoSuchPathError, ValueError) as exc:
        raise ClashfinderError("Unable to determine the current Git revision.") from exc

    return full_sha, short_sha


def build_revision_note(full_sha, short_sha, force=False, now=None):
    commit_url = f"{REPOSITORY_URL}/commit/{full_sha}"
    note = f"{REVISION_PREFIX} · {short_sha} · {commit_url}"
    if force:
        timestamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
        note = f"{note} · forced {timestamp}"
    return note


def validate_schedule_data(data):
    if not data.strip():
        raise ClashfinderError("The Clashfinder data file is empty.")
    if not re.search(r"(?m)^\s*timezone\s*=", data):
        raise ClashfinderError("The Clashfinder data file does not contain a timezone.")
    if not re.search(r"(?m)^\s*act\s*=", data):
        raise ClashfinderError("The Clashfinder data file does not contain any acts.")


def successful_form_controls(form):
    controls = []

    for control in form.find_all(["input", "textarea", "select"]):
        name = control.get("name")
        if not name or control.has_attr("disabled"):
            continue

        if control.name == "textarea":
            controls.append((name, control.get_text()))
            continue

        if control.name == "select":
            options = control.find_all("option")
            selected = [option for option in options if option.has_attr("selected")]
            if not selected and options:
                selected = options[:1]
            for option in selected:
                controls.append((name, option.get("value", option.get_text())))
            continue

        input_type = control.get("type", "text").lower()
        if input_type in {"submit", "button", "reset", "file", "image"}:
            continue
        if input_type in {"checkbox", "radio"} and not control.has_attr("checked"):
            continue
        controls.append((name, control.get("value", "")))

    return controls


def replace_control(controls, name, value):
    return [(key, existing) for key, existing in controls if key != name] + [(name, value)]


def normalize_cookie_header(cookie):
    parsed = SimpleCookie()
    try:
        parsed.load(cookie.strip())
    except CookieError as exc:
        raise ClashfinderError("CLASHFINDER_COOKIE is not a valid cookie string.") from exc

    if not parsed:
        raise ClashfinderError("CLASHFINDER_COOKIE does not contain a cookie.")

    return "; ".join(f"{name}={morsel.value}" for name, morsel in parsed.items())


class ClashfinderClient:
    def __init__(self, cookie, session=None, base_url=CLASHFINDER_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update(
            {"Cookie": normalize_cookie_header(cookie), "User-Agent": USER_AGENT}
        )

    def edit_url(self, name):
        return f"{self.base_url}/s/{name}/?edit"

    def revisions_url(self, name):
        return f"{self.base_url}/l/{name}/?revs"

    def _get(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ClashfinderError(f"Unable to fetch {url}: {exc}") from exc
        return response

    def latest_revision_note(self, name):
        soup = BeautifulSoup(self._get(self.revisions_url(name)).text, "html.parser")
        note = soup.select_one(".revNote")
        return note.get_text(" ", strip=True) if note else None

    def prepare_update(self, name, schedule_data, revision_note):
        response = self._get(self.edit_url(name))
        soup = BeautifulSoup(response.text, "html.parser")

        if not re.search(r"\bisLoggedIn:\s*true\b", response.text):
            raise ClashfinderError(
                "Clashfinder authentication failed. Check CLASHFINDER_COOKIE."
            )

        schedule_control = soup.select_one("#jq-input1")
        if schedule_control is None or schedule_control.get("name") != "input1":
            raise ClashfinderError("Unable to find the Clashfinder data field #jq-input1.")

        form = schedule_control.find_parent("form")
        if form is None:
            raise ClashfinderError("Unable to find the update form containing #jq-input1.")

        controls = successful_form_controls(form)
        controls = replace_control(controls, "input1", schedule_data)
        controls = replace_control(controls, "revNote", revision_note)
        controls = replace_control(controls, "entData", "Update")
        action = urljoin(response.url, form.get("action") or response.url)
        return action, controls

    def update(self, name, schedule_data, revision_note):
        action, controls = self.prepare_update(name, schedule_data, revision_note)
        try:
            response = self.session.post(action, data=controls, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ClashfinderError(f"Clashfinder rejected the update: {exc}") from exc

        latest_note = self.latest_revision_note(name)
        if latest_note != revision_note:
            actual_note = latest_note or "(no revision note found)"
            raise ClashfinderError(
                "Clashfinder accepted the update request, but the new revision could not "
                "be verified.\n"
                f"Expected latest note: {revision_note}\n"
                f"Actual latest note: {actual_note}\n"
                f"Inspect revisions: {self.revisions_url(name)}"
            )


@click.command()
@click.option("--name", required=True, help="Clashfinder name, such as smf2026.")
@click.option(
    "--path",
    required=True,
    type=click.File("r", encoding="utf-8"),
    help="Clashfinder data source file.",
)
@click.option("--dry-run", is_flag=True, help="Compare revisions without uploading.")
@click.option("--force", is_flag=True, help="Upload even when the current revision matches.")
def update(name, path, dry_run, force):
    """Upload generated Clashfinder data when the Git revision changes."""
    load_dotenv()
    cookie = os.environ.get("CLASHFINDER_COOKIE")
    if not cookie:
        raise click.ClickException(
            "CLASHFINDER_COOKIE is unset. Add it to .env or the environment."
        )

    try:
        schedule_data = path.read()
        validate_schedule_data(schedule_data)
        full_sha, short_sha = get_git_revision(path.name)
        revision_note = build_revision_note(full_sha, short_sha, force=force)

        client = ClashfinderClient(cookie)
        click.echo(f"Checking Clashfinder revisions for {name}...")
        latest_note = client.latest_revision_note(name)

        if latest_note == revision_note and not force:
            click.echo(f"Already uploaded Git revision {short_sha}; nothing to do.")
            return

        if dry_run:
            action, _controls = client.prepare_update(name, schedule_data, revision_note)
            click.echo("Dry run: an upload would be submitted.")
            click.echo(f"Revision note: {revision_note}")
            click.echo(f"Data: {len(schedule_data.encode('utf-8'))} bytes from {path.name}")
            click.echo(f"Form action: {action}")
            return

        click.echo(f"Uploading Git revision {short_sha} to {name}...")
        client.update(name, schedule_data, revision_note)
        click.echo(f"Uploaded successfully: {revision_note}")
    except ClashfinderError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    update()
