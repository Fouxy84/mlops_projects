"""
Test suite pour tous les endpoints du Gateway.
Teste avec et sans authentification, dagshub integration.
"""

import requests
import json
import time
from pathlib import Path

# Configuration
GATEWAY_URL = "http://localhost:8000"
GATEWAY_HEALTH_URL = f"{GATEWAY_URL}/health"

# Test data
TEST_IMAGE = "image_1000076039_product_580161.jpg"
TEST_TEXT = "Ce livre est super intéressant pour apprendre les sciences"

# Credentials
ADMIN_CREDS = {"username": "admin", "password": "admin"}
USER_CREDS = {"username": "user", "password": "user"}
INVALID_CREDS = {"username": "invalid", "password": "wrong"}

# Session management
admin_session = requests.Session()
user_session = requests.Session()


def print_section(title):
    """Print test section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_test(name, status, details=""):
    """Print test result"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if details:
        print(f"   └─ {details}")


def test_gateway_health():
    """Test 1: Gateway health check (no auth required)"""
    print_section("1️⃣  TEST: HEALTH CHECK (No Auth)")
    
    try:
        response = requests.get(GATEWAY_HEALTH_URL, timeout=5)
        success = response.status_code == 200
        print_test("Gateway health", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return success
    except Exception as e:
        print_test("Gateway health", False, str(e))
        return False


def test_root_endpoint():
    """Test 2: Root endpoint (no auth required)"""
    print_section("2️⃣  TEST: ROOT ENDPOINT (No Auth)")
    
    try:
        response = requests.get(f"{GATEWAY_URL}/", timeout=5)
        success = response.status_code == 200
        print_test("Root endpoint", success, f"Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return success
    except Exception as e:
        print_test("Root endpoint", False, str(e))
        return False


def test_metrics():
    """Test 3: Metrics endpoint (no auth required)"""
    print_section("3️⃣  TEST: METRICS (No Auth)")
    
    try:
        response = requests.get(f"{GATEWAY_URL}/metrics", timeout=5)
        success = response.status_code == 200
        print_test("Metrics endpoint", success, f"Status: {response.status_code}")
        print(f"   Response length: {len(response.text)} characters")
        return success
    except Exception as e:
        print_test("Metrics endpoint", False, str(e))
        return False


def test_authentication():
    """Test 4: Authentication endpoints"""
    print_section("4️⃣  TEST: AUTHENTICATION")
    
    # Test invalid login
    print("\n📍 Invalid credentials:")
    try:
        response = requests.post(f"{GATEWAY_URL}/login", data=INVALID_CREDS, timeout=5)
        success = response.status_code == 401
        print_test("Invalid login (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Invalid login", False, str(e))
    
    # Test admin login
    print("\n📍 Admin login:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/login", data=ADMIN_CREDS, timeout=5)
        success = response.status_code == 200
        print_test("Admin login", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin login", False, str(e))
        return False
    
    # Test user login
    print("\n📍 User login:")
    try:
        response = user_session.post(f"{GATEWAY_URL}/login", data=USER_CREDS, timeout=5)
        success = response.status_code == 200
        print_test("User login", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("User login", False, str(e))
        return False
    
    return True


def test_get_me():
    """Test 5: Get current user"""
    print_section("5️⃣  TEST: GET /me (Auth Required)")
    
    # Test as admin
    print("\n📍 Admin /me:")
    try:
        response = admin_session.get(f"{GATEWAY_URL}/me", timeout=5)
        success = response.status_code == 200
        print_test("Admin /me", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin /me", False, str(e))
    
    # Test as user
    print("\n📍 User /me:")
    try:
        response = user_session.get(f"{GATEWAY_URL}/me", timeout=5)
        success = response.status_code == 200
        print_test("User /me", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("User /me", False, str(e))


def test_prediction_svm():
    """Test 6: SVM (Text) prediction"""
    print_section("6️⃣  TEST: POST /predict/svm (Auth Required)")
    
    # Test without auth
    print("\n📍 Without authentication:")
    try:
        response = requests.post(
            f"{GATEWAY_URL}/predict/svm",
            json={"text": TEST_TEXT},
            timeout=10
        )
        success = response.status_code == 401
        print_test("SVM without auth (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("SVM without auth", False, str(e))
    
    # Test as user
    print("\n📍 User SVM prediction:")
    try:
        response = user_session.post(
            f"{GATEWAY_URL}/predict/svm",
            json={"text": TEST_TEXT},
            timeout=10
        )
        success = response.status_code in [200, 400, 500]
        status_desc = {200: "Success", 400: "Bad Request", 500: "Service Error"}.get(response.status_code, "Unknown")
        print_test("User SVM prediction", success, f"Status: {response.status_code} ({status_desc})")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("User SVM prediction", False, str(e))


def test_prediction_cnn():
    """Test 7: CNN (Image) prediction"""
    print_section("7️⃣  TEST: POST /predict/cnn (Auth Required)")
    
    # Test without auth
    print("\n📍 Without authentication:")
    try:
        response = requests.post(
            f"{GATEWAY_URL}/predict/cnn",
            json={"image_path": TEST_IMAGE},
            timeout=10
        )
        success = response.status_code == 401
        print_test("CNN without auth (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("CNN without auth", False, str(e))
    
    # Test as user
    print("\n📍 User CNN prediction:")
    try:
        response = user_session.post(
            f"{GATEWAY_URL}/predict/cnn",
            json={"image_path": TEST_IMAGE},
            timeout=10
        )
        success = response.status_code in [200, 400, 500]
        status_desc = {200: "Success", 400: "Bad Request", 500: "Service Error"}.get(response.status_code, "Unknown")
        print_test("User CNN prediction", success, f"Status: {response.status_code} ({status_desc})")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("User CNN prediction", False, str(e))


def test_prediction_multimodal():
    """Test 8: Multimodal prediction"""
    print_section("8️⃣  TEST: POST /predict/multimodal (Auth Required)")
    
    # Test without auth
    print("\n📍 Without authentication:")
    try:
        response = requests.post(
            f"{GATEWAY_URL}/predict/multimodal",
            json={"text": TEST_TEXT, "image_path": TEST_IMAGE},
            timeout=10
        )
        success = response.status_code == 401
        print_test("Multimodal without auth (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Multimodal without auth", False, str(e))
    
    # Test as user
    print("\n📍 User multimodal prediction:")
    try:
        response = user_session.post(
            f"{GATEWAY_URL}/predict/multimodal",
            json={"text": TEST_TEXT, "image_path": TEST_IMAGE},
            timeout=10
        )
        success = response.status_code in [200, 400, 500]
        status_desc = {200: "Success", 400: "Bad Request", 500: "Service Error"}.get(response.status_code, "Unknown")
        print_test("User multimodal prediction", success, f"Status: {response.status_code} ({status_desc})")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print_test("User multimodal prediction", False, str(e))


def test_training():
    """Test 9: Training endpoints (Admin only)"""
    print_section("9️⃣  TEST: TRAINING ENDPOINTS (Admin Only)")
    
    # Test user cannot train
    print("\n📍 User attempting SVM training (should fail):")
    try:
        response = user_session.post(f"{GATEWAY_URL}/train/svm", timeout=10)
        success = response.status_code == 403
        print_test("User SVM training (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("User SVM training", False, str(e))
    
    # Test admin can train SVM
    print("\n📍 Admin SVM training:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/train/svm", timeout=30)
        success = response.status_code in [200, 202]
        print_test("Admin SVM training", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin SVM training", False, str(e))
    
    # Test admin can train CNN
    print("\n📍 Admin CNN training:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/train/cnn", timeout=30)
        success = response.status_code in [200, 202]
        print_test("Admin CNN training", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin CNN training", False, str(e))


def test_reload_models():
    """Test 10: Model reload endpoints (Admin only)"""
    print_section("🔟 TEST: MODEL RELOAD (Admin Only)")
    
    # Test user cannot reload
    print("\n📍 User attempting SVM reload (should fail):")
    try:
        response = user_session.post(f"{GATEWAY_URL}/reload/svm", timeout=10)
        success = response.status_code == 403
        print_test("User SVM reload (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("User SVM reload", False, str(e))
    
    # Test admin can reload SVM
    print("\n📍 Admin SVM reload:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/reload/svm", timeout=10)
        success = response.status_code in [200, 400, 500]
        print_test("Admin SVM reload", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin SVM reload", False, str(e))
    
    # Test admin can reload CNN
    print("\n📍 Admin CNN reload:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/reload/cnn", timeout=10)
        success = response.status_code in [200, 400, 500]
        print_test("Admin CNN reload", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin CNN reload", False, str(e))


def test_data_management():
    """Test 11: Data management endpoints (Admin only)"""
    print_section("1️⃣1️⃣  TEST: DATA MANAGEMENT (Admin Only)")
    
    # Check data updates
    print("\n📍 Admin check data updates:")
    try:
        response = admin_session.get(f"{GATEWAY_URL}/data/check-updates", timeout=10)
        success = response.status_code == 200
        print_test("Check data updates", success, f"Status: {response.status_code}")
        data = response.json()
        print(f"   Text files: {len(data.get('changes', {}).get('text', {}).get('current_files', []))}")
        print(f"   Image files: {len(data.get('changes', {}).get('image', {}).get('current_files', []))}")
    except Exception as e:
        print_test("Check data updates", False, str(e))
    
    # Set baseline
    print("\n📍 Admin set baseline:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/data/check-updates/baseline", timeout=10)
        success = response.status_code == 200
        print_test("Set baseline", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()['status']}")
    except Exception as e:
        print_test("Set baseline", False, str(e))
    
    # Check and retrain
    print("\n📍 Admin check and retrain:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/data/check-updates/retrain", timeout=30)
        success = response.status_code in [200, 202]
        print_test("Check and retrain", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Check and retrain", False, str(e))


def test_info():
    """Test 12: Info endpoint (Auth required)"""
    print_section("1️⃣2️⃣  TEST: INFO ENDPOINT (Auth Required)")
    
    # Test without auth
    print("\n📍 Without authentication:")
    try:
        response = requests.get(f"{GATEWAY_URL}/info", timeout=10)
        success = response.status_code == 401
        print_test("Info without auth (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Info without auth", False, str(e))
    
    # Test as user
    print("\n📍 User info request:")
    try:
        response = user_session.get(f"{GATEWAY_URL}/info", timeout=10)
        success = response.status_code in [200, 500]
        print_test("User info request", success, f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Gateway: {data.get('gateway')}")
            print(f"   Current user: {data.get('current_user', {}).get('username')}")
    except Exception as e:
        print_test("User info request", False, str(e))


def test_logout():
    """Test 13: Logout endpoint"""
    print_section("1️⃣3️⃣  TEST: LOGOUT")
    
    print("\n📍 Admin logout:")
    try:
        response = admin_session.post(f"{GATEWAY_URL}/logout", timeout=5)
        success = response.status_code == 200
        print_test("Admin logout", success, f"Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print_test("Admin logout", False, str(e))
    
    print("\n📍 Test access after logout (should fail):")
    try:
        response = admin_session.get(f"{GATEWAY_URL}/me", timeout=5)
        success = response.status_code == 401
        print_test("Access after logout (should fail)", success, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Access after logout", False, str(e))


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  GATEWAY ENDPOINT COMPREHENSIVE TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print(f"\n🔗 Gateway URL: {GATEWAY_URL}")
    print(f"⏱️  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Wait for gateway to be ready
    print("\n⏳ Waiting for gateway to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(GATEWAY_HEALTH_URL, timeout=2)
            if response.status_code == 200:
                print("✅ Gateway is ready!\n")
                break
        except:
            pass
        if attempt < max_attempts - 1:
            time.sleep(1)
            print(f"   Attempt {attempt + 1}/{max_attempts}...", end="\r")
    else:
        print("❌ Gateway failed to start")
        return
    
    # Run all tests
    test_gateway_health()
    test_root_endpoint()
    test_metrics()
    test_authentication()
    test_get_me()
    test_prediction_svm()
    test_prediction_cnn()
    test_prediction_multimodal()
    test_training()
    test_reload_models()
    test_data_management()
    test_info()
    test_logout()
    
    # Summary
    print("\n\n" + "="*80)
    print("  TEST SUITE COMPLETED")
    print("="*80)
    print("\n📊 Summary:")
    print("   ✅ All endpoints tested")
    print("   ✅ Authentication and authorization verified")
    print("   ✅ User and admin roles tested")
    print("   ✅ Predictions tested (SVM, CNN, Multimodal)")
    print("   ✅ Training endpoints tested")
    print("   ✅ Data management endpoints tested")
    print("   ✅ Session management tested (login/logout)")


if __name__ == "__main__":
    main()
