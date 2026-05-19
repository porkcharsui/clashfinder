#!/usr/bin/env bash

set -euo pipefail
set -x

APP_BUNDLE_ID="com.greencopper.lightninginabottle"
APP_ID="d0c90624-7b09-40a6-a782-4cbacd61c629"
SUB_APP_ID="dacd6cc1-59a4-47ba-b1a2-081ae655a55e"
APP_NAME="2026 Lightning In a Bottle"
TIMEZONE="America/Los_Angeles"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DESTINATION_DIR="${SCRIPT_DIR}/2026"

mkdir -p "${DESTINATION_DIR}"

# Find the Mac/iOS app container that has the GreenCopper app's preferences and database.
if [[ -z "${SQLITE_DB:-}" ]]; then
  SQLITE_DB=""
  while read -r db; do
    data_dir="$(dirname "$(dirname "${db}")")"
    prefs="${data_dir}/Library/Preferences/${APP_BUNDLE_ID}.plist"
    if [[ -f "${prefs}" ]]; then
      SQLITE_DB="${db}"
      break
    fi
  done < <(find "${HOME}/Library/Containers" -path "*/Data/Documents/db.sqlite" -print 2>/dev/null)
fi

[[ -z "${SQLITE_DB}" ]] && echo "ERROR: SQLite DB not found for ${APP_BUNDLE_ID}" && exit 1
[[ ! -f "${SQLITE_DB}" ]] && echo "ERROR: SQLite DB path does not exist: ${SQLITE_DB}" && exit 1

cp "${SQLITE_DB}" "${DESTINATION_DIR}/db.sqlite"

python3 - "${DESTINATION_DIR}/db.sqlite" "${DESTINATION_DIR}/lightning-in-a-bottle-2026-schedule.json" <<'PY'
import datetime
import json
import sqlite3
import sys
from zoneinfo import ZoneInfo


APP_ID = "d0c90624-7b09-40a6-a782-4cbacd61c629"
SUB_APP_ID = "dacd6cc1-59a4-47ba-b1a2-081ae655a55e"
APP_NAME = "2026 Lightning In a Bottle"
TIMEZONE = "America/Los_Angeles"


def rows(conn, query):
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query).fetchall()]


def parse_json(value):
    if value in (None, ""):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def split_ids(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def iso_utc(epoch):
    if epoch is None:
        return None
    return datetime.datetime.fromtimestamp(epoch, datetime.UTC).isoformat().replace("+00:00", "Z")


def local_time(epoch, tz_name=TIMEZONE):
    if epoch is None:
        return None
    tz = ZoneInfo(tz_name)
    return datetime.datetime.fromtimestamp(epoch, tz).strftime("%Y-%m-%dT%H:%M:%S")


def compact_performer(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "image": row["image"],
        "profile_image": row["profile_image"],
        "thumbnail_image": row["thumbnail_image"],
        "small_image": row["small_image"],
        "featured_image": row["featured_image"],
        "links": {
            "website": row["website_url"],
            "instagram": row["instagram_url"],
            "facebook": row["facebook_url"],
            "spotify": row["spotify_url"],
            "soundcloud": row["soundcloud_url"],
            "youtube": row["youtube_url"],
            "tiktok": row["tiktok_url"],
            "twitch": row["twitch_url"],
            "music": row["music_url"],
        },
        "share_short_url": row["share_short_url"],
        "deep_link_uri": row["deep_link_uri"],
    }


def compact_category(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category_type": row["category_type"],
        "parent_category_id": row["parent_category_id"],
        "is_root_category": row["is_root_category"] == 1,
        "color": row["color"],
        "tag_color": row["tag_color"],
        "image": row["image"],
    }


db_path, output_path = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db_path)

app_rows = rows(conn, "select * from dragonfly_app_table limit 1")
schedule_day_rows = rows(conn, "select * from schedule_day_table order by starts_at_utc")
event_rows = rows(conn, "select * from event_table order by starts_at_utc, name")
performer_rows = rows(conn, "select * from performer_table order by name")
category_rows = rows(conn, "select * from category_table order by category_type, name")
scheduled_rows = rows(conn, "select * from scheduled_event_table")

