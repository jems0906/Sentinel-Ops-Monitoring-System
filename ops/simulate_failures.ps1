param(
    [Parameter(Mandatory = $true)][string]$Mode,
    [int]$TargetId = 1,
    [int]$LatencyMs = 950,
    [string]$ApiBase = "http://localhost:8001"
)

$payload = @{ target_id = $TargetId; mode = $Mode }
if ($Mode -eq "high_latency") {
    $payload.latency_ms = $LatencyMs
}

Invoke-RestMethod -Method Post -Uri "$ApiBase/api/simulations/toggle" -ContentType "application/json" -Body ($payload | ConvertTo-Json)
Write-Host "Simulation $Mode applied to target $TargetId"
