#!/usr/bin/env bash

set -euo pipefail


SERVER="localhost:8080"
SERVER="https://ray-open-port-checker.uc.r.appspot.com"

set -x

time curl \
    -H "X-Ray-Open-Port-Check: 1" \
    -H "Content-Type: application/json" \
    --data-binary "$(seq 80 10000 | shuf | head -50 | sort | jq -src '{"ports": .}')" \
   "${SERVER}/open-port-check"
