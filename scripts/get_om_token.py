#!/usr/bin/env python3
"""Extract OpenMetadata ingestion-bot JWT token.

OM 1.11.x: token is in user_entity table (not bot_entity),
Fernet-encrypted in json->authenticationMechanism->config->JWTToken.
Fernet key is read from the openmetadata_server container environment.
"""

import subprocess
import sys

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # type: ignore[assignment,misc]


def get_encrypted_token():
    result = subprocess.run(
        ["docker", "exec", "openmetadata_mysql",
         "mysql", "-u", "openmetadata_user", "-popenmetadata_password",
         "openmetadata_db", "-sNe",
         "SELECT JSON_UNQUOTE(JSON_EXTRACT(json, '$.authenticationMechanism.config.JWTToken'))"
         " FROM user_entity WHERE name='ingestion-bot' LIMIT 1;"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def get_fernet_key():
    result = subprocess.run(
        ["docker", "exec", "openmetadata_server", "env"],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("FERNET_KEY="):
            return line.split("=", 1)[1]
    return None


try:
    encrypted = get_encrypted_token()
    if not encrypted or encrypted == "NULL":
        print("Error: No token found in user_entity table. Is OpenMetadata running?",
              file=sys.stderr)
        sys.exit(1)

    if encrypted.startswith("fernet:"):
        if Fernet is None:
            print("Error: cryptography package required. Run: pip install cryptography",
                  file=sys.stderr)
            sys.exit(1)
        fernet_key = get_fernet_key()
        if not fernet_key:
            print("Error: Could not find FERNET_KEY in openmetadata_server environment.",
                  file=sys.stderr)
            sys.exit(1)
        token = Fernet(fernet_key.encode()).decrypt(encrypted[len("fernet:"):].encode()).decode()
    else:
        # Plain JWT — future OM versions may store token unencrypted
        token = encrypted

    print(token)

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
