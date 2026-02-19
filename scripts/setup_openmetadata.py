#!/usr/bin/env python3
"""
Add Pagila Database Service to OpenMetadata
Complete automated setup
"""

import os
import sys
import time
import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OM_URL = os.getenv("OM_URL", "http://localhost:8585/api")
OM_TOKEN = os.getenv("OM_TOKEN")

if not OM_TOKEN:
    print("❌ Error: OM_TOKEN not set in .env file")
    print()
    print("Get token from OpenMetadata (OM 1.11.x - Fernet method):")
    print("  python3 scripts/get_om_token.py")
    print("  # Then add to .env: OM_TOKEN=<output>")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {OM_TOKEN}", "Content-Type": "application/json"}

AIRFLOW_BASE = "http://localhost:8080"


def get_airflow_token():
    """Get Airflow API JWT token"""
    response = requests.post(
        f"{AIRFLOW_BASE}/auth/token",
        headers={"Content-Type": "application/json"},
        json={"username": "admin", "password": "admin"},
    )
    if response.status_code in (200, 201):
        return response.json()["access_token"]
    return None


def init_airflow_db():
    """Initialize Airflow DB (required before pipelines can run)"""
    print("🔧 Initializing Airflow DB...")
    result = os.system(
        "docker exec openmetadata_ingestion airflow db migrate > /dev/null 2>&1"
    )
    if result == 0:
        print("✅ Airflow DB initialized")
    else:
        print("⚠️  Airflow DB init returned non-zero (may already be initialized)")


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
                "authType": {"password": "pagila"},
                # Use Docker internal hostname so OM ingestion container can reach it
                "hostPort": "pagila_postgres:5432",
                "database": "pagila",
                "sslMode": "disable",
                "supportsMetadataExtraction": True,
                "supportsDBTExtraction": True,
                "supportsProfiler": True,
                "supportsQueryComment": True,
            }
        },
    }

    url = f"{OM_URL}/v1/services/databaseServices"
    response = requests.post(url, headers=HEADERS, json=service_config)

    if response.status_code in [200, 201]:
        service = response.json()
        print(f"✅ Created service: {service['id']}")
        return service["id"]
    elif response.status_code == 409:
        print("⏭️  Service 'pagila' already exists")
        get_url = f"{OM_URL}/v1/services/databaseServices/name/pagila"
        response = requests.get(get_url, headers=HEADERS)
        if response.status_code == 200:
            service = response.json()
            # Ensure hostPort is correct (fix if it was created with localhost:5433)
            conn = service.get("connection", {}).get("config", {})
            if conn.get("hostPort") != "pagila_postgres:5432":
                print("🔧 Fixing hostPort to use Docker internal hostname...")
                patch_url = f"{OM_URL}/v1/services/databaseServices/{service['id']}"
                patch_response = requests.patch(
                    patch_url,
                    headers={**HEADERS, "Content-Type": "application/json-patch+json"},
                    json=[
                        {
                            "op": "replace",
                            "path": "/connection/config/hostPort",
                            "value": "pagila_postgres:5432",
                        }
                    ],
                )
                if patch_response.status_code == 200:
                    print("✅ Fixed hostPort to pagila_postgres:5432")
                else:
                    print(f"⚠️  Could not fix hostPort: {patch_response.status_code}")
            return service["id"]
    else:
        print(f"❌ Failed to create service: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)


def create_metadata_ingestion(service_id):
    """Create metadata ingestion pipeline"""
    print("📝 Creating metadata ingestion pipeline...")

    config = {
        "name": "pagila_metadata",
        "displayName": "Pagila Metadata Ingestion",
        "pipelineType": "metadata",
        "service": {"id": service_id, "type": "databaseService"},
        "sourceConfig": {
            "config": {
                "type": "DatabaseMetadata",
                "markDeletedTables": True,
                "includeTables": True,
                "includeViews": True,
                "databaseFilterPattern": {"includes": ["pagila"]},
                "schemaFilterPattern": {"includes": ["public"]},
            }
        },
        "airflowConfig": {"scheduleInterval": "0 0 * * *"},
    }

    url = f"{OM_URL}/v1/services/ingestionPipelines"
    response = requests.post(url, headers=HEADERS, json=config)

    if response.status_code in [200, 201]:
        pipeline = response.json()
        print(f"✅ Created metadata pipeline: {pipeline['id']}")
        return pipeline["id"]
    elif response.status_code == 409:
        print("⏭️  Pipeline 'pagila_metadata' already exists")
        get_url = (
            f"{OM_URL}/v1/services/ingestionPipelines/name/" "pagila.pagila_metadata"
        )
        response = requests.get(get_url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()["id"]
    else:
        print(f"❌ Failed to create pipeline: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def deploy_pipeline(pipeline_id):
    """Deploy pipeline to Airflow (required before triggering)"""
    print("📦 Deploying pipeline to Airflow...")
    url = f"{OM_URL}/v1/services/ingestionPipelines/deploy/{pipeline_id}"
    response = requests.post(url, headers=HEADERS)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Pipeline deployed: {result.get('reason', 'OK')}")
        return True
    else:
        print(f"⚠️  Deploy returned {response.status_code}: {response.text[:200]}")
        return False


def trigger_pipeline_via_airflow(dag_id="pagila_metadata"):
    """Trigger pipeline directly via Airflow API (more reliable than OM API in 1.11.x)"""
    print("🚀 Triggering metadata ingestion via Airflow...")

    airflow_token = get_airflow_token()
    if not airflow_token:
        print("⚠️  Could not get Airflow token, trying OM trigger...")
        return False

    airflow_headers = {
        "Authorization": f"Bearer {airflow_token}",
        "Content-Type": "application/json",
    }

    # Unpause the DAG first
    requests.patch(
        f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}",
        headers=airflow_headers,
        json={"is_paused": False},
    )

    # Trigger a DAG run
    logical_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = f"manual_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    response = requests.post(
        f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}/dagRuns",
        headers=airflow_headers,
        json={"dag_run_id": run_id, "logical_date": logical_date},
    )

    if response.status_code == 200:
        print(f"✅ DAG run triggered (id: {run_id})")
        return run_id, airflow_token
    else:
        print(
            f"⚠️  Airflow trigger returned {response.status_code}: "
            f"{response.text[:200]}"
        )
        return False


