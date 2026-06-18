param(
    [string]$EnvFile = ".env.production",
    [switch]$SkipBuild,
    [switch]$RunDrills,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path $Path)) {
        throw "$Name not found at: $Path"
    }
}

function Get-EnvMap {
    param([string]$Path)

    $envMap = @{}
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        if ($trimmed.StartsWith("#")) {
            continue
        }
        if ($trimmed -notmatch "^\s*([^=]+?)\s*=\s*(.*)\s*$") {
            continue
        }

        $key = $matches[1].Trim()
        $value = $matches[2].Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $envMap[$key] = $value
    }

    return $envMap
}

function Assert-EnvValuePresent {
    param(
        [hashtable]$EnvMap,
        [string]$Key
    )

    if (-not $EnvMap.ContainsKey($Key) -or [string]::IsNullOrWhiteSpace($EnvMap[$Key])) {
        throw "Required environment variable '$Key' is missing or empty in env file"
    }
}

function Invoke-PreflightChecks {
    param([string]$Path)

    $envMap = Get-EnvMap -Path $Path

    Assert-EnvValuePresent -EnvMap $envMap -Key "SENTINEL_DATABASE_URL"
    Assert-EnvValuePresent -EnvMap $envMap -Key "GF_SECURITY_ADMIN_USER"
    Assert-EnvValuePresent -EnvMap $envMap -Key "GF_SECURITY_ADMIN_PASSWORD"

    $blockedPasswords = @("change_me", "changeme", "password", "admin", "admin123", "default")
    $password = $envMap["GF_SECURITY_ADMIN_PASSWORD"]
    if ($blockedPasswords -contains $password.ToLower()) {
        throw "GF_SECURITY_ADMIN_PASSWORD is using a blocked placeholder value"
    }

    $smtpHost = ""
    if ($envMap.ContainsKey("SENTINEL_SMTP_HOST")) {
        $smtpHost = $envMap["SENTINEL_SMTP_HOST"]
    }
    if (-not [string]::IsNullOrWhiteSpace($smtpHost)) {
        Assert-EnvValuePresent -EnvMap $envMap -Key "SENTINEL_SMTP_USERNAME"
        Assert-EnvValuePresent -EnvMap $envMap -Key "SENTINEL_SMTP_PASSWORD"
        Assert-EnvValuePresent -EnvMap $envMap -Key "SENTINEL_ALERT_TO_EMAIL"
        Assert-EnvValuePresent -EnvMap $envMap -Key "SENTINEL_ALERT_FROM_EMAIL"
    }

    Write-Host "Preflight checks passed."
}

Write-Host "Starting production deployment..."

Assert-PathExists -Path $EnvFile -Name "Environment file"
Assert-PathExists -Path "docker-compose.yml" -Name "docker-compose.yml"
Assert-PathExists -Path "ops/go_live_verify.ps1" -Name "Go-live verification script"

if ($SkipPreflight) {
    Write-Host "WARNING: preflight checks were skipped by operator request."
}
else {
    Write-Host "Running preflight checks..."
    Invoke-PreflightChecks -Path $EnvFile
}

$composeArgs = @("--env-file", $EnvFile)

if ($SkipBuild) {
    Write-Host "Deploy mode: up -d (skip build)"
    docker compose @composeArgs up -d
}
else {
    Write-Host "Deploy mode: up --build -d"
    docker compose @composeArgs up --build -d
}

if ($LASTEXITCODE -ne 0) {
    throw "Deployment command failed"
}

Write-Host "Running go-live verification..."
& ./ops/go_live_verify.ps1

if ($LASTEXITCODE -ne 0) {
    throw "Go-live verification failed"
}

if ($RunDrills) {
    Assert-PathExists -Path "ops/run_all_drills.ps1" -Name "Drill script"
    Write-Host "Running post-deploy drills..."
    & ./ops/run_all_drills.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Drill validation failed"
    }
}

Write-Host "Production deployment completed successfully."
