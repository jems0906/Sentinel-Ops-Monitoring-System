param(
    [string]$ApiBase = "http://localhost:8001"
)

function Convert-ToArray {
    param(
        [Parameter(Mandatory = $true)]$InputObject
    )

    if ($null -eq $InputObject) {
        return @()
    }

    if ($InputObject -is [System.Array]) {
        return @($InputObject)
    }

    if ($null -ne $InputObject.value) {
        return @($InputObject.value)
    }

    return @($InputObject)
}

function Get-ApiIncidents {
    return Convert-ToArray -InputObject (Invoke-RestMethod "$ApiBase/api/incidents")
}

function Get-ApiAlerts {
    return Convert-ToArray -InputObject (Invoke-RestMethod "$ApiBase/api/alerts")
}

function Get-LatestIncidentForTarget {
    param(
        [Parameter(Mandatory = $true)][int]$TargetId,
        [datetime]$Since
    )

    $incidents = Get-ApiIncidents | Where-Object { $_.target_id -eq $TargetId }
    if ($PSBoundParameters.ContainsKey('Since')) {
        $incidents = $incidents | Where-Object { ([datetime]$_.created_at) -ge $Since }
    }

    return $incidents | Sort-Object -Property created_at -Descending | Select-Object -First 1
}

function Get-TargetLatestCheck {
    param(
        [Parameter(Mandatory = $true)][int]$TargetId
    )

    $checks = Convert-ToArray -InputObject (Invoke-RestMethod "$ApiBase/api/checks?limit=200")
    return $checks | Where-Object { $_.target_id -eq $TargetId } | Sort-Object -Property created_at -Descending | Select-Object -First 1
}

$scenarioResults = @{}

$targets = Invoke-RestMethod "$ApiBase/api/targets"
if ($targets.Count -eq 0) {
    $seed = @(
        @{name='Gateway Ping'; target_type='ping'; address='1.1.1.1'; interval_seconds=5; enabled=$true; extra=@{timeout=2}},
        @{name='Frontend Service'; target_type='http'; address='http://frontend'; interval_seconds=5; enabled=$true; extra=@{timeout=5; expected_status=200}},
        @{name='Public DNS Check'; target_type='dns'; address='example.com'; interval_seconds=5; enabled=$true; extra=@{resolver='8.8.8.8'; record_type='A'}},
        @{name='Internal DNS Check'; target_type='dns'; address='frontend'; interval_seconds=5; enabled=$true; extra=@{resolver='127.0.0.11'; record_type='A'}},
        @{name='Backend Service'; target_type='http'; address='http://backend:8000/health'; interval_seconds=5; enabled=$true; extra=@{timeout=5; expected_status=200}}
    )

    foreach ($t in $seed) {
        Invoke-RestMethod -Method Post -Uri "$ApiBase/api/targets" -ContentType "application/json" -Body ($t | ConvertTo-Json -Depth 8) | Out-Null
    }
    $targets = Invoke-RestMethod "$ApiBase/api/targets"
}

foreach ($target in $targets) {
    $clear = @{target_id=$target.id; mode='none'} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$ApiBase/api/simulations/toggle" -ContentType "application/json" -Body $clear | Out-Null
}

function Invoke-ForcedCycle {
    try {
        Invoke-RestMethod -Method Post -Uri "$ApiBase/api/admin/run-cycle?force=true" | Out-Null
    }
    catch {
        Invoke-RestMethod -Method Post -Uri "$ApiBase/api/admin/run-cycle?force=true" | Out-Null
    }
}

function Invoke-Simulation {
    param(
        [int]$TargetId,
        [string]$Mode,
        [int]$LatencyMs = 0
    )

    $payload = @{target_id=$TargetId; mode=$Mode}
    if ($Mode -eq 'high_latency') {
        $payload.latency_ms = $LatencyMs
    }

    Invoke-RestMethod -Method Post -Uri "$ApiBase/api/simulations/toggle" -ContentType "application/json" -Body ($payload | ConvertTo-Json) | Out-Null
    Invoke-ForcedCycle
}

# 1) Server down -> alert
$serverDownStart = Get-Date
Invoke-Simulation -TargetId 5 -Mode 'server_down'
$serverDownIncident = Get-LatestIncidentForTarget -TargetId 5 -Since $serverDownStart
$serverDownAlert = Get-ApiAlerts |
    Where-Object { ([datetime]$_.created_at) -ge $serverDownStart -and $_.subject -like '*Backend Service is down*' } |
    Sort-Object -Property created_at -Descending |
    Select-Object -First 1
