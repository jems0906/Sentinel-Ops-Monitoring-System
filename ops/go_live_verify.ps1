param(
    [string]$BackendHealthUrl = "http://localhost:8001/health",
    [string]$FrontendUrl = "http://localhost:5173",
    [string]$PrometheusHealthUrl = "http://localhost:9090/-/healthy",
    [string]$GrafanaHealthUrl = "http://localhost:3000/api/health",
    [string]$AlertmanagerUrl = "http://localhost:9093"
)

$ErrorActionPreference = "Stop"

function Assert-Http200 {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -ne 200) {
            throw "$Name returned status $($response.StatusCode)"
        }
        Write-Host "[PASS] $Name => 200"
    }
    catch {
        Write-Host "[FAIL] $Name => $($_.Exception.Message)"
        throw
    }
}

function Assert-BackendJson {
    param([string]$Url)

    try {
        $obj = Invoke-RestMethod -Uri $Url -TimeoutSec 10
        if ($obj.status -ne "ok") {
            throw "Backend health payload is not expected: $($obj | ConvertTo-Json -Compress)"
        }
        Write-Host "[PASS] Backend health payload status=ok"
    }
    catch {
        Write-Host "[FAIL] Backend health payload => $($_.Exception.Message)"
        throw
    }
}

Write-Host "Starting go-live verification..."

Assert-BackendJson -Url $BackendHealthUrl
Assert-Http200 -Name "Frontend" -Url $FrontendUrl
Assert-Http200 -Name "Prometheus" -Url $PrometheusHealthUrl
Assert-Http200 -Name "Grafana" -Url $GrafanaHealthUrl
Assert-Http200 -Name "Alertmanager" -Url $AlertmanagerUrl

Write-Host "Go-live verification passed."
