#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend migrations (requires Postgres on localhost:5432)"
bash scripts/check_migrations.sh

echo "==> Backend pytest"
(cd backend && pytest app/tests -q --tb=line)

echo "==> Frontend typecheck"
(cd frontend && npm run typecheck)

echo "==> Frontend lint"
(cd frontend && npm run lint)

echo "==> Frontend test"
(cd frontend && npm test -- --run)

echo "==> Frontend build"
(cd frontend && npm run build)

echo "All local verification steps passed."
