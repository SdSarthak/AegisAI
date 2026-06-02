#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# --- CONFIGURATION ---
BASE_URL="http://localhost:8000/api/v1"
WEBHOOK_URL="YOUR WEBHOOK URL HERE"
USERNAME="YOUR EMAIL HERE"
PASSWORD="YOUR PASSWORD HERE"

echo -e "Starting AegisAI Monitoring End-to-End Test..."

# --- 0. AUTHENTICATE ---
echo -e "0. Authenticating..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD" | jq -r .access_token)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "Authentication failed. Check credentials."
    exit 1
fi
echo "Token acquired."

# ---CREATE SYSTEM ---
echo -e "Creating a fresh AI System..."
SYS_ID=$(curl -s -X POST "$BASE_URL/ai-systems" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Webhook Test System", "use_case": "hr_recruitment", "sector": "HR Tech"}' | jq -r .id)
echo "System created with ID: $SYS_ID"

# ---ENABLE MONITORING ---
echo -e "Enabling monitoring and attaching webhook..."
curl -s -X PATCH "$BASE_URL/ai-systems/$SYS_ID/monitoring" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"monitoring_enabled\": true, \"webhook_url\": \"$WEBHOOK_URL\"}" > /dev/null
echo "Monitoring enabled."

# ---ROTATE SECRET ---
echo -e "Generating HMAC Webhook Secret..."
SECRET=$(curl -s -X POST "$BASE_URL/ai-systems/$SYS_ID/monitoring/rotate-secret" \
  -H "Authorization: Bearer $TOKEN" | jq -r .webhook_secret)
echo -e "SECRET GENERATED (Save this!): \033[1;33m$SECRET\033[0m"

# --- FORCE SCAN ---
echo -e "Forcing compliance scan..."
# Note: If you need to trigger a drift event, patch the risk level here before scanning.
SCAN_RESULT=$(curl -s -X POST "$BASE_URL/admin/compliance/scan" \
  -H "Authorization: Bearer $TOKEN")
EVENTS_CREATED=$(echo $SCAN_RESULT | jq -r .events_created)
echo "Scan complete. Events created: $EVENTS_CREATED"

# --- GET EVENT HISTORY ---
echo -e "Fetching drift event history..."
curl -s -X GET "$BASE_URL/ai-systems/$SYS_ID/drift-events" \
  -H "Authorization: Bearer $TOKEN" | jq '{total: .total, latest_events: .items}'

echo -e "Test sequence complete! Check $WEBHOOK_URL to verify payload and signature."
