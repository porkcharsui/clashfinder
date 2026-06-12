# ClashFinder

Tools to export raw data from festival applications and transform into [Clashfinder](https://clashfinder.com/) schedules

## Supported Festival Platforms

* [Appmiral](https://appmiral.com/): Shambhala Festival
* GreenCopper / Aloompa FestApp: Lightning in a Bottle

## Setup

Required tools for use: 

* curl
* jq
* uv

`uv` manages the project's Python version and dependencies from
`pyproject.toml` and `uv.lock`. Create the locked project environment after
cloning:

```bash
uv sync --locked
```

Run Python tools through `uv run`; activating `.venv` manually is not required.

Extract the application session key using a MITM proxy tool like [Charles Proxy](https://www.charlesproxy.com/) or [mitmproxy](https://mitmproxy.org/).

Within the desired festival application directory, add the extracted `SESSION_KEY` to a `.env` file (e.g. `festivals/shambhalafestival/.env`). The format should be:

```
SESSION_KEY=VALUE_HERE
```

To upload generated data to Clashfinder, add the authenticated Clashfinder cookie
to the repository-root `.env` file:

```dotenv
CLASHFINDER_COOKIE="your-cookie-value"
```

The cookie is used only for authenticated Clashfinder requests and is never
printed by the CLI.

GreenCopper / Aloompa FestApp extraction currently uses the app's local SQLite database after the iOS app has run on macOS. On macOS 26, download the iOS festival app from the App Store, launch it, and let it finish updating its in-app data. This creates a Mac/iOS app container under `~/Library/Containers` with the app's preferences and `Documents/db.sqlite` database. The Lightning in a Bottle script finds that container, copies the SQLite database, exports schedule JSON, and renders Clashfinder text.

## Usage

* Extract all scheduling data by running an extract script

```bash
pushd festivals/shambhalafestival
./2026.sh
popd
```

For Lightning in a Bottle 2026, first install and run the iOS app on macOS 26, then run:

```bash
./festivals/lightninginabottle/2026.sh
```

This writes:

```text
festivals/lightninginabottle/2026/db.sqlite
festivals/lightninginabottle/2026/lightning-in-a-bottle-2026-schedule.json
festivals/lightninginabottle/2026/clashfinder.txt
```

* Render the scheduling data as Clashfinder markup and paste the output from the transform script into the Clashfinder data field:

```bash
uv run ./bin/appmiral_transform.py --tz "US/Pacific" --artists festivals/shambhalafestival/2026/shambhalafestival.artists.json --stages festivals/shambhalafestival/2026/shambhalafestival.stages.json
```

`uv run` ensures the project environment is available before running the
transform.

For GreenCopper / Aloompa FestApp schedule exports:

```bash
uv run ./bin/greencopper_transform.py \
  --schedule exports/lightning-in-a-bottle-2026-schedule.json \
  > festivals/lightninginabottle/2026/clashfinder.txt
```

## Uploading to Clashfinder

Upload a generated data file when the current Git commit has not already been
published:

```bash
uv run ./bin/clashfinder.py \
  --name smf2026 \
  --path festivals/shambhalafestival/2026/clashfinder.txt
```

The CLI generates a revision note containing the current Git commit, then reads
the latest revision note from Clashfinder before uploading. If Clashfinder's
latest revision note exactly matches the note the CLI generated, the CLI
recognizes its own previous upload and exits successfully without uploading the
same revision again.

Before comparing or uploading, the CLI verifies that `--path` points to a
tracked file with no uncommitted changes. This ensures the commit linked in the
revision note contains the exact Clashfinder data being uploaded. Commit changes
to the data file before running the CLI; `--force` does not bypass this check.

Uploaded revisions include the direct URL to their GitHub commit.

Use `--dry-run` to compare revisions without submitting data. Use `--force` to
upload even when the CLI recognizes its own revision note; forced revision
notes include a local ISO timestamp so they remain unique.

The input file is authoritative and replaces the Clashfinder data field while
preserving the schedule's existing setup data and form settings.

## Clashfinder Data Format

Each performance is composed of an `act` object with ` start`, `end`, `stage`, and `act` keys. 
```
timezone = US/Pacific

act = {"start": "2024-07-24 07:30", "end": "2024-07-24 09:00", "stage": "Pagoda", "act": "Justin Martin", "blurb": "Some text about this artist.", "url": "https://example.com/artist"}
```

The schedule dictates the festival's local time zone. While performing a data transform, set the `--tz` flag to match this timezone to ensure accurate schedules are produced. TZ values are defined by the [TZ database](https://www.iana.org/time-zones).
