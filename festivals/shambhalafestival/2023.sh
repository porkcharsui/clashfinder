#!/usr/bin/env bash

# load session key
[[ ! -f .env ]] && echo "ERROR: env file with session key missing" && exit 1 
set -o allexport; source .env; set +o allexport

DESTINATION_DIR=$(pwd)/2023

mkdir -p "${DESTINATION_DIR}"

# Fetching lineup
curl -H "Host: app.appmiral.com" -H "Content-Type: application/json" -H "x-protect: ${SESSION_KEY}" -H "Accept: application/json" -H "User-Agent: ShambhalaFestival-2023/3299 CFNetwork/1408.0.4 Darwin/22.5.0" -H "Accept-Language: en" --compressed "https://app.appmiral.com/api/v6/events/shambhalafestival/editions/shambhalafestival2023/artists?includehistory=true&maxperpage=500" | jq > "${DESTINATION_DIR}/shambhalafestival.artists.json"
# Fetching stages
curl -H "Host: app.appmiral.com" -H "Content-Type: application/json" -H "x-protect: ${SESSION_KEY}" -H "Accept: application/json" -H "User-Agent: ShambhalaFestival-2023/3299 CFNetwork/1408.0.4 Darwin/22.5.0" -H "Accept-Language: en" --compressed "https://app.appmiral.com/api/v6/events/shambhalafestival/editions/shambhalafestival2023/stages?includehistory=true&maxperpage=100" | jq > "${DESTINATION_DIR}/shambhalafestival.stages.json"
