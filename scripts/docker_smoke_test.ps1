#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    } else {
        throw "Missing .env and .env.example; cannot run docker smoke test."
    }
}

Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        Set-Item -Path "env:$($Matches[1])" -Value $Matches[2]
    }
}

$backendPort = if ($env:BACKEND_HOST_PORT) { $env:BACKEND_HOST_PORT } else { "8800" }
$frontendPort = if ($env:FRONTEND_HOST_PORT) { $env:FRONTEND_HOST_PORT } else { "5173" }
$backendBase = "http://localhost:$backendPort"

docker compose config | Out-Null
docker compose build
docker compose up -d

$waitScript = Join-Path $PSScriptRoot "wait_for_http.ps1"
& $waitScript -Url "$backendBase/health" -TimeoutSeconds 180
& $waitScript -Url "$backendBase/ready" -TimeoutSeconds 180
& $waitScript -Url "http://localhost:$frontendPort" -TimeoutSeconds 180

docker compose ps
docker compose logs backend --tail 50

docker compose down -v
Write-Host "Docker smoke test passed."
