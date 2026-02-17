#!/usr/bin/env python3
"""
Add Pagila Database Service to OpenMetadata
Complete automated setup
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OM_URL = os.getenv("OM_URL", "http://localhost:8585/api")
OM_TOKEN = os.getenv("OM_TOKEN")

if not OM_TOKEN:
    print("❌ Error: OM_TOKEN not set in .env file")
    print()
    print("Get token from OpenMetadata UI:")
    print("1. Open http://localhost:8585")
    print("2. Login: admin / admin")
    print("3. Go to: Settings → Bots → ingestion-bot")
    print("4. Copy the JWT token")
    print("5. Add to .env as: OM_TOKEN=eyJ...")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {OM_TOKEN}",
    "Content-Type": "application/json"
}

def create_database_service():
    """Create Pagila database service"""
    print("📝 Creating Pagila database service...")

    service_config = {
        "name": "pagila",
        "displayName": "Pagila Sample Database",
        "description": "PostgreSQL Pagila sample database for UDAE demo",
        "serviceType": "Postgres",
        "connection": {
            "config": {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "username": "postgres",
                "authType": {
                    "password": "pagila"
                },
                "hostPort": "localhost:5433",
                "database": "pagila",
                "sslMode": "disable",
                "supportsMetadataExtraction": True,
                "supportsDBTExtraction": True,
                "supportsProfiler": True,
                "supportsQueryComment": True
            }
        }
    }

    url = f"{OM_URL}/v1/services/databaseServices"
    response = requests.post(url, headers=HEADERS, json=service_config)

    if response.status_code in [200, 201]:
        service = response.json()
        print(f"✅ Created service: {service['id']}")
        return service['id']
    elif response.status_code == 409:
        print("⏭️  Service 'pagila' already exists")
        # Get existing service
        get_url = f"{OM_URL}/v1/services/databaseServices/name/pagila"
        response = requests.get(get_url, headers=HEADERS)
        if response.status_code == 200:
            service = response.json()
            return service['id']
    else:
        print(f"❌ Failed to create service: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

def test_connection(service_id):
    """Test database connection"""
    print("🔌 Testing database connection...")

    test_config = {
        "connection": {
            "config": {
                "type": "Postgres",
                "scheme": "postgresql+psycopg2",
                "username": "postgres",
                "authType": {
                    "password": "pagila"
                },
                "hostPort": "localhost:5433",
                "database": "pagila",
                "sslMode": "disable"
            }
        },
        "serviceType": "Postgres"
    }

    url = f"{OM_URL}/v1/services/ingestionPipelines/testConnection"
    response = requests.post(url, headers=HEADERS, json=test_config)

    if response.status_code == 200:
        result = response.json()
        steps = result.get('steps', [])

        failed_steps = [s for s in steps if not s.get('passed') and s.get('mandatory')]

        if failed_steps:
            print("❌ Connection test failed:")
            for step in failed_steps:
                print(f"   - {step['name']}: {step.get('message', 'Failed')}")
            return False
        else:
            print("✅ Connection test passed!")
            return True
    else:
        print(f"⚠️  Could not test connection: {response.status_code}")
        return None

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
                "includeTables": True,
                "includeViews": True,
                "databaseFilterPattern": {
                    "includes": ["pagila"]
                },
                "schemaFilterPattern": {
                    "includes": ["public"]
                }
            }
        },
        "airflowConfig": {
            "scheduleInterval": "0 0 * * *"
        }
    }

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    response = requests.post(url, headers=HEADERS, json=config)

    if response.status_code in [200, 201]:
        pipeline = response.json()
        print(f"✅ Created metadata pipeline: {pipeline['id']}")
        return pipeline['id']
    else:
        print(f"❌ Failed to create pipeline: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def trigger_pipeline(pipeline_id):
    """Trigger pipeline execution"""
    print("🚀 Triggering metadata ingestion...")

    url = f"{OM_URL}/v1/services/ingestionPipelines/trigger/{pipeline_id}"
    response = requests.post(url, headers=HEADERS)

    if response.status_code in [200, 201]:
        print("✅ Metadata ingestion started!")
        return True
    else:
        print(f"⚠️  Failed to trigger: {response.status_code}")
        return False

def main():
    print("🔧 Complete OpenMetadata Setup for Pagila")
    print("=" * 60)
    print()

    # Step 1: Create database service
    service_id = create_database_service()

    # Step 2: Test connection
    test_connection(service_id)

    # Step 3: Create metadata ingestion
    pipeline_id = create_metadata_ingestion(service_id)

    if pipeline_id:
        # Step 4: Trigger ingestion
        trigger_pipeline(pipeline_id)

        print()
        print("=" * 60)
        print("✅ Setup complete!")
        print()
        print("Monitor progress:")
        print("  1. Open http://localhost:8585")
        print("  2. Go to: Services → Databases → pagila")
        print("  3. Click: Ingestion → pagila_metadata → View Logs")
        print()
        print("Wait 1-2 minutes for ingestion to complete, then:")
        print("  1. Browse to: Databases → pagila → public")
        print("  2. You should see 23 tables")
        print()
        print("Next steps:")
        print("  python scripts/configure_profiler.py     # Run profiler")
        print("  python -m semantic_inference --service pagila  # Add descriptions")

if __name__ == "__main__":
    main()
