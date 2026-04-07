param(
    [string]$action = "",
    [string]$text = "Beautiful digital watch",
    [string]$imageName = "image_1000076039_product_580161.jpg"
)

# Configuration
$GATEWAY_URL = "http://localhost:8000"
$INFERENCE_URL = "http://localhost:8001"
$TRAINING_URL = "http://localhost:8002"
$MLFLOW_URL = "http://localhost:5000"

# ===== FORMATTING FUNCTIONS =====
function Write-Header {
    param([string]$title)
    Write-Host "`n=== $title ===" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$msg)
    Write-Host "  $msg" -ForegroundColor Gray
}

function Write-Success {
    param([string]$msg)
    Write-Host "  SUCCESS: $msg" -ForegroundColor Green
}

function Write-Failed {
    param([string]$msg)
    Write-Host "  FAILED: $msg" -ForegroundColor Red
}

# ===== AUTHENTICATION =====
function Get-Token {
    param(
        [string]$username = "admin",
        [string]$password = "admin123"
    )
    
    Write-Header "Authentication"
    
    try {
        Write-Info "Requesting token for user: $username"
        
        $response = curl.exe -s -X POST "$GATEWAY_URL/token" `
            -H "Content-Type: application/x-www-form-urlencoded" `
            -d "username=$username&password=$password"
        
        Write-Host "Response: $response" -ForegroundColor Yellow
        
        if ($response) {
            try {
                $json = $response | ConvertFrom-Json
                if ($json.access_token) {
                    Write-Success "Token obtained: $($json.access_token.Substring(0,20))..."
                    return $json.access_token
                }
                else {
                    Write-Failed "No access_token in response"
                }
            }
            catch {
                Write-Failed "Failed to parse response: $_"
            }
        }
    }
    catch {
        Write-Failed "Token request failed: $_"
    }
    return $null
}

# ===== HEALTH CHECKS =====
function Test-Health {
    Write-Header "Health Checks"
    
    $services = @(
        @{ name = "Gateway"; url = "$GATEWAY_URL/health" },
        @{ name = "Inference"; url = "$INFERENCE_URL/health" },
        @{ name = "Training"; url = "$TRAINING_URL/health" },
        @{ name = "MLflow"; url = "$MLFLOW_URL" }
    )
    
    foreach ($service in $services) {
        Write-Info "$($service.name)..."
        try {
            $response = Invoke-RestMethod -Uri $service.url -Method Get -TimeoutSec 5
            if ($response.status -eq "ok" -or $response.PSObject.Properties.Name -contains "status") {
                Write-Success "$($service.name) is UP"
            }
            else {
                Write-Info "$($service.name) responded (non-standard format)"
            }
        }
        catch {
            Write-Failed "$($service.name) is DOWN or unreachable: $($_.Exception.Message)"
        }
    }
}

# ===== TEXT PREDICTION =====
function Test-TextPrediction {
    param(
        [string]$text,
        [string]$token
    )
    
    Write-Header "Text Prediction (SVM)"
    
    Write-Info "Predicting for: $text"
    
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        text = $text
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/predict/svm" `
            -Method Post `
            -Headers $headers `
            -Body $body
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
    }
    catch {
        Write-Failed "Prediction failed: $($_.Exception.Message)"
    }
}

# ===== IMAGE PREDICTION =====
function Test-ImagePrediction {
    param(
        [string]$imageName,
        [string]$token
    )
    
    Write-Header "Image Prediction (CNN)"
    
    Write-Info "Predicting for: $imageName"
    
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        image_path = $imageName
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/predict/cnn" `
            -Method Post `
            -Headers $headers `
            -Body $body
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
    }
    catch {
        Write-Failed "Prediction failed: $($_.Exception.Message)"
    }
}

# ===== MULTIMODAL PREDICTION =====
function Test-MultimodalPrediction {
    param(
        [string]$text,
        [string]$imageName,
        [string]$token
    )
    
    Write-Header "Multimodal Prediction"
    
    Write-Info "Predicting for text=$text, image=$imageName"
    
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        text = $text
        image_name = $imageName
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/predict/multimodal" `
            -Method Post `
            -Headers $headers `
            -Body $body
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
    }
    catch {
        Write-Failed "Prediction failed: $($_.Exception.Message)"
    }
}

