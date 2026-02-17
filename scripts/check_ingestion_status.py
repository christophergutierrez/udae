#!/usr/bin/env python3
"""
Check metadata ingestion status
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

OM_URL = os.getenv("OM_URL", "http://localhost:8585/api")
OM_TOKEN = os.getenv("OM_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {OM_TOKEN}",
    "Content-Type": "application/json"
}

print("🔍 Checking Metadata Ingestion Status")
print("=" * 60)
print()

# Get pagila service
url = f"{OM_URL}/v1/services/databaseServices/name/pagila"
response = requests.get(url, headers=HEADERS)

if response.status_code != 200:
    print("❌ Pagila service not found")
    sys.exit(1)

service = response.json()
service_id = service['id']
print(f"✅ Found pagila service: {service_id}")
print()

# List all pipelines for this service
url = f"{OM_URL}/v1/services/ingestionPipelines"
params = {"service": service_id}
response = requests.get(url, headers=HEADERS, params=params)

if response.status_code == 200:
    pipelines = response.json().get("data", [])
    print(f"Found {len(pipelines)} ingestion pipeline(s):")
    print()

    for pipeline in pipelines:
        print(f"Pipeline: {pipeline['name']}")
        print(f"  Type: {pipeline['pipelineType']}")
        print(f"  Status: {pipeline.get('pipelineStatuses', {})}")
        print()

        # Get pipeline runs
        pipeline_id = pipeline['id']
        runs_url = f"{OM_URL}/v1/services/ingestionPipelines/{pipeline_id}/pipelineStatus"
        runs_response = requests.get(runs_url, headers=HEADERS)

        if runs_response.status_code == 200:
            runs = runs_response.json().get("data", [])
            print(f"  Last {min(3, len(runs))} run(s):")
            for run in runs[:3]:
                status = run.get('pipelineState', 'unknown')
                start = run.get('startDate', 'N/A')
                end = run.get('endDate', 'N/A')
                print(f"    - {status} | Started: {start}")
                if status == 'failed':
                    print(f"      Error: {run.get('error', 'No error message')}")
        print()
else:
    print(f"❌ Could not list pipelines: {response.status_code}")
    print(response.text)

# Check if any tables exist in pagila
print("Checking for tables in pagila...")
url = f"{OM_URL}/v1/tables"
params = {"service": "pagila", "limit": 5}
response = requests.get(url, headers=HEADERS, params=params)

if response.status_code == 200:
    tables = response.json().get("data", [])
    if tables:
        print(f"✅ Found {len(tables)} table(s):")
        for table in tables:
            print(f"  - {table['name']}")
    else:
        print("❌ No tables found in OpenMetadata for pagila")
        print()
        print("This means metadata ingestion hasn't run successfully yet.")
else:
    print(f"⚠️ Could not check tables: {response.status_code}")

print()
print("=" * 60)
