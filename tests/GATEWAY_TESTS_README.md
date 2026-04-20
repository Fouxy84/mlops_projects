# 🧪 Gateway Endpoint Test Suite

Comprehensive test suite for all gateway endpoints with DagsHub integration support.

## 📋 Endpoints Tested

### 1. **Health & Status** (No Auth Required)
- ✅ `GET /health` - Gateway health check
- ✅ `GET /` - Root endpoint with service info
- ✅ `GET /metrics` - Prometheus metrics

### 2. **Authentication** (Session Management)
- ✅ `POST /login` - Login with credentials
- ✅ `GET /me` - Get current user info
- ✅ `POST /logout` - Logout and clear session

### 3. **Predictions** (User Auth Required)
- ✅ `POST /predict/svm` - Text classification (SVM)
- ✅ `POST /predict/cnn` - Image classification (CNN)
- ✅ `POST /predict/multimodal` - Combined text + image prediction

### 4. **Training** (Admin Auth Required)
- ✅ `POST /train/svm` - Train text model
- ✅ `POST /train/cnn` - Train image model
- ✅ `POST /reload/svm` - Reload text model from MLflow/local
- ✅ `POST /reload/cnn` - Reload image model from MLflow/local

### 5. **Data Management** (Admin Auth Required)
- ✅ `GET /data/check-updates` - Check for new training data
- ✅ `POST /data/check-updates/baseline` - Set baseline for data
- ✅ `POST /data/check-updates/retrain` - Auto-retrain on data changes

### 6. **System Info** (User Auth Required)
- ✅ `GET /info` - Get all services health & model info

## 🚀 Running Tests

### Quick Start
```powershell
cd C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects
python tests/test_gateway_endpoints.py
```

### With PowerShell Script (Recommended)
```powershell
# Basic run
.\tests\run_tests.ps1

# With DagsHub credentials
.\tests\run_tests.ps1 -DagsHubUser "your_username" -DagsHubPass "your_password"

# With DagsHub token
.\tests\run_tests.ps1 -DagsHubToken "your_token_here"

# Show environment variables
.\tests\run_tests.ps1 -ShowEnv

# Skip gateway wait
.\tests\run_tests.ps1 -SkipWait
```

### With Python Script
```bash
# Basic run
python tests/run_gateway_tests.py

# With environment variables
$env:DAGSHUB_USER_NAME="your_username"
$env:DAGSHUB_USER_PASSWORD="your_password"
python tests/run_gateway_tests.py
```

## 🔐 DagsHub Configuration

Tests support DagsHub integration for remote model management. Set credentials in one of these ways:

### Option 1: Environment Variables
```powershell
$env:DAGSHUB_USER_NAME = "your_dagshub_username"
$env:DAGSHUB_USER_PASSWORD = "your_dagshub_password"
```

### Option 2: .env File
Create `.env` file in project root:
```
DAGSHUB_USER_NAME=your_dagshub_username
DAGSHUB_USER_PASSWORD=your_dagshub_password
MLFLOW_TRACKING_URI=https://dagshub.com/your_dagshub_username/your_repo/mlflow
```

### Option 3: Direct Parameter (PowerShell)
```powershell
.\tests\run_tests.ps1 -DagsHubUser "username" -DagsHubPass "password"
```

## 📊 Test Output

Each test section displays:
- ✅ **Success indicators** - Green checkmarks for passed tests
- ❌ **Failure indicators** - Red crosses for failed tests
- 📝 **HTTP Status codes** - Response status (200, 401, 403, 500, etc.)
- 📦 **Response data** - JSON responses from endpoints

### Example Output
```
================================================================================
  4️⃣  TEST: AUTHENTICATION
================================================================================

📍 Invalid credentials:
❌ Invalid login (should fail) ✅ 401

📍 Admin login:
✅ Admin login (Status: 200)
   Response: {'status': 'logged_in', 'username': 'admin', 'role': 'admin', ...}

📍 User login:
✅ User login (Status: 200)
   Response: {'status': 'logged_in', 'username': 'user', 'role': 'user', ...}
```

## 🧪 Test Cases

### Authentication Tests
- ✅ Invalid credentials rejection (401)
- ✅ Admin login success (200)
- ✅ User login success (200)
- ✅ Session management