# ===== SVM TRAINING =====
function Test-SVMTraining {
    param([string]$token)
    
    Write-Header "SVM Training"
    
    Write-Info "Starting SVM training..."
    
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/train/svm" `
            -Method Post `
            -Headers $headers
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
        return $response.task_id
    }
    catch {
        Write-Failed "Training failed: $($_.Exception.Message)"
    }
}

# ===== CNN TRAINING =====
function Test-CNNTraining {
    param([string]$token)
    
    Write-Header "CNN Training"
    
    Write-Info "Starting CNN training..."
    
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/train/cnn" `
            -Method Post `
            -Headers $headers
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
        return $response.task_id
    }
    catch {
        Write-Failed "Training failed: $($_.Exception.Message)"
    }
}

# ===== TRAINING STATUS =====
function Test-TrainingStatus {
    param(
        [string]$taskId,
        [string]$token
    )
    
    Write-Header "Training Status"
    
    Write-Info "Checking status for task: $taskId"
    
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$GATEWAY_URL/train/status/$taskId" `
            -Method Get `
            -Headers $headers
        
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Green
    }
    catch {
        Write-Failed "Status check failed: $($_.Exception.Message)"
    }
}

# ===== MAIN MENU =====
function Show-Menu {
    Write-Host "`n===== MLOps API Tests - Main Menu =====" -ForegroundColor Cyan
    Write-Host "1. Health Checks (all services)"
    Write-Host "2. Get token"
    Write-Host "3. Text prediction"
    Write-Host "4. Image prediction"
    Write-Host "5. Train SVM"
    Write-Host "6. Train CNN"
    Write-Host "7. Check training status"
    Write-Host "8. Run all tests"
    Write-Host "9. Exit"
    Write-Host ""
}

# ===== RUN ALL TESTS =====
function Run-AllTests {
    Write-Host "`n`n" -ForegroundColor White
    Write-Host "##############################################" -ForegroundColor Green
    Write-Host "#     RUNNING ALL TESTS IN SEQUENCE          #" -ForegroundColor Green
    Write-Host "##############################################" -ForegroundColor Green
    
    Write-Header "Health Checks"
    Test-Health
    Start-Sleep -Seconds 1
    
    Write-Header "Authentication"
    $token = Get-Token
    if (-not $token) {
        Write-Failed "Could not obtain token, aborting remaining tests"
        return
    }
    Start-Sleep -Seconds 1
    
    Write-Header "Text Prediction Test"
    Test-TextPrediction -text "beautiful digital watch" -token $token
    Start-Sleep -Seconds 1
    
    Write-Header "Image Prediction Test"
    Write-Info "Attempting image prediction..."
    Write-Info "Available images: check data/raw/image_train/ directory"
    Test-ImagePrediction -imageName "image_1000076039_product_580161.jpg" -token $token
    Start-Sleep -Seconds 1
    
    Write-Header "SVM Training"
    Write-Info "Starting SVM training (this may take a while)..."
    $svmResult = Test-SVMTraining -token $token
    Start-Sleep -Seconds 1
    
    Write-Header "CNN Training"
    Write-Info "Starting CNN training (this may take a while)..."
    $cnnResult = Test-CNNTraining -token $token
    Start-Sleep -Seconds 1
    
    Write-Host "`n" -ForegroundColor White
    Write-Host "##############################################" -ForegroundColor Green
    Write-Host "#     ALL TESTS COMPLETED                    #" -ForegroundColor Green
    Write-Host "##############################################" -ForegroundColor Green
}

# ===== MAIN PROGRAM =====
if ($action -eq "health") {
    Test-Health
} elseif ($action -eq "token") {
    Get-Token
} elseif ($action -eq "predict-text") {
    $token = Get-Token
    Test-TextPrediction -text $text -token $token
} elseif ($action -eq "predict-image") {
    $token = Get-Token
    Test-ImagePrediction -imageName $imageName -token $token
} elseif ($action -eq "predict-multimodal") {
    $token = Get-Token
    Test-MultimodalPrediction -text $text -imageName $imageName -token $token
} elseif ($action -eq "train-svm") {
    $token = Get-Token
    Test-SVMTraining -token $token
} elseif ($action -eq "train-cnn") {
    $token = Get-Token
    Test-CNNTraining -token $token
} elseif ($action -eq "status") {
    $token = Get-Token
    Test-TrainingStatus -taskId $text -token $token
} elseif ($action -eq "all") {
    Run-AllTests
} else {
    do {
        Show-Menu
        $choice = Read-Host "Choose option"
        
        switch ($choice) {
            "1" { Test-Health }
            "2" { 
                $user = Read-Host "User (admin/user/scientist) [admin]"
                if (-not $user) { $user = "admin" }
                $pass = Read-Host "Password" -AsSecureString
                $passPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($pass))
                Get-Token -username $user -password $passPlain
            }
            "3" { 
                $token = Get-Token
                $t = Read-Host "Text [Test product]"
                if (-not $t) { $t = "Test product" }
                Test-TextPrediction -text $t -token $token
            }
            "4" { 
                $token = Get-Token
                $img = Read-Host "Image name [image_1000076039_product_580161.jpg]"
                if (-not $img) { $img = "image_1000076039_product_580161.jpg" }
                Test-ImagePrediction -imageName $img -token $token
            }
            "5" { 
                $token = Get-Token
                $taskId = Test-SVMTraining -token $token
            }
            "6" { 
                $token = Get-Token
                $taskId = Test-CNNTraining -token $token
            }
            "7" { 
                $token = Get-Token
                $tid = Read-Host "Task ID"
                Test-TrainingStatus -taskId $tid -token $token
            }
            "8" { 
                Run-AllTests
            }
            "9" { 
                Write-Host "Goodbye!" -ForegroundColor Green
                exit
            }
            default { Write-Host "Invalid option - please choose 1-9" -ForegroundColor Red }
        }
    } while ($true)
}
