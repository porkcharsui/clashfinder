#!/usr/bin/env python3
import click
import json
import arrow

ts_format = "YYYY-MM-DD HH:mm"

@click.command()
@click.option("--artists", required=True, type=click.File('rb'), help="Artist JSON")
@click.option("--stages", required=True, type=click.File('rb'), help="Stage JSON")
def transform(artists, stages):
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
                # produce clashfinder act dict object
                # e.g. act = {"start":"2016-06-24 18:15","end":"2016-06-24 19:15","stage":"Pyramid","act":"Jess Glynne"}
                start_ts = arrow.get(p['start_time']).format(ts_format)
                end_ts = arrow.get(p['end_time']).format(ts_format)
                stage = stage_dict[p['stage_id']]
                act = artist['name']

                acts_list.append({"start": start_ts, "end": end_ts, "stage": stage, "act": act})
        else: 
            print(f"// no performances found for artist id={artist['id']}")

    print(f"// total acts found = {len(acts_list)}")

    for act in acts_list:
        print(f"act = {json.dumps(act)}")

if __name__ == "__main__":
    transform()
