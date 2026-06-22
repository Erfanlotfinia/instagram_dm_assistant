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

if [[ ! -f docker/postgres/init-app-user.sh ]]; then
  echo "Missing docker/postgres/init-app-user.sh" >&2
  exit 1
fi

BACKEND_PORT="$(grep -E '^BACKEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r' || true)"
BACKEND_PORT="${BACKEND_PORT:-8800}"
FRONTEND_PORT="$(grep -E '^FRONTEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r' || true)"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

INFRA_SERVICES=(postgres redis rabbitmq qdrant)

dump_service_logs() {
  local service="$1"
  echo "---- ${service} logs (last 100 lines) ----"
  docker compose logs "${service}" --tail=100 || true
}

on_failure() {
  echo "Docker smoke test failed." >&2
  docker compose ps || true
  for service in "${INFRA_SERVICES[@]}" backend frontend; do
    dump_service_logs "${service}"
  done
  docker compose down -v || true
}

trap on_failure ERR

docker compose config
docker compose build

echo "==> Starting infrastructure services"
docker compose up -d "${INFRA_SERVICES[@]}"

for service in "${INFRA_SERVICES[@]}"; do
  bash scripts/wait_for_compose_healthy.sh "${service}" 240
done

echo "==> Starting application services"
docker compose up -d

bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/health" 240
bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/ready" 240
bash scripts/wait_for_http.sh "http://localhost:${FRONTEND_PORT}" 240

docker compose ps
docker compose logs backend --tail=50 || true

trap - ERR
docker compose down -v
