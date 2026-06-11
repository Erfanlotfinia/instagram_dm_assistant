#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "==> Backend pytest"
Push-Location backend
py -3.12 -m pytest app/tests -q --tb=line
Pop-Location

Write-Host "==> Backend migrations (requires Postgres on localhost:5432)"
Push-Location backend
py -3.12 -m alembic upgrade head
Pop-Location

Write-Host "==> Frontend typecheck"
Push-Location frontend
npm run typecheck
npm run lint
npm test -- --run
npm run build
Pop-Location

Write-Host "All local verification steps passed."
