#!/usr/bin/env bash

set -x

# load session key
[[ ! -f .env ]] && echo "ERROR: env file with session key missing" && exit 1 
set -o allexport; source .env; set +o allexport

DESTINATION_DIR=$(pwd)/2024

mkdir -p "${DESTINATION_DIR}"

# Fetching lineup
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2024/6145 CFNetwork/1496.0.7 Darwin/23.5.0' -H 'x-app-version: 6.0.0' -H 'x-os-version: 17.5.1' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2024/artists?max_per_page=500' | jq > "${DESTINATION_DIR}/shambhalafestival.artists.json"
# Fetching stages
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2024/6145 CFNetwork/1496.0.7 Darwin/23.5.0' -H 'x-app-version: 6.0.0' -H 'x-os-version: 17.5.1' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2024/stages?max_per_page=500' | jq > "${DESTINATION_DIR}/shambhalafestival.stages.json"
