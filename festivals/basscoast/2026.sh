#!/usr/bin/env bash

set -euo pipefail
set -x

SHARE_URL="${SHARE_URL:-https://woov.to/basscoast26}"
TIMEZONE="${TIMEZONE:-America/Vancouver}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DESTINATION_DIR="${SCRIPT_DIR}/2026"
SCHEDULE_JSON="${DESTINATION_DIR}/basscoast-2026-woov-timetable.json"

mkdir -p "${DESTINATION_DIR}"

EVENT_ID="$(
  curl -L -sS "${SHARE_URL}" |
    python3 -c 'import re, sys; data=sys.stdin.read(); match=re.search(r"woov://events/([0-9a-f-]{36})", data); print(match.group(1) if match else "", end="")'
)"

[[ -z "${EVENT_ID}" ]] && echo "ERROR: unable to find Woov event ID in ${SHARE_URL}" && exit 1

curl -L -sS \
  -H "accept: application/json" \
  "https://woov.api.amplify.one/events/${EVENT_ID}/timetable" \
  > "${SCHEDULE_JSON}"

(
  cd "${REPO_ROOT}"
  uv run ./bin/woov_transform.py \
    --schedule "${SCHEDULE_JSON}" \
    --tz "${TIMEZONE}" \
    > "${DESTINATION_DIR}/clashfinder.txt"
)