performers = {row["id"]: compact_performer(row) for row in performer_rows}
categories = {row["id"]: compact_category(row) for row in category_rows}
scheduled_events = {row["id"]: row for row in scheduled_rows}

schedule_days = []
for row in schedule_day_rows:
    starts_at = parse_json(row["starts_at"])
    tz_name = starts_at.get("timezoneName", TIMEZONE) if isinstance(starts_at, dict) else TIMEZONE
    schedule_days.append({
        "id": row["id"],
        "name": row["name"],
        "starts_at": starts_at,
        "starts_at_utc": row["starts_at_utc"],
        "starts_at_iso_utc": iso_utc(row["starts_at_utc"]),
        "starts_at_local": local_time(row["starts_at_utc"], tz_name),
    })

stages = sorted(
    {
        (row["stage_id"] or row["stage_name"]): {"id": row["stage_id"], "name": row["stage_name"]}
        for row in event_rows
        if row["stage_name"]
    }.values(),
    key=lambda item: item["name"],
)

events = []
for row in event_rows:
    starts_at = parse_json(row["starts_at"])
    ends_at = parse_json(row["ends_at"])
    opens_at = parse_json(row["opens_at"])
    tz_name = TIMEZONE
    if isinstance(starts_at, dict) and starts_at.get("timezoneName"):
        tz_name = starts_at["timezoneName"]
    elif isinstance(ends_at, dict) and ends_at.get("timezoneName"):
        tz_name = ends_at["timezoneName"]

    performer_ids = split_ids(row["performer_ids"])
    category_ids = split_ids(row["category_ids"])
    scheduled = scheduled_events.get(row["id"])

    events.append({
        "id": row["id"],
        "sub_app_id": row["sub_app_id"],
        "name": row["name"],
        "description": row["description"],
        "preview": row["preview"],
        "status_message": row["status_message"],
        "image": row["image"],
        "images": {
            "profile": row["profile_image"],
            "thumbnail": row["thumbnail_image"],
            "small": row["small_image"],
            "featured": row["featured_image"],
            "copyright": row["image_copyright_text"],
        },
        "stage": {"id": row["stage_id"], "name": row["stage_name"]},
        "schedule_day_id": row["schedule_day_id"],
        "time_is_tbd": row["time_is_tbd"] == 1,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "opens_at": opens_at,
        "starts_at_utc": row["starts_at_utc"],
        "ends_at_utc": row["ends_at_utc"],
        "starts_at_iso_utc": iso_utc(row["starts_at_utc"]),
        "ends_at_iso_utc": iso_utc(row["ends_at_utc"]),
        "starts_at_local": local_time(row["starts_at_utc"], tz_name),
        "ends_at_local": local_time(row["ends_at_utc"], tz_name),
        "event_capacity": row["event_capacity"],
        "feed_mapping_id": row["feed_mapping_id"],
        "share_short_url": row["share_short_url"],
        "deep_link_uri": row["deep_link_uri"],
        "common_button": parse_json(row["common_button"]) or {
            "text": row["common_button_text"],
            "color": row["common_button_color"],
            "url": row["common_button_url"],
        },
        "performer_ids": performer_ids,
        "performers": [performers.get(performer_id, {"id": performer_id}) for performer_id in performer_ids],
        "category_ids": category_ids,
        "categories": [categories.get(category_id, {"id": category_id}) for category_id in category_ids],
        "user_scheduled": scheduled["scheduled"] == 1 if scheduled else False,
    })

export = {
    "metadata": {
        "exported_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "source_app": app_rows[0] if app_rows else None,
        "app_id": APP_ID,
        "sub_app_id": SUB_APP_ID,
        "app_name": APP_NAME,
        "timezone": TIMEZONE,
        "counts": {
            "events": len(events),
            "schedule_days": len(schedule_days),
            "stages": len(stages),
            "performers": len(performer_rows),
            "categories": len(category_rows),
        },
    },
    "schedule_days": schedule_days,
    "stages": stages,
    "events": events,
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(export, f, indent=2)
    f.write("\n")
PY

(
  cd "${REPO_ROOT}"
  uv run ./bin/greencopper_transform.py \
    --schedule "${DESTINATION_DIR}/lightning-in-a-bottle-2026-schedule.json" \
    > "${DESTINATION_DIR}/clashfinder.txt"
)
