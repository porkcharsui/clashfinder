# Clashfinder Feed Tools

**Official festival data in. One battle-tested schedule out.**

Clashfinder Feed Tools extracts schedule and artist data from official festival
apps and transforms it into feeds for
[Clashfinder](https://clashfinder.com/).

Festival apps remain the canonical source for lineup changes, set times, artist
details, and stage information. This project does not try to replace them or
invent another schedule ecosystem. It gives their data a more useful interface:
the clear, consistent, easy-to-scan Clashfinder experience.

## Why Clashfinder?

At a festival, a schedule is operational equipment. It needs to work quickly,
predictably, and with minimal attention when the sun is gone, the network is
congested, and a rave dance battle is already underway.

Every festival shipping another bespoke app means another unfamiliar interface,
another account or onboarding flow, and another experience that may barely work
when it matters most. Clashfinder offers one familiar view across festivals. It
makes clashes obvious, supports fast planning, and puts the timetable ahead of
everything else.

The philosophy is simple:

* **Trust the official app for the facts.** Its data feeds are the canonical
  schedule and artist resource.
* **Transform rather than duplicate.** Convert those feeds into Clashfinder
  data instead of maintaining a competing schedule by hand.
* **Use one dependable interface.** Learn Clashfinder once, then use it at every
  festival.

```text
Official festival app → canonical data feed → transform → Clashfinder
```

The result combines authoritative festival data with an interface designed for
the moment you actually need it.

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
CLASHFINDER_COOKIE="userLogin=your-cookie-value"
```

The cookie is used only for authenticated Clashfinder requests and is never
printed by the CLI. For GitHub Actions, store a base64-encoded copy in the
`CLASHFINDER_COOKIE_BASE64` secret:

```bash
printf '%s' 'userLogin=your-cookie-value' | base64
```

Response-only attributes copied from a `Set-Cookie` header, such as `expires`,
`Max-Age`, and `path`, are not needed; the CLI strips them if they are present.

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
