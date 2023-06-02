# ClashFinder

Tools to export raw data from festival applications and transform into [Clashfinder](https://clashfinder.com/) schedules

## Supported Festival Platforms

* [Appmiral](https://appmiral.com/)
  * Shambhala Festival
## Setup

Required tools for use: 

* curl
* jq
* pipenv
* python 3+

Extract the application session key using a MITM proxy tool like [Charles Proxy](https://www.charlesproxy.com/) or [mitmproxy](https://mitmproxy.org/).

Within the desired festival application directory, add the extracted `SESSION_KEY` to a `.env` file (e.g. `festivals/shambhalafestival/.env`). The format should be:

```
SESSION_KEY=VALUE_HERE
```

## Usage

* Setup the python virtualenv using Pipenv

```bash
pipenv install
pipenv shell
```

* Extract all scheduling data by running an extract script

```bash
pushd festivals/shambhalafestival
./2023.sh
popd
```

* Render the scheduling data as Clashfinder markup and paste the output from the transform script into the Clashfinder data field:

```bash
./bin/appmiral_transform.py --tz "US/Pacific" --artists festivals/shambhalafestival/2023/shambhalafestival.artists.json --stages festivals/shambhalafestival/2023/shambhalafestival.stages.json
```

## Clashfinder Data Format

Each performance is composed of an `act` object with ` start`, `end`, `stage`, and `act` keys. 
```
timezone = US/Pacific

act = {"start": "2022-07-24 07:30", "end": "2022-07-24 09:00", "stage": "Pagoda", "act": "Justin Martin"}
```

The schedule dictates the festival's local time zone. While performing a data transform, set the `--tz` flag to match this timezone to ensure accurate schedules are produced. TZ values are defined by the [TZ database](https://www.iana.org/time-zones).
