#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

printf '%s\n' "================================================================="
printf '%s\n' " ⚡ CLAIM-SENTRY // AUTONOMOUS TRIAGE ENGINE"
printf '%s\n' " Web UI & API running at: http://${HOST}:${PORT}"
printf '%s\n' "================================================================="

exec python3 -m uvicorn claim_sentry.server:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --log-level info
