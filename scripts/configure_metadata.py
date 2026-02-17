#!/usr/bin/env python3
"""
Configure OpenMetadata Metadata Ingestion (not profiler)
This must run BEFORE the profiler
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
        sys.exit(1)

    service = response.json()
    print(f"✅ Found service: {service['id']}")
    return service['id']

def delete_existing_pipelines(service_id, pipeline_type="metadata"):
    """Delete existing pipelines"""
    print(f"🗑️  Checking for existing {pipeline_type} pipelines...")

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    params = {
        "service": service_id,
        "pipelineType": pipeline_type
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        pipelines = response.json().get("data", [])
        for pipeline in pipelines:
            print(f"   Deleting: {pipeline['name']}")
            delete_url = f"{OM_URL}/v1/services/ingestionPipelines/{pipeline['id']}"
            requests.delete(delete_url, headers=HEADERS, params={"hardDelete": "true"})

        if pipelines:
            print(f"✅ Deleted {len(pipelines)} existing pipeline(s)")
    else:
        print("⏭️  No existing pipelines found")

def create_metadata_ingestion(service_id):
    """Create metadata ingestion pipeline"""
    print("📝 Creating metadata ingestion pipeline...")

    config = {
        "name": "pagila_metadata",
        "displayName": "Pagila Metadata Ingestion",
        "pipelineType": "metadata",
        "service": {
            "id": service_id,
            "type": "databaseService"
        },
        "sourceConfig": {
            "config": {
                "type": "DatabaseMetadata",
                "markDeletedTables": True,
                "markAllDeletedTables": False,
                "includeTables": True,
                "includeViews": True,
                "includeTags": True,
                "databaseFilterPattern": {
                    "includes": ["pagila"],
                    "excludes": []
                },
                "schemaFilterPattern": {
                    "includes": ["public"],
                    "excludes": []
                },
                "tableFilterPattern": {
                    "includes": [],
                    "excludes": []
                }
            }
        },
        "airflowConfig": {
            "scheduleInterval": "0 0 * * *"  # Daily at midnight
        }
    }

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    response = requests.post(url, headers=HEADERS, json=config)

    if response.status_code in [200, 201]:
        pipeline = response.json()
        print(f"✅ Created metadata ingestion: {pipeline['id']}")
        return pipeline['id']
    else:
        print(f"❌ Failed to create metadata ingestion: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

def trigger_pipeline(pipeline_id):
    """Trigger the pipeline to run"""
    print("🚀 Triggering pipeline run...")

    url = f"{OM_URL}/v1/services/ingestionPipelines/trigger/{pipeline_id}"
    response = requests.post(url, headers=HEADERS)

    if response.status_code in [200, 201]:
        print("✅ Pipeline triggered successfully")
        print("   This will take 1-2 minutes...")
        return True
    else:
        print(f"⚠️  Failed to trigger pipeline: {response.status_code}")
        return False

def main():
    print("🔧 OpenMetadata Metadata Ingestion Setup")
    print("=" * 50)
    print()
    print("⚠️  IMPORTANT: Run this BEFORE the profiler!")
    print()

    # Get service ID
    service_id = get_service_id("pagila")

    # Delete existing metadata pipelines
    delete_existing_pipelines(service_id, "metadata")

    # Create metadata ingestion
    pipeline_id = create_metadata_ingestion(service_id)

    # Trigger pipeline
    trigger_pipeline(pipeline_id)

    print()
    print("✅ Metadata ingestion started!")
    print()
    print("Monitor progress:")
    print("  1. Go to http://localhost:8585")
    print("  2. Services → pagila → Ingestion")
    print("  3. Click on 'pagila_metadata' → View Logs")
    print()
    print("Expected results:")
    print("  - Discovers 23 tables in public schema")
    print("  - Takes 1-2 minutes to complete")
    print()
    print("After metadata ingestion completes:")
    print("  - You can browse tables in the UI")
    print("  - Then run the profiler")
    print("  - Then run semantic inference")

if __name__ == "__main__":
    main()
