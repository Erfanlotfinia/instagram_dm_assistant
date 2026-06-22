#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:?service name required}"
TIMEOUT="${2:-240}"
INTERVAL="${3:-2}"

cid="$(docker compose ps -q "$SERVICE" 2>/dev/null || true)"
if [[ -z "$cid" ]]; then
  echo "Service ${SERVICE} is not running" >&2
  exit 1
fi

deadline=$((SECONDS + TIMEOUT))
last_status="starting"

while (( SECONDS < deadline )); do
  if ! cid="$(docker compose ps -q "$SERVICE" 2>/dev/null || true)" || [[ -z "$cid" ]]; then
    echo "Service ${SERVICE} is not running" >&2
    docker compose logs "$SERVICE" --tail=100 >&2 || true
    exit 1
  fi

  last_status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo missing)"

  case "$last_status" in
    healthy)
      echo "OK: ${SERVICE} is healthy"
      exit 0
      ;;
    running)
      # Services without a healthcheck report "running" instead of "healthy".
      if ! docker inspect --format='{{if .State.Health}}1{{end}}' "$cid" 2>/dev/null | grep -q 1; then
        echo "OK: ${SERVICE} is running"
        exit 0
      fi
      ;;
    exited|dead)
      echo "${SERVICE} container stopped (status=${last_status})" >&2
      docker compose logs "$SERVICE" --tail=100 >&2 || true
      exit 1
      ;;
  esac

  sleep "$INTERVAL"
done

echo "Timeout waiting for ${SERVICE} to become healthy (last status: ${last_status})" >&2
docker compose logs "$SERVICE" --tail=100 >&2 || true
exit 1
