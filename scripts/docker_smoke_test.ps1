#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose config | Out-Null
docker compose build
docker compose up -d

$waitScript = Join-Path $PSScriptRoot "wait_for_http.ps1"
& $waitScript -Url "http://localhost:8800/health" -TimeoutSeconds 180
& $waitScript -Url "http://localhost:8800/api/v1/ready" -TimeoutSeconds 180
& $waitScript -Url "http://localhost:5173" -TimeoutSeconds 180

docker compose ps
docker compose logs backend --tail 50

docker compose down -v
Write-Host "Docker smoke test passed."
