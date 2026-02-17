"""
CLI entry point for text-to-query server.
"""

import sys
from .server import run_server

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
