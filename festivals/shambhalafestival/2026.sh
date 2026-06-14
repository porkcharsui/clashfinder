#!/usr/bin/env bash

# load session key
[[ ! -f .env ]] && echo "ERROR: env file with session key missing" && exit 1 
set -o allexport; source .env; set +o allexport

DESTINATION_DIR=$(pwd)/2026

mkdir -p "${DESTINATION_DIR}"

NORMALIZE_APPMIRAL_JSON='
  del(..|.modified_at?)
  | .data |= (
    map(
      if (.performances? | type) == "array" then
        .performances |= sort_by(.id // .external_id // .start_time // "")
      else
        .
      end
      | if (.tracks? | type) == "array" then
        .tracks |= sort_by(.track_id // .title // "")
      else
        .
      end
      | if (.tags? | type) == "array" then
        .tags |= sort_by(.slug // .name // "")
      else
        .
      end
    )
    | sort_by(.id // .external_id // .name // "")
  )
'

# Fetching lineup
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2026/497 CFNetwork/3826.500.131 Darwin/25.5.0' -H 'x-app-version: 8.0.0' -H 'x-os-version: 26.5' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2026/artists?max_per_page=1000' | \
  # Remove volatile fields and normalize API order.
  jq -S "${NORMALIZE_APPMIRAL_JSON}" > "${DESTINATION_DIR}/shambhalafestival.artists.json"
# Fetching stages
curl -H 'content-type: application/json' -H 'accept: application/json' --compressed -H "x-protect: $SESSION_KEY" -H 'accept-language: en' -H 'user-agent: ShambhalaFestival-2026/497 CFNetwork/3826.500.131 Darwin/25.5.0' -H 'x-app-version: 8.0.0' -H 'x-os-version: 26.5' -H 'x-platform: ios' 'https://app.appmiral.com/api/v7/events/shambhalafestival/editions/shambhalafestival2026/stages?max_per_page=500' | \
  # Remove volatile fields and normalize API order.
  jq -S "${NORMALIZE_APPMIRAL_JSON}" > "${DESTINATION_DIR}/shambhalafestival.stages.json"
