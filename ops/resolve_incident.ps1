param(
    [Parameter(Mandatory = $true)][int]$IncidentId,
    [string]$RootCause = "Resolved after mitigation",
    [string]$ApiBase = "http://localhost:8001"
)

$payload = @{ status = "resolved"; root_cause = $RootCause } | ConvertTo-Json
Invoke-RestMethod -Method Patch -Uri "$ApiBase/api/incidents/$IncidentId" -ContentType "application/json" -Body $payload
Write-Host "Incident $IncidentId resolved"
