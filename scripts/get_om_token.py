#!/usr/bin/env python3
"""Extract and decrypt OpenMetadata ingestion-bot token.

OM 1.11.x: token is in bot_entity table (not user_entity),
and the Fernet key is in the container's environment variables.
"""

import subprocess
import sys


def get_fernet_key():
    result = subprocess.run(
        ["docker", "exec", "openmetadata_server", "env"],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("FERNET_KEY="):
            return line.split("=", 1)[1]
    return None


def get_encrypted_token():
    result = subprocess.run(
        ["docker", "exec", "openmetadata_mysql",
         "mysql", "-u", "openmetadata_user", "-popenmetadata_password",
         "openmetadata_db", "-sNe",
         "SELECT token FROM bot_entity WHERE name='ingestion-bot' LIMIT 1;"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


try:
    encrypted_token = get_encrypted_token()
    if not encrypted_token:
        print("Error: No token found in bot_entity table. Is OpenMetadata running?", file=sys.stderr)
        sys.exit(1)

    if not encrypted_token.startswith("fernet:"):
        # Already a plain JWT
        print(encrypted_token)
        sys.exit(0)

    fernet_key = get_fernet_key()
    if not fernet_key:
        print("Error: FERNET_KEY not found in openmetadata_server container env.", file=sys.stderr)
        sys.exit(1)

    from cryptography.fernet import Fernet
    payload = encrypted_token.replace("fernet:", "")
    token = Fernet(fernet_key.encode()).decrypt(payload.encode()).decode()
    print(token)

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
