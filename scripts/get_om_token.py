#!/usr/bin/env python3
"""Extract and decrypt OpenMetadata ingestion-bot token"""

import subprocess
import json
from cryptography.fernet import Fernet

# Fernet key from OpenMetadata config (default)
FERNET_KEY = b"jJ/9sz0g0OHxsfxOoSfdFdmk3ysNmPRnH3TUAbz3IHA="

# Query MySQL for ingestion-bot JSON
cmd = [
    "docker", "exec", "openmetadata_mysql",
    "mysql", "-u", "openmetadata_user", "-popenmetadata_password",
    "openmetadata_db", "-N", "-s",
    "-e", "SELECT json FROM user_entity WHERE name='ingestion-bot';"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    user_json = json.loads(result.stdout.strip())

    # Extract encrypted token
    jwt_token = user_json['authenticationMechanism']['config']['JWTToken']

    # Remove 'fernet:' prefix if present
    if jwt_token.startswith('fernet:'):
        encrypted_token = jwt_token.replace('fernet:', '')
    else:
        encrypted_token = jwt_token

    # If token is not encrypted (plain JWT), just print it
    if encrypted_token.startswith('eyJ'):
        print(encrypted_token)
    else:
        # Decrypt
        f = Fernet(FERNET_KEY)
        decrypted = f.decrypt(encrypted_token.encode())
        token = decrypted.decode()
        print(token)

except Exception as e:
    print(f"Error: {e}", file=__import__('sys').stderr)
    exit(1)
