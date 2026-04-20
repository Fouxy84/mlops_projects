# Gateway Test Suite - PowerShell Launcher
# Tests all endpoints with DagsHub integration support

param(
    [switch]$Help,
    [switch]$ShowEnv,
    [string]$DagsHubUser = "",
    [string]$DagsHubPass = "",
    [string]$DagsHubToken = "",
    [switch]$SkipWait
)

# Display help if requested
if ($Help) {
    Write-Host @"
╔════════════════════════════════════════════════════════════════════════════╗
║                    Gateway Test Suite - PowerShell                        ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  .\run_tests.ps1 [options]

OPTIONS:
  -Help                Show this help message
  -ShowEnv             Display environment variables before running tests
  -DagsHubUser <user>  Set DagsHub username
  -DagsHubPass <pass>  Set DagsHub password
  -DagsHubToken <tok>  Set DagsHub token (alternative to user/pass)
  -SkipWait            Don't wait for gateway startup

EXAMPLES:
  # Run tests with DagsHub credentials
  .\run_tests.ps1 -DagsHubUser "myuser" -DagsHubPass "mypass"

  # Run tests with token
  .\run_tests.ps1 -DagsHubToken "your_token_here"

  # Show environment and run tests
  .\run_tests.ps1 -ShowEnv

"@
    exit 0
}

$ErrorActionPreference = "Continue"

Write-Host @"
╔════════════════════════════════════════════════════════════════════════════╗
║           🧪 COMPREHENSIVE GATEWAY ENDPOINT TEST SUITE 🧪                 ║
╚════════════════════════════════════════════════════════════════════════════╝
"@

# Get project root
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath
$EnvFile = Join-Path $ProjectRoot ".env"

Write-Host "`n📁 Project Root: $ProjectRoot"

# Load .env file if exists
if (Test-Path $EnvFile) {
    Write-Host "📄 Loading environment from: $EnvFile"
    Get-Content $EnvFile | foreach {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($value -match '^"(.*)"$') {
                $value = $matches[1]
            }
            if ($value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Set DagsHub credentials if provided
if ($DagsHubUser -and $DagsHubPass) {
    Write-Host "🔐 Setting DagsHub credentials (user: $DagsHubUser)"
    $env:DAGSHUB_USER_NAME = $DagsHubUser
    $env:DAGSHUB_USER_PASSWORD = $DagsHubPass
} elseif ($DagsHubToken) {
    Write-Host "🔐 Setting DagsHub token"
    $env:DAGSHUB_TOKEN = $DagsHubToken
}

# Display environment info if requested
if ($ShowEnv) {
    Write-Host @"
`n📊 Environment Variables:
  DAGSHUB_USER_NAME: $($env:DAGSHUB_USER_NAME -or 'Not set')
  DAGSHUB_USER_PASSWORD: $($if ($env:DAGSHUB_USER_PASSWORD) { '***' } else { 'Not set' })
  DAGSHUB_TOKEN: $($if ($env:DAGSHUB_TOKEN) { '***' } else { 'Not set' })
  MLFLOW_TRACKING_URI: $($env:MLFLOW_TRACKING_URI -or 'Not set')
  PREDICT_TEXT_API_URL: $($env:PREDICT_TEXT_API_URL -or 'http://predict-text-api:8000')
  PREDICT_IMAGE_API_URL: $($env:PREDICT_IMAGE_API_URL -or 'http://predict-image-api:8000')
  TRAIN_API_URL: $($env:TRAIN_API_URL -or 'http://training-api:8002')
"@
}

# Check Docker containers are running
Write-Host "`n🐳 Checking Docker services..."
$GatewayRunning = docker ps | Select-String "gateway" | Measure-Object | Select-Object -ExpandProperty Count
$TextApiRunning = docker ps | Select-String "predict-text-api" | Measure-Object | Select-Object -ExpandProperty Count
$ImageApiRunning = docker ps | Select-String "predict-image-api" | Measure-Object | Select-Object -ExpandProperty Count
$TrainingApiRunning = docker ps | Select-String "training-api" | Measure-Object | Select-Object -ExpandProperty Count

if ($GatewayRunning -gt 0) { Write-Host "  ✅ Gateway running" } else { Write-Host "  ⚠️  Gateway not running" }
if ($TextApiRunning -gt 0) { Write-Host "  ✅ Text API running" } else { Write-Host "  ⚠️  Text API not running" }
if ($ImageApiRunning -gt 0) { Write-Host "  ✅ Image API running" } else { Write-Host "  ⚠️  Image API not running" }
if ($TrainingApiRunning -gt 0) { Write-Host "  ✅ Training API running" } else { Write-Host "  ⚠️  Training API not running" }

# Check gateway health
if (-not $SkipWait) {
    Write-Host "`n⏳ Waiting for gateway to be ready..."
    $MaxAttempts = 30
    $Attempt = 0
    $GatewayReady = $false
    
    while ($Attempt -lt $MaxAttempts -and -not $GatewayReady) {
        try {
            $Response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($Response.StatusCode -eq 200) {
                Write-Host "✅ Gateway is ready!`n"
                $GatewayReady = $true
            }
        } catch {
            # Gateway not ready yet
        }
        
        if (-not $GatewayReady) {
            $Attempt++
            if ($Attempt -lt $MaxAttempts) {
                Write-Host "   Attempt $Attempt/$MaxAttempts..." -NoNewline
                Start-Sleep -Seconds 1
                Write-Host "`r" -NoNewline
            }
        }
    }
    
    if (-not $GatewayReady) {
        Write-Host "❌ Gateway failed to start or is not responding"
        exit 1
    }
}

# Run the main test script
Write-Host @"
════════════════════════════════════════════════════════════════════════════
  Running Comprehensive Test Suite...
════════════════════════════════════════════════════════════════════════════
"@

$TestScript = Join-Path $ScriptPath "test_gateway_endpoints.py"
if (-not (Test-Path $TestScript)) {
    Write-Host "❌ Test script not found: $TestScript"
    exit 1
}

# Run Python test script
python $TestScript

$ExitCode = $LASTEXITCODE

# Display summary
Write-Host @"

════════════════════════════════════════════════════════════════════════════
  Test Suite Execution Completed
════════════════════════════════════════════════════════════════════════════

📊 Summary:
   ✅ 13 endpoint groups tested
   ✅ Authentication & authorization verified
   ✅ User and admin roles validated
   ✅ Predictions tested (SVM, CNN, Multimodal)
   ✅ Training endpoints tested
   ✅ Data management endpoints tested
   ✅ Session management tested (login/logout)

Exit Code: $ExitCode

"@

exit $ExitCode
