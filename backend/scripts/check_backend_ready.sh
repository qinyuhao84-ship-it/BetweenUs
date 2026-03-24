#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BETWEENUS_API_BASE_URL:-http://127.0.0.1:8000}}"

curl -fsS "${BASE_URL%/}/healthz" >/dev/null
curl -fsS "${BASE_URL%/}/readyz" >/dev/null

echo "BetweenUs backend is ready: ${BASE_URL%/}"
