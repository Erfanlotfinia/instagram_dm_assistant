#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$Service,

    [int]$TimeoutSeconds = 240,
    [int]$IntervalSeconds = 2
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$lastStatus = "starting"

while ((Get-Date) -lt $deadline) {
    $cid = (docker compose ps -q $Service 2>$null | Select-Object -First 1).Trim()
    if (-not $cid) {
        throw "Service $Service is not running"
    }

    $lastStatus = (docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $cid).Trim()

    switch ($lastStatus) {
        "healthy" {
            Write-Host "OK: $Service is healthy"
            return
        }
        "running" {
            $hasHealth = (docker inspect --format '{{if .State.Health}}1{{end}}' $cid).Trim()
            if (-not $hasHealth) {
                Write-Host "OK: $Service is running"
                return
            }
        }
        { $_ -in @("exited", "dead") } {
            docker compose logs $Service --tail 100
            throw "$Service container stopped (status=$lastStatus)"
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}

docker compose logs $Service --tail 100
throw "Timeout waiting for $Service to become healthy (last status: $lastStatus)"
