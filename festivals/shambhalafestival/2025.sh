#!/usr/bin/env bash

set -x

# load session key
[[ ! -f .env ]] && echo "ERROR: env file with session key missing" && exit 1 
set -o allexport; source .env; set +o allexport

DESTINATION_DIR=$(pwd)/2025

mkdir -p "${DESTINATION_DIR}"

# Fetching lineup
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2025/9526 CFNetwork/3826.500.131 Darwin/24.5.0' -H 'x-app-version: 7.0.0' -H 'x-os-version: 18.5' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2025/artists?max_per_page=500' | jq > "${DESTINATION_DIR}/shambhalafestival.artists.json"
# Fetching stages
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2025/9526 CFNetwork/3826.500.131 Darwin/24.5.0' -H 'x-app-version: 7.0.0' -H 'x-os-version: 18.5' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2025/stages?max_per_page=500' | jq > "${DESTINATION_DIR}/shambhalafestival.stages.json"
