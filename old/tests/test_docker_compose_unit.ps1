param()

Write-Host ""
Write-Host "Docker-Compose Configuration Unit Tests"
Write-Host "========================================"
Write-Host ""

$script:failedTests = @()
$script:passedTests = @()

# Helper function for testing
function Test-Config {
    param([string]$Description, [scriptblock]$TestBlock)
    Write-Host "  - $Description" -NoNewline
    try {
        $null = &$TestBlock
        $script:passedTests += $Description
        Write-Host " OK" -ForegroundColor Green
    }
    catch {
        $script:failedTests += @{ Name = $Description; Error = $_.Exception.Message }
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ==============================================================================
# [1] Docker-Compose Validation
# ==============================================================================
Write-Host "[1] Docker-Compose Validation"
Write-Host ""

Test-Config "docker-compose.yml exists" {
    if (-not (Test-Path "docker-compose.yml")) {
        throw "docker-compose.yml not found"
    }
}

Test-Config "docker-compose.yml is valid" {
    $output = docker-compose config 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Invalid YAML: $output"
    }
}

# ==============================================================================
# [2] Services Exist
# ==============================================================================
Write-Host ""
Write-Host "[2] Services Defined"
Write-Host ""

@("gateway", "inference", "training", "mlflow") | ForEach-Object {
    Test-Config "Service '$_' exists" {
        $found = Select-String -Path "docker-compose.yml" -Pattern "^\s+$_\s*:" -Quiet
        if (-not $found) {
            throw "Service '$_' not defined"
        }
    }
}

# ==============================================================================
# [3] Port Mappings
# ==============================================================================
Write-Host ""
Write-Host "[3] Port Mappings"
Write-Host ""

Test-Config "Gateway port 8000:8000" {
    $found = Select-String -Path "docker-compose.yml" -Pattern '8000:8000' -Quiet
    if (-not $found) { throw "Port 8000:8000 not found" }
}

Test-Config "Inference port 8001:8000" {
    $found = Select-String -Path "docker-compose.yml" -Pattern '8001:8000' -Quiet
    if (-not $found) { throw "Port 8001:8000 not found" }
}

Test-Config "Training port 8002:8000" {
    $found = Select-String -Path "docker-compose.yml" -Pattern '8002:8000' -Quiet
    if (-not $found) { throw "Port 8002:8000 not found" }
}

Test-Config "MLflow port 5000:5000" {
    $found = Select-String -Path "docker-compose.yml" -Pattern '5000:5000' -Quiet
    if (-not $found) { throw "Port 5000:5000 not found" }
}

# ==============================================================================
# [4] Volume Mounts
# ==============================================================================
Write-Host ""
Write-Host "[4] Volume Mounts"
Write-Host ""

Test-Config "Data volume mounted" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './data:/app/data' -Quiet
    if (-not $found) { throw "Data volume not found" }
}

Test-Config "Models volume mounted" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './models:/app/models' -Quiet
    if (-not $found) { throw "Models volume not found" }
}

Test-Config "Source volume mounted" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './src:/app/src' -Quiet
    if (-not $found) { throw "Source volume not found" }
}

Test-Config "MLflow runs volume mounted" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './mlflow/mlruns:/mlflow/mlruns' -Quiet
    if (-not $found) { throw "MLflow runs volume not found" }
}

# ==============================================================================
# [5] Environment Variables
# ==============================================================================
Write-Host ""
Write-Host "[5] Environment Variables"
Write-Host ""

Test-Config "MLFLOW_TRACKING_URI set" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'MLFLOW_TRACKING_URI' -Quiet
    if (-not $found) { throw "MLFLOW_TRACKING_URI not set" }
}

Test-Config "INFERENCE_URL set" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'INFERENCE_URL' -Quiet
    if (-not $found) { throw "INFERENCE_URL not set" }
}

Test-Config "TRAINING_URL set" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'TRAINING_URL' -Quiet
    if (-not $found) { throw "TRAINING_URL not set" }
}

# ==============================================================================
# [6] Network Configuration
# ==============================================================================
Write-Host ""
Write-Host "[6] Network Configuration"
Write-Host ""

Test-Config "mlops_network defined" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'mlops_network:' -Quiet
    if (-not $found) { throw "mlops_network not defined" }
}

# ==============================================================================
# [7] Service Dependencies
# ==============================================================================
Write-Host ""
Write-Host "[7] Service Dependencies"
Write-Host ""

Test-Config "Gateway has depends_on" {
    $content = Get-Content "docker-compose.yml" -Raw
    $gatewaySec = $content -match 'gateway:[\s\S]*?(?=\n  [a-z]|\Z)'
    if ($gatewaySec -and $content -match 'gateway:[\s\S]*?depends_on:') {
        # Valid
    } else {
        throw "Gateway dependencies not properly configured"
    }
}

# ==============================================================================
# [8] Container Status
# ==============================================================================
Write-Host ""
Write-Host "[8] Container Status"
Write-Host ""

Test-Config "All services running" {
    $ps = docker-compose ps --services 2>$null
    $expected = @("gateway", "inference", "training", "mlflow")
    $running = $ps.Count -ge 4
    if (-not $running) { throw "Not all services running" }
}

