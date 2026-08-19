#!/usr/bin/env bash
# Test plan item: smoke on prod URL — full demo scenario after cold start,
# not just localhost. Manual/CI step, not a pytest (needs a live deployed
# backend). Run this in the 08:00-12:00 Aug 20 block per plan.md, and again
# right before the pitch to catch Render free-tier cold start.
#
# Usage: ./scripts/smoke_prod.sh https://your-backend.onrender.com
set -euo pipefail

BASE_URL="${1:?Usage: smoke_prod.sh <backend-base-url>}"

echo "1. Health check (also absorbs cold-start latency)..."
time curl -sf "$BASE_URL/health" | tee /dev/stderr | grep -q '"status":"ok"'

echo "2. Login as sender..."
COOKIE_JAR=$(mktemp)
curl -sf -c "$COOKIE_JAR" -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-test-sender","role":"sender"}' > /dev/null

echo "3. Create the exact demo load (Aktau -> Shetpe, brick)..."
LOAD=$(curl -sf -b "$COOKIE_JAR" -X POST "$BASE_URL/loads" \
  -H "Content-Type: application/json" \
  -d '{"origin":"aktau","destination":"shetpe","cargo_type":"кирпич","cargo_category":"стройматериалы","weight_tons":5,"required_vehicle":"тент","pickup_time":"2026-08-20T08:00:00Z","price_kzt":45000}')
echo "$LOAD" | grep -q '"status":"OPEN"'

echo "4. Login as carrier, post a matching vehicle..."
curl -sf -c "$COOKIE_JAR" -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-test-carrier","role":"carrier"}' > /dev/null

VEHICLE=$(curl -sf -b "$COOKIE_JAR" -X POST "$BASE_URL/vehicles" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_type":"тент","capacity_tons":8,"origin":"aktau","destination":"shetpe","departure_time":"2026-08-20T08:30:00Z"}')
VEHICLE_ID=$(echo "$VEHICLE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "5. Fetch matches — must be non-empty for a direct-route vehicle..."
MATCHES=$(curl -sf "$BASE_URL/vehicles/$VEHICLE_ID/matches")
echo "$MATCHES" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d["matches"], "no matches found — check seed data"; print("OK:", len(d["matches"]), "matches")'

echo "6. Dispatcher view responds..."
curl -sf "$BASE_URL/matches" > /dev/null

rm -f "$COOKIE_JAR"
echo "SMOKE TEST PASSED — prod URL is warm and the golden path works."
