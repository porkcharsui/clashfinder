#!/usr/bin/env bash

# load session key
[ ! -f .env ] && echo "ERROR: env file with session key missing" && exit 1 
set -o allexport; source .env; set +o allexport

# Fetching lineup
curl -H "Host: app.appmiral.com" -H "Content-Type: application/json" -H "x-protect: ${SESSION_KEY}" -H "Accept: application/json" -H "User-Agent: ShambhalaFestival-2022/1 CFNetwork/1333.0.4 Darwin/21.5.0" -H "Accept-Language: en" --compressed "https://app.appmiral.com/api/v6/events/shambhalafestival/editions/shambhalafestival2022/artists?includehistory=true&maxperpage=500" | jq > shambhalafestival.artists.json
# Fetching stages
curl -H "Host: app.appmiral.com" -H "Content-Type: application/json" -H "x-protect: ${SESSION_KEY}" -H "Accept: application/json" -H "User-Agent: ShambhalaFestival-2022/1 CFNetwork/1333.0.4 Darwin/21.5.0" -H "Accept-Language: en" --compressed "https://app.appmiral.com/api/v6/events/shambhalafestival/editions/shambhalafestival2022/stages?includehistory=true&maxperpage=100" | jq > shambhalafestival.stages.json
