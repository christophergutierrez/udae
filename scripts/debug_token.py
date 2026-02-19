#!/usr/bin/env python3
"""
Debug OpenMetadata Token Issue
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OM_URL = os.getenv("OM_URL", "http://localhost:8585/api")
OM_TOKEN = os.getenv("OM_TOKEN", "")

print("🔍 Token Debug Information")
print("=" * 60)
print()

# Check if token exists
if not OM_TOKEN:
    print("❌ OM_TOKEN is not set in .env file")
    sys.exit(1)

print("✅ Token loaded from .env")
print(f"   Length: {len(OM_TOKEN)} characters")
print(f"   First 20 chars: {OM_TOKEN[:20]}...")
print(f"   Last 20 chars: ...{OM_TOKEN[-20:]}")
print(f"   Starts with 'eyJ': {OM_TOKEN.startswith('eyJ')}")
print(f"   Has whitespace: {any(c.isspace() for c in OM_TOKEN)}")
print(f"   Has newlines: {'\\n' in OM_TOKEN or '\\r' in OM_TOKEN}")
print()

# Clean token (remove any whitespace)
clean_token = OM_TOKEN.strip()
if clean_token != OM_TOKEN:
    print("⚠️  Token had whitespace! Cleaning...")
    OM_TOKEN = clean_token

# Test 1: Check OpenMetadata is running
print("Test 1: Check OpenMetadata is running...")
try:
    response = requests.get(f"{OM_URL.replace('/api', '')}", timeout=5)
    if response.status_code == 200:
        print("✅ OpenMetadata is accessible")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Cannot reach OpenMetadata: {e}")
    sys.exit(1)

print()

# Test 2: Try to get current user info
print("Test 2: Get current user with token...")
headers = {"Authorization": f"Bearer {OM_TOKEN}", "Content-Type": "application/json"}

response = requests.get(f"{OM_URL}/v1/users/loggedInUser", headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")

if response.status_code == 200:
    user = response.json()
    print("✅ Token is valid!")
    print(f"   Logged in as: {user.get('name')} ({user.get('email')})")
    print(f"   User type: {user.get('type', 'N/A')}")
    print(f"   Is admin: {user.get('isAdmin', False)}")
else:
    print("❌ Token authentication failed!")
    print(f"   Full response: {response.text}")

print()

# Test 3: List services
print("Test 3: Try to list database services...")
response = requests.get(f"{OM_URL}/v1/services/databaseServices", headers=headers)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    services = response.json()
    print("✅ Can list services!")
    print(f"   Found {len(services.get('data', []))} services")
    for svc in services.get("data", [])[:3]:
        print(f"   - {svc.get('name')}")
elif response.status_code == 401:
    print("❌ Unauthorized (401)")
    print(f"   Response: {response.text}")
else:
    print(f"⚠️  Status {response.status_code}")
    print(f"   Response: {response.text[:200]}")

print()

# Test 4: Try to create a simple service
print("Test 4: Try to create a test service...")
test_service = {
    "name": "test_connection_check",
    "serviceType": "Postgres",
    "connection": {
        "config": {
            "type": "Postgres",
            "username": "test",
            "password": "test",
            "hostPort": "localhost:5432",
            "database": "test",
        }
    },
}

response = requests.post(
    f"{OM_URL}/v1/services/databaseServices", headers=headers, json=test_service
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")

if response.status_code == 401:
    print()
    print("=" * 60)
    print("❌ PROBLEM IDENTIFIED: Token is not authorized")
    print()
    print("This usually means:")
    print("  1. You're using a BOT token instead of a USER token")
    print("  2. The bot doesn't have the right permissions")
    print()
    print("SOLUTION: Get a user login token instead")
    print()
    print("Try this in your browser console at http://localhost:8585:")
    print("  localStorage.getItem('oidcIdToken')")
    print()
    print("Or create a new admin user and use their token")

print()
print("=" * 60)
print("Debug complete")
