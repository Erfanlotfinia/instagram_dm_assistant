#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose config
docker compose build
docker compose up -d

bash scripts/wait_for_http.sh "http://localhost:8800/health" 180
bash scripts/wait_for_http.sh "http://localhost:8800/api/v1/ready" 180
bash scripts/wait_for_http.sh "http://localhost:5173" 180

docker compose ps
docker compose logs backend --tail=50 || true

docker compose down -v
