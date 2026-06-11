#!/usr/bin/env bash
set -euo pipefail

URL="${1:?url required}"
TIMEOUT="${2:-120}"
INTERVAL="${3:-2}"

deadline=$((SECONDS + TIMEOUT))
while (( SECONDS < deadline )); do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "OK: $URL"
    exit 0
  fi
  sleep "$INTERVAL"
done

echo "Timeout waiting for $URL" >&2
exit 1