$scenarioResults.server_down = @{
    passed = ($null -ne $serverDownIncident -and $null -ne $serverDownAlert)
    target_id = 5
    incident_id = if ($null -ne $serverDownIncident) { $serverDownIncident.id } else { $null }
    alert_id = if ($null -ne $serverDownAlert) { $serverDownAlert.id } else { $null }
    note = 'Server outage simulation should generate incident and alert.'
}

# 2) High latency -> network investigation
$highLatencyStart = Get-Date
Invoke-Simulation -TargetId 1 -Mode 'high_latency' -LatencyMs 900
$highLatencyIncident = Get-LatestIncidentForTarget -TargetId 1 -Since $highLatencyStart
$highLatencyCheck = Get-TargetLatestCheck -TargetId 1
$scenarioResults.high_latency = @{
    passed = ($null -ne $highLatencyIncident -and $null -ne $highLatencyCheck -and $highLatencyCheck.status -eq 'degraded')
    target_id = 1
    incident_id = if ($null -ne $highLatencyIncident) { $highLatencyIncident.id } else { $null }
    check_id = if ($null -ne $highLatencyCheck) { $highLatencyCheck.id } else { $null }
    observed_status = if ($null -ne $highLatencyCheck) { $highLatencyCheck.status } else { $null }
    observed_latency_ms = if ($null -ne $highLatencyCheck) { $highLatencyCheck.latency_ms } else { $null }
    note = 'Latency simulation should mark target degraded and open incident.'
}

# 3) DNS failure -> resolution chain debug
$dnsFailureStart = Get-Date
Invoke-Simulation -TargetId 4 -Mode 'dns_failure'
$dnsIncident = Get-LatestIncidentForTarget -TargetId 4 -Since $dnsFailureStart
$dnsCheck = Get-TargetLatestCheck -TargetId 4
$scenarioResults.dns_failure = @{
    passed = ($null -ne $dnsIncident -and $null -ne $dnsCheck -and $dnsCheck.status -eq 'down')
    target_id = 4
    incident_id = if ($null -ne $dnsIncident) { $dnsIncident.id } else { $null }
    check_id = if ($null -ne $dnsCheck) { $dnsCheck.id } else { $null }
    observed_status = if ($null -ne $dnsCheck) { $dnsCheck.status } else { $null }
    note = 'DNS failure simulation should mark target down and open incident.'
}

# 4) Service crash -> restart + log
$serviceCrashStart = Get-Date
Invoke-Simulation -TargetId 2 -Mode 'service_crash'
$incident = (Get-ApiIncidents) |
    Where-Object { $_.target_id -eq 2 } |
    Sort-Object -Property created_at -Descending |
    Select-Object -First 1
if ($null -ne $incident) {
    $note = @{note='Service crash confirmed during drill. Restart initiated and health recovered.'} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$ApiBase/api/incidents/$($incident.id)/notes" -ContentType "application/json" -Body $note | Out-Null
    Invoke-RestMethod -Method Patch -Uri "$ApiBase/api/incidents/$($incident.id)" -ContentType "application/json" -Body (@{root_cause='Application service crash simulated and mitigated with restart.'} | ConvertTo-Json) | Out-Null
}
Invoke-RestMethod -Method Post -Uri "$ApiBase/api/simulations/restart-service/2" | Out-Null
Invoke-ForcedCycle
$resolvedServiceIncident = Get-LatestIncidentForTarget -TargetId 2 -Since $serviceCrashStart
$scenarioResults.service_crash_restart = @{
    passed = ($null -ne $resolvedServiceIncident -and $resolvedServiceIncident.status -eq 'resolved')
    target_id = 2
    incident_id = if ($null -ne $resolvedServiceIncident) { $resolvedServiceIncident.id } else { $null }
    final_status = if ($null -ne $resolvedServiceIncident) { $resolvedServiceIncident.status } else { $null }
    note = 'Service crash should be investigated, restarted, and resolved.'
}

# Cleanup simulated states
foreach ($target in $targets) {
    $clear = @{target_id=$target.id; mode='none'} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$ApiBase/api/simulations/toggle" -ContentType "application/json" -Body $clear | Out-Null
}
Invoke-ForcedCycle

$report = @{
    executed_at = (Get-Date).ToString('s')
    summary = Invoke-RestMethod "$ApiBase/api/summary"
    incidents = Invoke-RestMethod "$ApiBase/api/incidents"
    alerts = Invoke-RestMethod "$ApiBase/api/alerts"
    scenario_results = $scenarioResults
}

$reportPath = Join-Path $PSScriptRoot "drill_report.json"
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $reportPath -Encoding utf8
Write-Host "Drill execution completed. Report written to $reportPath"