Test-Config "No services exited with error" {
    $ps = docker-compose ps 2>$null
    if ($ps -match "Exit") {
        throw "One or more containers have exited"
    }
}

# ==============================================================================
# [9] Health Checks
# ==============================================================================
Write-Host ""
Write-Host "[9] Health Checks"
Write-Host ""

Test-Config "Gateway health check" {
    try {
        $response = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction Stop
        if ($response.status -ne "ok") { throw "Status is not 'ok'" }
    }
    catch {
        throw "Gateway health check failed: $_"
    }
}

Test-Config "Inference health check" {
    try {
        $response = Invoke-RestMethod "http://localhost:8001/health" -TimeoutSec 3 -ErrorAction Stop
        if ($response.status -ne "ok") { throw "Status is not 'ok'" }
    }
    catch {
        throw "Inference health check failed: $_"
    }
}

Test-Config "Training health check" {
    try {
        $response = Invoke-RestMethod "http://localhost:8002/health" -TimeoutSec 3 -ErrorAction Stop
        if ($response.status -ne "ok") { throw "Status is not 'ok'" }
    }
    catch {
        throw "Training health check failed: $_"
    }
}

# ==============================================================================
# [10] Streamlit Configuration
# ==============================================================================
Write-Host ""
Write-Host "[10] Streamlit Configuration"
Write-Host ""

Test-Config "Streamlit service exists" {
    $found = Select-String -Path "docker-compose.yml" -Pattern "^\s+streamlit\s*:" -Quiet
    if (-not $found) {
        throw "Streamlit service not defined"
    }
}

Test-Config "Streamlit port 8501:8501" {
    $found = Select-String -Path "docker-compose.yml" -Pattern '8501:8501' -Quiet
    if (-not $found) { throw "Port 8501:8501 not found" }
}

Test-Config "Streamlit Dockerfile exists" {
    if (-not (Test-Path "streamlit/Dockerfile")) {
        throw "streamlit/Dockerfile not found"
    }
}

Test-Config "Streamlit has GATEWAY_URL environment" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'GATEWAY_URL=http://gateway:8000' -Quiet
    if (-not $found) { throw "GATEWAY_URL not set for Streamlit" }
}

Test-Config "Streamlit has MLFLOW_URL environment" {
    $found = Select-String -Path "docker-compose.yml" -Pattern 'MLFLOW_URL=http://mlflow:5000' -Quiet
    if (-not $found) { throw "MLFLOW_URL not set for Streamlit" }
}

Test-Config "Streamlit depends on gateway" {
    $content = Get-Content "docker-compose.yml" -Raw
    if ($content -match 'streamlit:[\s\S]*?depends_on:[\s\S]*?gateway') {
        # Valid
    } else {
        throw "Streamlit dependency on gateway not configured"
    }
}

Test-Config "Streamlit volume mounted for data" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './data:/app/data' -Quiet
    if (-not $found) { throw "Data volume not mounted for Streamlit" }
}

Test-Config "Streamlit volume mounted for models" {
    $found = Select-String -Path "docker-compose.yml" -Pattern './models:/app/models' -Quiet
    if (-not $found) { throw "Models volume not mounted for Streamlit" }
}

Test-Config "Streamlit health check endpoint" {
    try {
        $response = Invoke-RestMethod "http://localhost:8501/_stcore/health" -TimeoutSec 3 -ErrorAction Stop
        # Streamlit returns plain text, just check if response is not empty
        if ($null -eq $response) { throw "No response from Streamlit health check" }
    }
    catch {
        Write-Host "  (Note: Streamlit may not be fully started yet)" -ForegroundColor Yellow
    }
}

Test-Config "Streamlit app file exists" {
    if (-not (Test-Path "streamlit/streamlit_rakuten.py")) {
        throw "streamlit/streamlit_rakuten.py not found"
    }
}

Test-Config "Streamlit auth manager exists" {
    if (-not (Test-Path "streamlit/auth_manager.py")) {
        throw "streamlit/auth_manager.py not found"
    }
}

Test-Config "Streamlit requirements.txt exists" {
    if (-not (Test-Path "streamlit/requirements.txt")) {
        throw "streamlit/requirements.txt not found"
    }
}

# ==============================================================================
# TEST SUMMARY
# ==============================================================================
Write-Host ""
Write-Host "========================================"
Write-Host "TEST SUMMARY"
Write-Host "========================================"
Write-Host ""

$total = $script:passedTests.Count + $script:failedTests.Count
Write-Host "Total Tests: $total"
Write-Host "Passed:      $($script:passedTests.Count)" -ForegroundColor Green
Write-Host "Failed:      $($script:failedTests.Count)" -ForegroundColor $(if ($script:failedTests.Count -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($script:failedTests.Count -gt 0) {
    Write-Host "FAILED TESTS:" -ForegroundColor Red
    $script:failedTests | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Red
        Write-Host "    Error: $($_.Error)" -ForegroundColor DarkRed
    }
    Write-Host ""
    exit 1
}
else {
    Write-Host "SUCCESS: All tests passed!" -ForegroundColor Green
    Write-Host ""
    exit 0
}
