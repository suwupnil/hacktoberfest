#!/usr/bin/env python3
"""Entry point launcher for ClaimSentry."""

import sys
import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    print("=" * 65)
    print(" ⚡ CLAIM-SENTRY // AUTONOMOUS TRIAGE ENGINE")
    print(" Hacktoberfest HackDay Sonipat • Problem 2: Triage that tests the claims")
    print(f" Web UI & API running at: http://{host}:{port}")
    print(" Local Apple Silicon M5 Optimization Active")
    print("=" * 65)

    uvicorn.run("claim_sentry.server:app", host=host, port=port, reload=False, log_level="info")
