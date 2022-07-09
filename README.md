# ClashFinder

Tools to export raw data from festival applications and render [Clashfinder](https://clashfinder.com/) schedules

## Supported Festival Platforms

* [Appmiral](https://appmiral.com/)
  * Shambhala Festival
## Setup

Required tools for use: 

* curl
* jq
* python 3+

Extract the application session key using a MITM proxy tool like [Charles Proxy](https://www.charlesproxy.com/) or [mitmproxy](https://mitmproxy.org/).

Within the desired festival application directory, add the extracted `SESSION_KEY` to a `.env` file (e.g. `festivals/shambhalafestival/.env`). The format should be:

```
SESSION_KEY=VALUE_HERE
```

## Usage

1. Extract all scheduling data by running an extract script
```
cd festivals/shambhalafestival
./2022.sh
```

2. Render the scheduling data as Clashfinder markup.

```
TODO
```