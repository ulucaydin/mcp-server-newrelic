#!/bin/bash

# Deploy New Relic Dashboard Script
# This script deploys the MCP Server dashboard to your New Relic account

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required environment variables
if [ -z "$NEW_RELIC_API_KEY" ]; then
    echo "Error: NEW_RELIC_API_KEY is not set"
    exit 1
fi

if [ -z "$NEW_RELIC_ACCOUNT_ID" ]; then
    echo "Error: NEW_RELIC_ACCOUNT_ID is not set"
    exit 1
fi

# Set API endpoint based on region
if [ "$NEW_RELIC_REGION" = "EU" ]; then
    API_ENDPOINT="https://api.eu.newrelic.com/graphql"
else
    API_ENDPOINT="https://api.newrelic.com/graphql"
fi

# Dashboard file
DASHBOARD_FILE="dashboards/mcp-server-dashboard.json"

if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "Error: Dashboard file not found: $DASHBOARD_FILE"
    exit 1
fi

# Read dashboard JSON
DASHBOARD_JSON=$(cat "$DASHBOARD_FILE")

# Create GraphQL mutation
MUTATION=$(cat <<EOF
{
  "query": "mutation CreateDashboard(\$accountId: Int!, \$dashboard: DashboardInput!) {
    dashboardCreate(accountId: \$accountId, dashboard: \$dashboard) {
      entityResult {
        guid
        name
        accountId
        createdAt
        updatedAt
        permissions
        dashboardUrl: permalink
      }
      errors {
        description
        type
      }
    }
  }",
  "variables": {
    "accountId": $NEW_RELIC_ACCOUNT_ID,
    "dashboard": $DASHBOARD_JSON
  }
}
EOF
)

echo "Deploying dashboard to New Relic..."
echo "Account ID: $NEW_RELIC_ACCOUNT_ID"
echo "Region: ${NEW_RELIC_REGION:-US}"
echo "API Endpoint: $API_ENDPOINT"

# Make API request
RESPONSE=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "API-Key: $NEW_RELIC_API_KEY" \
    -d "$MUTATION")

# Check for errors
if echo "$RESPONSE" | grep -q '"errors":\[\]'; then
    echo "Dashboard deployed successfully!"
    
    # Extract dashboard URL
    DASHBOARD_URL=$(echo "$RESPONSE" | grep -o '"dashboardUrl":"[^"]*' | sed 's/"dashboardUrl":"//')
    if [ ! -z "$DASHBOARD_URL" ]; then
        echo "Dashboard URL: $DASHBOARD_URL"
    fi
else
    echo "Error deploying dashboard:"
    echo "$RESPONSE" | jq .
    exit 1
fi

# Optional: Update existing dashboard
# To update an existing dashboard, you would need to:
# 1. First query for the dashboard by name to get its GUID
# 2. Use dashboardUpdate mutation instead of dashboardCreate

echo ""
echo "To update this dashboard in the future, you can:"
echo "1. Modify the dashboard JSON file"
echo "2. Use the New Relic UI to get the dashboard GUID"
echo "3. Modify this script to use dashboardUpdate mutation"