def wait_for_ingestion(dag_id, run_id, airflow_token, timeout=300):
    """Poll Airflow until the DAG run completes"""
    print("⏳ Waiting for ingestion to complete...")
    airflow_headers = {"Authorization": f"Bearer {airflow_token}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        time.sleep(10)
        response = requests.get(
            f"{AIRFLOW_BASE}/api/v2/dags/{dag_id}/dagRuns/{run_id}",
            headers=airflow_headers,
        )
        if response.status_code == 200:
            state = response.json().get("state")
            print(f"   State: {state}")
            if state == "success":
                print("✅ Ingestion completed successfully!")
                return True
            elif state == "failed":
                print(
                    "❌ Ingestion failed. Check Airflow logs at "
                    "http://localhost:8080"
                )
                return False
        else:
            print(f"   (could not poll status: {response.status_code})")

    print(
        "⚠️  Timed out waiting for ingestion. Check "
        "http://localhost:8080 for status."
    )
    return False


def verify_tables():
    """Verify tables were discovered in OM"""
    print("🔍 Verifying discovered tables...")
    url = f"{OM_URL}/v1/tables?database=pagila.pagila.public&limit=50"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tables = response.json().get("data", [])
        print(f"✅ Tables discovered: {len(tables)}")
        for t in sorted(tables, key=lambda x: x.get("name", "")):
            print(f"   - {t['name']}")
        return len(tables)
    else:
        print(f"⚠️  Could not verify tables: {response.status_code}")
        return 0


def main():
    print("🔧 Complete OpenMetadata Setup for Pagila")
    print("=" * 60)
    print()

    # Step 1: Initialize Airflow DB
    init_airflow_db()

    # Step 2: Create database service (with correct Docker hostname)
    service_id = create_database_service()

    # Step 3: Create metadata ingestion pipeline
    pipeline_id = create_metadata_ingestion(service_id)

    if not pipeline_id:
        print("❌ Could not get pipeline ID. Exiting.")
        sys.exit(1)

    # Step 4: Deploy pipeline to Airflow
    time.sleep(2)
    deploy_pipeline(pipeline_id)

    # Step 5: Trigger via Airflow API
    time.sleep(2)
    result = trigger_pipeline_via_airflow("pagila_metadata")

    if result:
        run_id, airflow_token = result
        # Step 6: Wait for completion
        wait_for_ingestion("pagila_metadata", run_id, airflow_token)

        # Step 7: Verify
        time.sleep(5)
        count = verify_tables()

        print()
        print("=" * 60)
        if count >= 20:
            print("✅ Setup complete!")
        else:
            print(f"⚠️  Setup complete but only {count} tables found (expected 23).")
            print(
                "   Re-run this script or check Airflow logs at http://localhost:8080"
            )
    else:
        print()
        print("=" * 60)
        print("⚠️  Could not trigger ingestion automatically.")
        print("   Trigger manually via Airflow UI at http://localhost:8080")
        print("   Login: admin / admin")
        print("   Find DAG: pagila_metadata → trigger")

    print()
    print("Next steps:")
    print("  python -m semantic_inference --service pagila  # Add descriptions")
    print("  python -m semantic_layer --service pagila      # Generate Cube.js schemas")


if __name__ == "__main__":
    main()