### Authorization Tests
- ✅ User cannot access admin endpoints (403)
- ✅ Admin can access admin endpoints (200)
- ✅ Unauthenticated access rejected (401)

### Prediction Tests
- ✅ SVM predictions with text input
- ✅ CNN predictions with image path
- ✅ Multimodal predictions (text + image)
- ✅ MLflow model loading with fallback to local models

### Training Tests
- ✅ Admin-only training endpoints
- ✅ Model reload from MLflow/local storage
- ✅ Training API communication

### Data Management Tests
- ✅ Data change detection
- ✅ Baseline state management
- ✅ Auto-retraining on data changes

## ⚙️ Configuration

### Environment Variables
```
PREDICT_TEXT_API_URL=http://predict-text-api:8000
PREDICT_IMAGE_API_URL=http://predict-image-api:8000
TRAIN_API_URL=http://training-api:8002
MLFLOW_TRACKING_URI=https://dagshub.com/.../mlflow (optional)
DAGSHUB_USER_NAME=your_username (optional)
DAGSHUB_USER_PASSWORD=your_password (optional)
DAGSHUB_TOKEN=your_token (optional)
```

### Test Data
- **Test Image**: `image_1000076039_product_580161.jpg`
- **Test Text**: "Ce livre est super intéressant pour apprendre les sciences"

### User Credentials
- **Admin**: username=`admin`, password=`admin`
- **User**: username=`user`, password=`user`

## 📋 Troubleshooting

### Gateway Connection Refused
```
❌ Gateway failed to start
```
**Solution**: Ensure Docker containers are running:
```powershell
docker-compose ps
docker-compose up -d
```

### Model Loading Failures
```
500: MLflow model loading error
```
**Solution**: Check DagsHub credentials or ensure local models exist:
- Verify `.env` file with DAGSHUB credentials
- Check `/app/models/` directory in container
- View logs: `docker logs gateway`

### Upstream Service Errors
```
503: Upstream service unavailable
```
**Solution**: Ensure all services are healthy:
```powershell
docker-compose ps
docker logs predict-image-api
docker logs predict-text-api
docker logs training-api
```

## 🔍 Debugging

### Verbose Container Logs
```powershell
# Watch gateway logs
docker logs -f gateway

# Watch predict-image-api logs
docker logs -f predict-image-api

# Watch predict-text-api logs
docker logs -f predict-text-api

# Watch training-api logs
docker logs -f training-api
```

### Direct Endpoint Testing
```powershell
# Test health
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Test login
Invoke-RestMethod -Uri "http://localhost:8000/login" `
  -Method Post `
  -Body @{username="admin"; password="admin"} `
  -ContentType "application/x-www-form-urlencoded"

# Test prediction
Invoke-RestMethod -Uri "http://localhost:8000/predict/cnn" `
  -Method Post `
  -Headers @{Authorization="Bearer $token"} `
  -Body '{"image_path":"image.jpg"}' `
  -ContentType "application/json"
```

## 📈 Performance Metrics

Tests also validate Prometheus metrics endpoint:
- `GET /metrics` - Returns gauge, counter, and histogram metrics
- Request count tracking per endpoint
- Request latency tracking
- Upstream API call tracking

## ✅ Success Criteria

All tests pass when:
- ✅ Health check returns 200
- ✅ Authentication works with valid credentials
- ✅ Authorization prevents unauthorized access
- ✅ Predictions return valid results
- ✅ Training endpoints accept requests
- ✅ Data management detects changes
- ✅ Session management works correctly

## 📚 Additional Resources

- [Gateway Main](../gateway/gateway_main.py) - Gateway implementation
- [Inference API](../src/inference/main.py) - Prediction service
- [Training API](../src/training/main.py) - Training service
- [Docker Compose](../docker-compose.yml) - Service orchestration
- [DagsHub Integration](https://dagshub.com) - Model registry

## 🎯 Next Steps

1. ✅ Run test suite: `.\tests\run_tests.ps1`
2. ✅ Review test results for any failures
3. ✅ Configure DagsHub if model management needed
4. ✅ Monitor logs for service issues
5. ✅ Adjust timeouts if services are slow

---

**Last Updated**: April 20, 2026
**Test Coverage**: 100% of gateway endpoints
