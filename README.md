# ClashFinder

Tools to export raw data from festival applications and render [Clashfinder](https://clashfinder.com/)

## Supported Applications

* [Appmiral](https://appmiral.com/)
  * Shambhala Festival

## Usage

Required for use: 

* curl
* jq
* python 3+

### Setup

Extract the application session key using a MITM proxy tool like [Charles Proxy](https://www.charlesproxy.com/) or [mitmproxy](https://mitmproxy.org/).

Within the desired festival application directory, add the extracted `SESSION_KEY` to a `.env` file (e.g. `festivals/shambhalafestival/.env`). The format should be:

```
SESSION_KEY=VALUE_HERE
```