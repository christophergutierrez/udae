#!/usr/bin/env python3
"""
Delete all broken ingestion pipelines for pagila
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

print("🗑️  Deleting All Pagila Ingestion Pipelines")
print("=" * 60)
print()

# Get all ingestion pipelines
url = f"{OM_URL}/v1/services/ingestionPipelines"
response = requests.get(url, headers=HEADERS, params={"limit": 100})

if response.status_code != 200:
    print(f"❌ Failed to list pipelines: {response.status_code}")
    print(response.text)
    sys.exit(1)

pipelines = response.json().get("data", [])
pagila_pipelines = [p for p in pipelines if "pagila" in p.get("service", {}).get("name", "").lower()]

if not pagila_pipelines:
    print("✅ No pagila pipelines found to delete")
    sys.exit(0)

print(f"Found {len(pagila_pipelines)} pagila pipeline(s) to delete:")
for pipeline in pagila_pipelines:
    print(f"  - {pipeline['name']} ({pipeline['pipelineType']})")

print()

for pipeline in pagila_pipelines:
    pipeline_id = pipeline['id']
    pipeline_name = pipeline['name']

    print(f"Deleting: {pipeline_name}...")
    delete_url = f"{OM_URL}/v1/services/ingestionPipelines/{pipeline_id}"
    response = requests.delete(delete_url, headers=HEADERS, params={"hardDelete": "true"})

    if response.status_code in [200, 204]:
        print(f"  ✅ Deleted {pipeline_name}")
    else:
        print(f"  ⚠️  Failed to delete {pipeline_name}: {response.status_code}")

print()
print("=" * 60)
print("✅ Cleanup complete!")
print()
print("Now in the OpenMetadata UI:")
print("1. Go to Settings → Services → Databases → pagila")
print("2. Click Agents tab")
print("3. Click 'Add Agent' button")
print("4. Select 'Metadata Ingestion'")
print("5. Configure and Save")
print("6. Click Run")
