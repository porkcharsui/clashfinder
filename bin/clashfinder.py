#!/usr/bin/env python3
import click
import requests
import os
from dotenv import load_dotenv

CLASHFINDER_BASE_URL = "https://clashfinder.com/s"

# Load auth cookie from .env file, terminate if not found
load_dotenv()
cf_cookie = os.environ.get("CLASHFINDER_COOKIE")
if not cf_cookie:
    raise SystemExit("🛑 CLASHFINDER_COOKIE unset, please set ENV variable and retry!")

@click.command()
@click.option("--name", required=True, help="Clashfinder Name (field: cfName)")
@click.option("--path", required=True, type=click.File('rb'), help="Clashfinder data source file (field: input1)")
@click.option("--dry-run", is_flag=True, default=False, help="Do not update Clashfinder, but print out the request which would be made to the console")
def update(name, path, dry_run):
    print(f"Fetching {name} from clashfinder...")

    r = requests.get(f"{CLASHFINDER_BASE_URL}/{name}", cookies=cf_cookie)






    return




if __name__ == "__main__":
    update()
