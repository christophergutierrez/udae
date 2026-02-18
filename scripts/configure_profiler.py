#!/usr/bin/env python3
"""
Configure OpenMetadata Profiler via API
Fixes the database filter pattern issue
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OM_URL = os.getenv("OM_URL", "http://localhost:8585/api")
OM_TOKEN = os.getenv("OM_TOKEN")

if not OM_TOKEN:
    print("❌ Error: OM_TOKEN not set in .env file")
    print("   Please get token from OpenMetadata UI:")
    print("   1. Login to http://localhost:8585 (admin/admin)")
    print("   2. Settings → Bots → Create Bot")
    print("   3. Copy JWT token to .env as OM_TOKEN")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {OM_TOKEN}",
    "Content-Type": "application/json"
}

def get_service_id(service_name="pagila"):
    """Get the service ID for the database service"""
    print(f"🔍 Looking for service: {service_name}")

    url = f"{OM_URL}/v1/services/databaseServices/name/{service_name}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"❌ Service '{service_name}' not found")
        print(f"   Please add the Pagila database service first via the UI")
        print(f"   Settings → Services → Databases → Add Service")
        sys.exit(1)

    service = response.json()
    print(f"✅ Found service: {service['id']}")
    return service['id']

def delete_existing_profiler(service_id):
    """Delete existing profiler ingestion pipelines"""
    print("🗑️  Checking for existing profiler pipelines...")

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    params = {
        "service": service_id,
        "pipelineType": "profiler"
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        pipelines = response.json().get("data", [])
        for pipeline in pipelines:
            print(f"   Deleting: {pipeline['name']}")
            delete_url = f"{OM_URL}/v1/services/ingestionPipelines/{pipeline['id']}"
            requests.delete(delete_url, headers=HEADERS, params={"hardDelete": "true"})

        if pipelines:
            print(f"✅ Deleted {len(pipelines)} existing profiler(s)")
    else:
        print("⏭️  No existing profilers found")

def create_profiler(service_id):
    """Create a new profiler with correct configuration"""
    print("📝 Creating new profiler configuration...")

    profiler_config = {
        "name": "pagila_profiler",
        "displayName": "Pagila Profiler",
        "pipelineType": "profiler",
        "service": {
            "id": service_id,
            "type": "databaseService"
        },
        "sourceConfig": {
            "config": {
                "type": "Profiler",
                "generateSampleData": True,
                "profileSample": 100.0,
                "profileSampleType": "PERCENTAGE",
                "databaseFilterPattern": {
                    "includes": ["pagila"],  # ✅ Explicitly include pagila
                    "excludes": ["^template.*"]
                },
                "schemaFilterPattern": {
                    "includes": ["public"],  # ✅ Include public schema
                    "excludes": []
                },
                "tableFilterPattern": {
                    "includes": [".*"],  # Include all tables
                    "excludes": []
                }
            }
        },
        "airflowConfig": {
            "scheduleInterval": "0 */6 * * *"  # Every 6 hours
        }
    }

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    response = requests.post(url, headers=HEADERS, json=profiler_config)

    if response.status_code in [200, 201]:
        pipeline = response.json()
        print(f"✅ Created profiler: {pipeline['id']}")
        return pipeline['id']
    else:
        print(f"❌ Failed to create profiler: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

def trigger_profiler(pipeline_id):
    """Trigger the profiler to run.

    Note: In OM 1.11.x the /trigger endpoint may return 400 even on success.
    If this fails, trigger via Airflow at http://localhost:8080 (admin/admin).
    """
    print("🚀 Triggering profiler run...")

    url = f"{OM_URL}/v1/services/ingestionPipelines/trigger/{pipeline_id}"
    response = requests.post(url, headers=HEADERS)

    if response.status_code in [200, 201]:
        print("✅ Profiler triggered successfully")
        print("   Check progress in OpenMetadata UI:")
        print("   Services → pagila → Ingestion → View Logs")
        return True
    else:
        print(f"⚠️  OM trigger returned {response.status_code} (known issue in OM 1.11.x)")
        print("   Trigger manually via Airflow UI at http://localhost:8080")
        print("   Login: admin/admin → find DAG: pagila_profiler → trigger")
        return False

def main():
    print("🔧 OpenMetadata Profiler Configuration")
    print("=" * 50)
    print()

    # Get service ID
    service_id = get_service_id("pagila")

    # Delete existing profilers
    delete_existing_profiler(service_id)

    # Create new profiler with correct config
    pipeline_id = create_profiler(service_id)

    # Trigger profiler
    trigger_profiler(pipeline_id)

    print()
    print("✅ Profiler configuration complete!")
    print()
    print("Monitor progress:")
    print("  1. Go to http://localhost:8585")
    print("  2. Services → pagila → Ingestion")
    print("  3. Click on 'pagila_profiler' → View Logs")
    print()
    print("Expected results:")
    print("  - Profiles 23 tables in public schema")
    print("  - Collects statistics (nulls, unique values, etc.)")
    print("  - Takes 2-5 minutes to complete")

if __name__ == "__main__":
    main()
