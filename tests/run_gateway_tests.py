#!/usr/bin/env python3
"""
Setup dagshub credentials and run comprehensive gateway tests.
This script configures environment for dagshub integration before running tests.
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    print(f"📁 Loading environment from: {env_file}")
    load_dotenv(env_file)

# Setup dagshub credentials from environment
print("\n🔐 Configuring DagsHub credentials...")

DAGSHUB_USERNAME = os.getenv("DAGSHUB_USERNAME", "")
DAGSHUB_PASSWORD = os.getenv("DAGSHUB_PASSWORD", "")
DAGSHUB_TOKEN = os.getenv("DAGSHUB_TOKEN", "")

if DAGSHUB_USERNAME and DAGSHUB_PASSWORD:
    print(f"✅ DagsHub username found: {DAGSHUB_USERNAME}")
    os.environ["DAGSHUB_USER_NAME"] = DAGSHUB_USERNAME
    os.environ["DAGSHUB_USER_PASSWORD"] = DAGSHUB_PASSWORD
elif DAGSHUB_TOKEN:
    print(f"✅ DagsHub token found (length: {len(DAGSHUB_TOKEN)})")
    os.environ["DAGSHUB_TOKEN"] = DAGSHUB_TOKEN
else:
    print("⚠️  No DagsHub credentials found in environment")
    print("   Set DAGSHUB_USERNAME, DAGSHUB_PASSWORD, or DAGSHUB_TOKEN")

# Setup MLflow URI if needed
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "")
if MLFLOW_TRACKING_URI:
    print(f"✅ MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    os.environ["MLFLOW_TRACKING_URI"] = MLFLOW_TRACKING_URI

# Configure Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("  STARTING COMPREHENSIVE GATEWAY TEST SUITE")
print("="*80)

# Run the test script
test_script = Path(__file__).parent / "test_gateway_endpoints.py"
if not test_script.exists():
    print(f"❌ Test script not found: {test_script}")
    sys.exit(1)

print(f"\n📝 Running test script: {test_script}\n")

# Execute tests
try:
    result = subprocess.run(
        [sys.executable, str(test_script)],
        cwd=str(project_root),
        env=os.environ.copy(),
        check=False
    )
    sys.exit(result.returncode)
except KeyboardInterrupt:
    print("\n\n⚠️  Tests interrupted by user")
    sys.exit(130)
except Exception as e:
    print(f"\n❌ Error running tests: {e}")
    sys.exit(1)
