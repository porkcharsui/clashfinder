#!/usr/bin/env python3
import json

import arrow
import click


TS_FORMAT = "YYYY-MM-DD HH:mm"
URL_PREFERENCE = (
    "spotify",
    "soundcloud",
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


def get_event_time(act, key, tz):
    epoch_ms = act.get(key)
    if epoch_ms is None:
        return None
    return arrow.get(epoch_ms / 1000).to(tz).format(TS_FORMAT)


def get_primary_url(artist):
    for link_type in URL_PREFERENCE:
        for link in artist.get("links") or []:
            if link.get("type") == link_type and link.get("url"):
                return link["url"]
    return ""


def get_act_artists(act, artists_by_id):
    weighted_artists = act.get("artists") or []
    if weighted_artists:
        artist_ids = [
            item.get("id")
            for item in sorted(weighted_artists, key=lambda item: item.get("weight", 0))
            if item.get("id")
        ]
    else:
        artist_ids = act.get("artistIds") or []

    return [artists_by_id[artist_id] for artist_id in artist_ids if artist_id in artists_by_id]


def get_act_name(act, act_artists):
    artist_names = [artist.get("name") for artist in act_artists if artist.get("name")]
    return first_present(act.get("name"), ", ".join(artist_names))


def get_blurb(act, act_artists):
    artist_blurb = ""
    if len(act_artists) == 1:
        artist_blurb = act_artists[0].get("description") or ""
    return first_present(act.get("description"), artist_blurb)


def get_url(act_artists):
    if len(act_artists) != 1:
        return ""
    return get_primary_url(act_artists[0])


@click.command()
@click.option("--schedule", required=True, type=click.File("rb"), help="Woov timetable JSON")
@click.option("--tz", default="America/Vancouver", help="TZ to convert act timestamps into")
def transform(schedule, tz):
    schedule = json.load(schedule)
    stages_by_id = {
        stage["id"]: stage["name"]
        for stage in schedule.get("stages", [])
        if stage.get("id") and stage.get("name")
    }
    artists_by_id = {
        artist["id"]: artist
        for artist in schedule.get("artists", [])
        if artist.get("id")
    }

    acts_list = []
    skipped_acts = 0
    missing_stage_acts = 0

    for act in schedule.get("acts", []):
        start_ts = get_event_time(act, "startTime", tz)
        end_ts = get_event_time(act, "endTime", tz)
        if not start_ts or not end_ts:
            skipped_acts += 1
            continue

        stage = stages_by_id.get(act.get("stageId"))
        if not stage:
            missing_stage_acts += 1
            stage = act.get("stageId") or "Other"

        act_artists = get_act_artists(act, artists_by_id)
        acts_list.append(
            {
                "start": start_ts,
                "end": end_ts,
                "stage": stage,
                "act": get_act_name(act, act_artists),
                "url": get_url(act_artists),
                "blurb": get_blurb(act, act_artists),
            }
        )

    print(f"timezone = {tz}")
    print(f"// total acts found = {len(acts_list)}")
    if skipped_acts:
        print(f"// skipped acts without start/end times = {skipped_acts}")
    if missing_stage_acts:
        print(f"// acts with missing stage names = {missing_stage_acts}")

    acts_list.sort(key=lambda act: (act["stage"], act["start"], act["end"], act["act"]))

    for act in acts_list:
        print(f"act = {json.dumps(act)}")


if __name__ == "__main__":
    transform()
