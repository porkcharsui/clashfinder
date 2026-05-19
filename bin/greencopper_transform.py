#!/usr/bin/env python3
import json

import arrow
import click


TS_FORMAT = "YYYY-MM-DD HH:mm"
URL_PREFERENCE = (
    "spotify",
    "soundcloud",
    "music",
    "website",
    "youtube",
    "instagram",
    "facebook",
    "tiktok",
    "twitch",
)


def first_present(*values):
    for value in values:
        if value:
            return value
    return ""


def get_event_epoch(event, key):
    value = event.get(key)
    if value is not None:
        return value

    embedded_key = key.removesuffix("_utc")
    embedded = event.get(embedded_key)
    if isinstance(embedded, dict):
        return embedded.get("date")

    return None


def get_event_time(event, key, tz):
    epoch = get_event_epoch(event, key)
    if epoch is None:
        return None
    return arrow.get(epoch).to(tz).format(TS_FORMAT)


def get_primary_url(event):
    performers = event.get("performers") or []

    if len(performers) == 1:
        links = performers[0].get("links") or {}
        for link_type in URL_PREFERENCE:
            if links.get(link_type):
                return links[link_type]
        if performers[0].get("share_short_url"):
            return performers[0]["share_short_url"]

    common_button = event.get("common_button") or {}
    if common_button.get("url"):
        return common_button["url"]

    return first_present(event.get("share_short_url"), event.get("deep_link_uri"))


def get_blurb(event):
    performers = event.get("performers") or []
    performer_blurb = ""
    if len(performers) == 1:
        performer_blurb = performers[0].get("description") or ""

    return first_present(event.get("description"), event.get("preview"), performer_blurb)


def infer_timezone(schedule):
    metadata_tz = (schedule.get("metadata") or {}).get("timezone")
    if metadata_tz:
        return metadata_tz

    for event in schedule.get("events", []):
        starts_at = event.get("starts_at")
        if isinstance(starts_at, dict) and starts_at.get("timezoneName"):
            return starts_at["timezoneName"]

    return "GMT"


@click.command()
@click.option("--schedule", required=True, type=click.File("rb"), help="GreenCopper schedule JSON")
@click.option("--tz", default=None, help="TZ to convert act timestamps into; defaults to schedule metadata timezone")
@click.option("--default-stage", default="Other", help="Stage name for events without a stage")
def transform(schedule, tz, default_stage):
    schedule = json.load(schedule)
    tz = tz or infer_timezone(schedule)

    acts_list = []
    skipped_events = 0
    defaulted_stage_events = 0

    for event in schedule.get("events", []):
        start_ts = get_event_time(event, "starts_at_utc", tz)
        end_ts = get_event_time(event, "ends_at_utc", tz)
        if not start_ts or not end_ts:
            skipped_events += 1
            continue

        stage = (event.get("stage") or {}).get("name")
        if not stage:
            stage = default_stage
            defaulted_stage_events += 1

        act = {
            "start": start_ts,
            "end": end_ts,
            "stage": stage,
            "act": event.get("name") or "",
            "url": get_primary_url(event),
            "blurb": get_blurb(event),
        }
        acts_list.append(act)

    print(f"timezone = {tz}")
    print(f"// total acts found = {len(acts_list)}")
    if skipped_events:
        print(f"// skipped events without start/end times = {skipped_events}")
    if defaulted_stage_events:
        print(f"// events assigned to default stage '{default_stage}' = {defaulted_stage_events}")

    acts_list.sort(key=lambda x: (x["stage"], x["start"], x["act"]))

    for act in acts_list:
        print(f"act = {json.dumps(act)}")


if __name__ == "__main__":
    transform()
