param(
    [Parameter(Mandatory = $true)][int]$IncidentId,
    [Parameter(Mandatory = $true)][string]$Note,
    [string]$ApiBase = "http://localhost:8001"
)

$payload = @{ note = $Note } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$ApiBase/api/incidents/$IncidentId/notes" -ContentType "application/json" -Body $payload
Write-Host "Note added to incident $IncidentId"
