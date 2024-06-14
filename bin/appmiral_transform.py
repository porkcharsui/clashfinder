#!/usr/bin/env python3
import click
import json
import arrow

ts_format = "YYYY-MM-DD HH:mm"

@click.command()
@click.option("--artists", required=True, type=click.File('rb'), help="Artist JSON")
@click.option("--stages", required=True, type=click.File('rb'), help="Stage JSON")
@click.option("--tz", default="GMT", help="TZ to convert act timestamps into")
def transform(artists, stages, tz):
    artists = json.load(artists)
    stages = json.load(stages)

    # create look dictionary for all stages
    stage_dict = {}
    for s in stages['data']:
        sid = s['id']
        stage_dict[sid] = s['name']

    acts_list = []

    # loop over all artists - each artists may have 1+ acts:
    for artist in artists['data']:
        if artist.get('performances'):
            for p in artist['performances']:
                # skip deleted performances
                if 'deleted_at' in p:
                    continue

                # produce clashfinder act dict object
                # e.g. act = {"start":"2016-06-24 18:15","end":"2016-06-24 19:15","stage":"Pyramid","act":"Jess Glynne"}
                start_ts = arrow.get(p['start_time']).to(tz)
                end_ts = arrow.get(p['end_time']).to(tz)
                stage = stage_dict[p['stage_id']]
                act = artist['name']
                blurb = artist['body']
                
                # select a primary URL to use for the act; prefer spotify, if not found fallback to others
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

    # Sort acts by stage name first, then by start time
    acts_list.sort(key=lambda x: (x['stage'], x['start']))

    for act in acts_list:
        print(f"act = {json.dumps(act)}")

if __name__ == "__main__":
    transform()
