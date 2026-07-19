#!/usr/bin/env python3
import json
import re

import arrow
import click
from bs4 import BeautifulSoup

ts_format = "YYYY-MM-DD HH:mm"
LINE_BREAK_MARKER = "\0line-break\0"
PARAGRAPH_BREAK_MARKER = "\0paragraph-break\0"
BLOCK_TAGS = (
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "main",
    "nav",
    "p",
    "section",
)


def plain_text(value):
    """Strip HTML while retaining line and paragraph breaks as plain text."""
    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")
    for tag in soup.find_all("br"):
        tag.replace_with(LINE_BREAK_MARKER)
    for tag in soup.find_all(BLOCK_TAGS):
        tag.append(PARAGRAPH_BREAK_MARKER)
    for tag in soup.find_all(("li", "tr")):
        tag.append(LINE_BREAK_MARKER)

    text = soup.get_text().replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\N{NO-BREAK SPACE}", " ")
    text = re.sub(
        rf"[ \t\n]*{re.escape(LINE_BREAK_MARKER)}[ \t\n]*",
        LINE_BREAK_MARKER,
        text,
    )
    text = re.sub(
        rf"[ \t\n]*{re.escape(PARAGRAPH_BREAK_MARKER)}[ \t\n]*",
        PARAGRAPH_BREAK_MARKER,
        text,
    )
    text = text.replace(LINE_BREAK_MARKER, "\n").replace(
        PARAGRAPH_BREAK_MARKER, "\n\n"
    )
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def performance_name(artist, performance):
    """Use the scheduled event name when the parent record represents a host."""
    if artist.get("show_in_artists") is False:
        return performance.get("name") or artist["name"]
    return artist["name"]


def performance_blurb(artist, performance):
    """Build a description from the performance body and preserve activity hosts."""
    if artist.get("show_in_artists") is not False:
        return plain_text(artist.get("body"))

    body = plain_text(performance.get("body") or artist.get("body"))
    scheduled_name = performance.get("name")
    is_hosted_event = scheduled_name and scheduled_name != artist["name"]
    if not is_hosted_event:
        return body

    host = f"Hosted by {artist['name']}"
    return f"{host}\n\n{body}" if body else host


@click.command()
@click.option("--artists", required=True, type=click.File('rb'), help="Artist JSON")
@click.option("--stages", required=True, type=click.File('rb'), help="Stage JSON")
@click.option("--tz", default="GMT", help="TZ to convert act timestamps into")
def transform(artists, stages, tz):
    artists = json.load(artists)
    stages = json.load(stages)

    # create look dictionary for all stages
    stage_dict = {}
    stage_priority = {}
    for s in stages['data']:
        if s.get('name'):
            stage_dict[s['id']] = s['name']
            # store priority for sorting (default to 999 if not available)
            stage_priority[s['name']] = s.get('priority', 999)

    acts_list = []

    # loop over all artists - each artists may have 1+ acts:
    for artist in artists['data']:
        if not artist.get('name'):
            continue

        if artist.get('performances'):
            for p in artist['performances']:
                # skip deleted and incomplete performances
                if p.get('deleted_at') or not p.get('start_time') or not p.get('end_time'):
                    continue

                # produce clashfinder act dict object
                # e.g. act = {"start":"2016-06-24 18:15","end":"2016-06-24 19:15","stage":"Pyramid","act":"Jess Glynne"}
                start_ts = arrow.get(p['start_time']).to(tz)
                end_ts = arrow.get(p['end_time']).to(tz)
                stage = stage_dict.get(p.get('stage_id'), p.get('stage_name'))
                if not stage:
                    continue
                act = performance_name(artist, p)
                blurb = performance_blurb(artist, p)
                
                # select a primary URL to use for the act; prefer spotify, if not found fallback to others
                url = ""
                if 'links' in artist:
                    if 'spotify_artist_id' in artist['links']:
                        url = f"https://open.spotify.com/artist/{artist['links']['spotify_artist_id']}"
                    elif 'soundcloud_user' in artist['links']:
                        url = f"https://soundcloud.com/{artist['links']['soundcloud_user']}"
                    elif 'youtube_user' in artist['links']:
                        url = f"https://youtube.com/@{artist['links']['youtube_user']}"
                    elif 'instagram_user' in artist['links']:
                        url = f"https://instagram.com/{artist['links']['instagram_user']}"
                    elif 'facebook_page_id' in artist['links']:
                        url = f"https://facebook.com/{artist['links']['facebook_page_id']}"
                    else:
                        url = ""

                acts_list.append({"start": start_ts.format(ts_format), "end": end_ts.format(ts_format), "stage": stage, "act": act, "url": url, "blurb": blurb})
        else: 
            print(f"// no performances found for artist id={artist['id']}")

    print(f"timezone = {tz}")
    print(f"// total acts found = {len(acts_list)}")

    # Sort acts deterministically by priority first, then stage, then time/act details.
    # Priority uses stage_priority lookup; defaults to 999 if not found.
    acts_list.sort(key=lambda x: (stage_priority.get(x['stage'], 999), x['stage'], x['start'], x['end'], x['act'], x['url'], x['blurb']))

    for act in acts_list:
        print(f"act = {json.dumps(act)}")

if __name__ == "__main__":
    transform()
