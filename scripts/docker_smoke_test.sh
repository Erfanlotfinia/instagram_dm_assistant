#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "Created .env from .env.example"
  else
    echo "Missing .env and .env.example" >&2
    exit 1
  fi
fi

BACKEND_PORT="$(grep -E '^BACKEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r' || true)"
BACKEND_PORT="${BACKEND_PORT:-8800}"
FRONTEND_PORT="$(grep -E '^FRONTEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r' || true)"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

docker compose config
docker compose build
docker compose up -d

bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/health" 180
bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/ready" 180
bash scripts/wait_for_http.sh "http://localhost:${FRONTEND_PORT}" 180

docker compose ps
docker compose logs backend --tail=50 || true

docker compose down -v
