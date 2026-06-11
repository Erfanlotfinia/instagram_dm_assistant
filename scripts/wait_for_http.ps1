param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$TimeoutSeconds = 120,
    [int]$IntervalSeconds = 2
)

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            Write-Host "OK: $Url"
            exit 0
        }
    } catch {
        # retry
    }
    Start-Sleep -Seconds $IntervalSeconds
}

Write-Error "Timeout waiting for $Url"
exit 1
