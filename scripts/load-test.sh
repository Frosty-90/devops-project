#!/usr/bin/env bash
set -euo pipefail
URL="${URL:-http://taskboard.local/api/products}"
for i in $(seq 1 5000); do curl -s "$URL" >/dev/null || true; done
echo "Load test completed"
