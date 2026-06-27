#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"

ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/modira-prod-env.XXXXXX")"
RESTORE_ENV=false
REMOVED_ENV=false

cleanup() {
  rm -f "$ENV_FILE"
  if [[ "$RESTORE_ENV" == "true" && -f .env.smoke-backup ]]; then
    mv .env.smoke-backup .env
  elif [[ "$REMOVED_ENV" == "true" ]]; then
    rm -f .env
  fi
}
trap cleanup EXIT

generate_secret() {
  python -c "import secrets; print(secrets.token_urlsafe(32))"
}

generate_fernet_key() {
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

if [[ ! -f .env.production.example ]]; then
  echo "Missing .env.production.example" >&2
  exit 1
fi

cp .env.production.example "$ENV_FILE"

# Replace placeholders with generated production-grade test secrets.
sed -i.bak \
  -e "s|<generate-min-32-char-secret>|$(generate_secret)|g" \
  -e "s|<generate-fernet-compatible-32-byte-key>|$(generate_fernet_key)|g" \
  -e "s|<generate-webhook-verification-secret>|$(generate_secret)|g" \
  -e "s|<generate-oauth-state-secret>|$(generate_secret)|g" \
  -e "s|<strong-postgres-app-password>|$(generate_secret)|g" \
  -e "s|<strong-postgres-superuser-password>|$(generate_secret)|g" \
  -e "s|<rabbitmq-username>|modira_rmq|g" \
  -e "s|<strong-rabbitmq-password>|$(generate_secret)|g" \
  -e "s|<meta-app-id>|test-meta-app-id|g" \
  -e "s|<meta-app-secret>|$(generate_secret)|g" \
  -e "s|<openai-or-compatible-api-key>|test-openai-key|g" \
  -e "s|<admin-email@example.com>|admin-prod-smoke@example.com|g" \
  -e "s|<strong-admin-password>|$(generate_secret)|g" \
  -e "s|https://api.example.com|http://localhost:8800|g" \
  -e "s|https://admin.example.com|http://localhost:8080|g" \
  -e "s|https://www.example.com|http://localhost:8081|g" \
  "$ENV_FILE"
rm -f "${ENV_FILE}.bak"

# Exercise the production overlay without HTTPS/CORS production validation blockers.
sed -i.bak \
  -e 's/^APP_ENV=production/APP_ENV=development/' \
  -e 's|^CORS_ORIGINS=\["https://admin.example.com"\]|CORS_ORIGINS=["http://localhost:8080"]|' \
  -e 's/^AUTH_COOKIE_SECURE=true/AUTH_COOKIE_SECURE=false/' \
  -e 's/^LLM_MODE=live/LLM_MODE=mock/' \
  -e 's/^ENABLE_REAL_PROVIDER_SEND=true/ENABLE_REAL_PROVIDER_SEND=false/' \
  -e 's/^BACKEND_HOST_PORT=8000/BACKEND_HOST_PORT=8800/' \
  -e 's|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://localhost:8800|' \
  -e 's|^VITE_PUBLIC_API_BASE_URL=.*|VITE_PUBLIC_API_BASE_URL=http://localhost:8800|' \
  -e 's|^VITE_LANDING_URL=.*|VITE_LANDING_URL=http://localhost:8081|' \
  -e 's|^VITE_FRONTEND_URL=.*|VITE_FRONTEND_URL=http://localhost:8080|' \
  -e 's|^PUBLIC_API_BASE_URL=.*|PUBLIC_API_BASE_URL=http://localhost:8800|' \
  -e 's|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=http://localhost:8080|' \
  "$ENV_FILE"
rm -f "${ENV_FILE}.bak"

if [[ -f .env ]]; then
  cp .env .env.smoke-backup
  RESTORE_ENV=true
else
  REMOVED_ENV=true
fi
cp "$ENV_FILE" .env

BACKEND_PORT="$(grep -E '^BACKEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r')"
BACKEND_PORT="${BACKEND_PORT:-8800}"
FRONTEND_PORT="$(grep -E '^FRONTEND_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r')"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"
LANDING_PORT="$(grep -E '^LANDING_HOST_PORT=' .env | cut -d= -f2- | tr -d '\r')"
LANDING_PORT="${LANDING_PORT:-8081}"

INFRA_SERVICES=(postgres redis rabbitmq qdrant)

dump_service_logs() {
  local service="$1"
  echo "---- ${service} logs (last 100 lines) ----"
  docker compose logs "${service}" --tail=100 || true
}

on_failure() {
  echo "Production Docker smoke test failed." >&2
  docker compose ps || true
  for service in "${INFRA_SERVICES[@]}" backend-migrate backend frontend landing; do
    dump_service_logs "${service}"
  done
  docker compose down -v || true
}

trap on_failure ERR

echo "==> Validating production compose config"
docker compose config >/dev/null

echo "==> Building production images"
docker compose build

echo "==> Starting infrastructure services"
docker compose up -d "${INFRA_SERVICES[@]}"

for service in "${INFRA_SERVICES[@]}"; do
  bash scripts/wait_for_compose_healthy.sh "${service}" 240
done

echo "==> Starting application services (includes one-shot backend-migrate)"
docker compose up -d

bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/health" 240
bash scripts/wait_for_http.sh "http://localhost:${BACKEND_PORT}/ready" 240
bash scripts/wait_for_http.sh "http://localhost:${FRONTEND_PORT}/health" 240
bash scripts/wait_for_http.sh "http://localhost:${LANDING_PORT}/health" 240

echo "==> Verifying backend runs as non-root"
backend_uid="$(docker compose exec -T backend id -u | tr -d '\r')"
if [[ "$backend_uid" == "0" ]]; then
  echo "Backend container is running as root (uid 0)" >&2
  exit 1
fi
echo "Backend uid: ${backend_uid}"

echo "==> Verifying no dev bind mounts on backend"
backend_mounts="$(docker inspect "$(docker compose ps -q backend)" \
  --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}')"
if echo "$backend_mounts" | grep -q '/backend/app'; then
  echo "Production backend still has source bind mounts:" >&2
  echo "$backend_mounts" >&2
  exit 1
fi

docker compose ps

trap - ERR
docker compose down -v
echo "Production Docker smoke test passed."
