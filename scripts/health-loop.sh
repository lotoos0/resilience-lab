#!/usr/bin/env bash
set -euo pipefail

i=0
while true; do
  i=$((i + 1))

  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H "Host: resilience-lab.local" \
    http://localhost:8080/api/healthz || echo "ERR")

  ts=$(date +%H:%M:%S)
  echo "[$ts] request $i -> $code"

  sleep 0.2
done
