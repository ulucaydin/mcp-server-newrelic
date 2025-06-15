#!/bin/bash

# MCP Server for New Relic - Main Entry Point
# Usage: ./main.sh [command] [options]

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_BIN="$PROJECT_ROOT/bin/mcp-server"
LOG_FILE="$PROJECT_ROOT/server.log"
PID_FILE="$PROJECT_ROOT/server.pid"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Helper functions
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        success) echo -e "${GREEN}✓${NC} $message" ;;
        error) echo -e "${RED}✗${NC} $message" ;;
        info) echo -e "${BLUE}ℹ${NC} $message" ;;
        warning) echo -e "${YELLOW}⚠${NC} $message" ;;
    esac
}

ensure_binary() {
    if [ ! -f "$SERVER_BIN" ]; then
        print_status "info" "Building server binary..."
        cd "$PROJECT_ROOT"
        if make build; then
            print_status "success" "Server binary built successfully"
        else
            print_status "error" "Failed to build server"
            exit 1
        fi
    fi
}

is_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

wait_for_server() {
    local port=${1:-8080}
    local timeout=${2:-30}
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if curl -s "http://localhost:$port/api/v1/health" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

# Commands
cmd_run() {
    ensure_binary
    
    if pid=$(is_server_running); then
        print_status "warning" "Server already running with PID $pid"
        print_status "info" "Use './main.sh stop' to stop it"
        return
    fi
    
    # Parse options
    local transport="${MCP_TRANSPORT:-http}"
    local port="${SERVER_PORT:-8080}"
    local debug="false"
    local dev="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --transport) transport="$2"; shift 2 ;;
            --port) port="$2"; shift 2 ;;
            --debug) debug="true"; shift ;;
            --dev) dev="true"; shift ;;
            *) shift ;;
        esac
    done
    
    # Set environment
    export MCP_TRANSPORT="$transport"
    export SERVER_PORT="$port"
    export LOG_LEVEL=$( [ "$debug" = "true" ] && echo "DEBUG" || echo "INFO" )
    export DEV_MODE="$dev"
    export API_ENABLED="true"
    
    # Ensure New Relic license key
    if [ -z "$NEW_RELIC_LICENSE_KEY" ] && [ -n "$NEW_RELIC_API_KEY" ]; then
        export NEW_RELIC_LICENSE_KEY="$NEW_RELIC_API_KEY"
    fi
    
    print_status "info" "Starting MCP Server..."
    print_status "info" "Transport: $transport"
    print_status "info" "API Port: $port"
    print_status "info" "Debug: $debug"
    print_status "info" "Dev Mode: $dev"
    
    # Run server
    "$SERVER_BIN" 2>&1 | tee "$LOG_FILE" &
    local server_pid=$!
    echo "$server_pid" > "$PID_FILE"
    
    # Give it a moment to start
    sleep 2
    
    if is_server_running >/dev/null; then
        print_status "success" "Server started with PID $server_pid"
        print_status "info" "Press Ctrl+C to stop"
        
        # Wait for interrupt
        trap "cmd_stop" INT TERM
        wait $server_pid
    else
        print_status "error" "Server failed to start"
        cat "$LOG_FILE" | tail -20
        exit 1
    fi
}

cmd_stop() {
    if pid=$(is_server_running); then
        print_status "info" "Stopping server (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while [ $count -lt 5 ] && is_server_running >/dev/null; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if needed
        if is_server_running >/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        print_status "success" "Server stopped"
    else
        print_status "info" "No server running"
    fi
}

cmd_status() {
    if pid=$(is_server_running); then
        print_status "success" "Server is running (PID $pid)"
        
        # Check API health
        if response=$(curl -s "http://localhost:8080/api/v1/health" 2>/dev/null); then
            print_status "success" "API is healthy"
            echo "$response" | jq . 2>/dev/null || echo "$response"
        else
            print_status "warning" "API is not responding"
        fi
    else
        print_status "info" "Server is not running"
    fi
}

cmd_test() {
    print_status "info" "Running unit tests..."
    
    cd "$PROJECT_ROOT"
    if go test ./... "$@"; then
        print_status "success" "All tests passed"
    else
        print_status "error" "Tests failed"
        exit 1
    fi
}

cmd_e2e() {
    print_status "info" "Running end-to-end tests..."
    
    ensure_binary
    
    # Stop any existing server
    if is_server_running >/dev/null; then
        print_status "info" "Stopping existing server..."
        cmd_stop
        sleep 2
    fi
    
    # Start server in background
    export MCP_TRANSPORT="http"
    export SERVER_PORT="8080"
    export API_ENABLED="true"
    export DEV_MODE="false"
    export LOG_LEVEL="INFO"
    export JWT_SECRET="e2e-test-jwt-secret"
    export API_KEY_SALT="e2e-test-api-salt"
    
    # Use mock mode if requested
    if [ "$1" = "--mock" ]; then
        export MOCK_MODE="true"
        print_status "info" "Using mock data"
    fi
    
    # Ensure license key
    if [ -z "$NEW_RELIC_LICENSE_KEY" ] && [ -n "$NEW_RELIC_API_KEY" ]; then
        export NEW_RELIC_LICENSE_KEY="$NEW_RELIC_API_KEY"
    fi
    
    print_status "info" "Starting server for E2E tests..."
    "$SERVER_BIN" > "$LOG_FILE" 2>&1 &
    local server_pid=$!
    echo "$server_pid" > "$PID_FILE"
    
    # Wait for server
    if ! wait_for_server; then
        print_status "error" "Server failed to start"
        echo "Server logs:"
        tail -50 "$LOG_FILE"
        kill $server_pid 2>/dev/null || true
        rm -f "$PID_FILE"
        exit 1
    fi
    
    print_status "success" "Server is ready"
    
    # Run E2E tests
    echo ""
    echo "=============================================="
    echo "Running E2E Test Suite"
    echo "=============================================="
    
    local api_url="http://localhost:8080/api/v1"
    local test_passed=true
    
    # Test 1: Health Check
    echo -e "\nTest 1: Health Check"
    echo "--------------------"
    if response=$(curl -s "$api_url/health"); then
        print_status "success" "Health check passed"
        echo "$response" | jq . 2>/dev/null || echo "$response"
    else
        print_status "error" "Health check failed"
        test_passed=false
    fi
    
    # Test 2: Authentication
    echo -e "\nTest 2: Authentication"
    echo "----------------------"
    
    # Login
    login_response=$(curl -s -X POST "$api_url/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email": "test@example.com", "password": "testpass123"}')
    
    # Debug: show response
    # echo "Login response: $login_response"
    
    # Extract token with error handling
    jwt_token=""
    if command -v jq >/dev/null 2>&1; then
        jwt_token=$(echo "$login_response" | jq -r .token 2>/dev/null || echo "")
    else
        # Fallback: extract token using grep/sed
        jwt_token=$(echo "$login_response" | grep -o '"token":"[^"]*"' | sed 's/"token":"//' | sed 's/"$//')
    fi
    
    if [ -n "$jwt_token" ] && [ "$jwt_token" != "null" ] && [ "$jwt_token" != "" ]; then
        print_status "success" "Login successful"
        echo "JWT Token: ${jwt_token:0:20}..."
        
        # Create API key
        api_key_response=$(curl -s -X POST "$api_url/apikeys" \
            -H "Authorization: Bearer $jwt_token" \
            -H "Content-Type: application/json" \
            -d '{"name": "E2E Test Key", "permissions": ["read", "write"]}')
        
        # Extract API key
        api_key=""
        if command -v jq >/dev/null 2>&1; then
            api_key=$(echo "$api_key_response" | jq -r .key 2>/dev/null || echo "")
        else
            api_key=$(echo "$api_key_response" | grep -o '"key":"[^"]*"' | sed 's/"key":"//' | sed 's/"$//')
        fi
        
        if [ -n "$api_key" ] && [ "$api_key" != "null" ] && [ "$api_key" != "" ]; then
            print_status "success" "API key created"
            echo "API Key: ${api_key:0:20}..."
        else
            print_status "error" "Failed to create API key"
            echo "$api_key_response" | head -100
            test_passed=false
        fi
    else
        print_status "error" "Login failed"
        echo "$login_response" | head -100
        test_passed=false
    fi
    
    # Test 3: Discovery (if authenticated)
    if [ -n "$api_key" ] && [ "$api_key" != "null" ]; then
        echo -e "\nTest 3: Schema Discovery"
        echo "------------------------"
        
        schemas_response=$(curl -s "$api_url/discovery/schemas" \
            -H "X-API-Key: $api_key")
        
        if echo "$schemas_response" | grep -q "schemas"; then
            # Try to count schemas
            if command -v jq >/dev/null 2>&1; then
                schema_count=$(echo "$schemas_response" | jq -r '.schemas | length' 2>/dev/null || echo "0")
            else
                schema_count=$(echo "$schemas_response" | grep -o '"event_type"' | wc -l)
            fi
            print_status "success" "Schema discovery working"
            echo "Found $schema_count schemas"
        else
            print_status "warning" "Schema discovery returned unexpected response"
            echo "$schemas_response" | head -100
        fi
        
        # Test 4: Query Generation
        echo -e "\nTest 4: Query Generation"
        echo "------------------------"
        
        query_response=$(curl -s -X POST "$api_url/query/generate" \
            -H "X-API-Key: $api_key" \
            -H "Content-Type: application/json" \
            -d '{
                "natural_language": "Show me the slowest transactions",
                "context": {"time_range": "1 hour ago"}
            }')
        
        # Extract NRQL
        nrql=""
        if command -v jq >/dev/null 2>&1; then
            nrql=$(echo "$query_response" | jq -r .nrql 2>/dev/null || echo "")
        else
            nrql=$(echo "$query_response" | grep -o '"nrql":"[^"]*"' | sed 's/"nrql":"//' | sed 's/"$//')
        fi
        
        if [ -n "$nrql" ] && [ "$nrql" != "null" ] && [ "$nrql" != "" ]; then
            print_status "success" "Query generation working"
            echo "Generated NRQL: $nrql"
        else
            print_status "warning" "Query generation returned unexpected response"
            echo "$query_response" | head -100
        fi
    fi
    
    # Test 5: MCP Protocol
    echo -e "\nTest 5: MCP Protocol"
    echo "--------------------"
    
    mcp_response=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
        MCP_TRANSPORT=stdio "$SERVER_BIN" 2>/dev/null | head -1)
    
    if echo "$mcp_response" | grep -q "result"; then
        # Try to count tools
        if command -v jq >/dev/null 2>&1; then
            tool_count=$(echo "$mcp_response" | jq -r '.result.tools | length' 2>/dev/null || echo "0")
        else
            tool_count=$(echo "$mcp_response" | grep -o '"name"' | wc -l)
        fi
        print_status "success" "MCP protocol working"
        echo "Found $tool_count tools"
    else
        print_status "warning" "MCP protocol test incomplete"
    fi
    
    # Cleanup
    echo -e "\nCleaning up..."
    cmd_stop
    
    # Summary
    echo ""
    echo "=============================================="
    if [ "$test_passed" = "true" ]; then
        print_status "success" "All E2E tests passed!"
    else
        print_status "error" "Some E2E tests failed"
        exit 1
    fi
    echo "=============================================="
}

cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "info" "Showing logs from $LOG_FILE"
        echo "----------------------------------------"
        tail -f "$LOG_FILE"
    else
        print_status "info" "No log file found"
    fi
}

cmd_info() {
    echo ""
    echo "=============================================="
    echo "MCP Server for New Relic"
    echo "=============================================="
    
    echo -e "\nEnvironment Configuration:"
    echo "  API Key: ${NEW_RELIC_API_KEY:+${NEW_RELIC_API_KEY:0:10}...${NEW_RELIC_API_KEY: -4}}"
    echo "  Account ID: ${NEW_RELIC_ACCOUNT_ID:-Not set}"
    echo "  Region: ${NEW_RELIC_REGION:-Not set}"
    echo "  License Key: ${NEW_RELIC_LICENSE_KEY:+${NEW_RELIC_LICENSE_KEY:0:10}...${NEW_RELIC_LICENSE_KEY: -4}}"
    
    echo -e "\nBinary Status:"
    if [ -f "$SERVER_BIN" ]; then
        print_status "success" "Server binary exists"
    else
        print_status "warning" "Server binary not built (run 'make build')"
    fi
    
    echo -e "\nServer Status:"
    if pid=$(is_server_running); then
        print_status "success" "Server is running (PID $pid)"
    else
        print_status "info" "Server is not running"
    fi
    
    echo -e "\nAvailable Commands:"
    echo "  ./main.sh run       Run the server"
    echo "  ./main.sh stop      Stop the server"
    echo "  ./main.sh status    Check server status"
    echo "  ./main.sh test      Run unit tests"
    echo "  ./main.sh e2e       Run end-to-end tests"
    echo "  ./main.sh logs      Show server logs"
    echo "  ./main.sh info      Show this information"
    echo "  ./main.sh help      Show usage help"
    echo ""
}

cmd_help() {
    echo "MCP Server for New Relic - Main Entry Point"
    echo ""
    echo "Usage: ./main.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  run [options]    Run the server"
    echo "    --transport    Transport type: stdio, http, sse (default: http)"
    echo "    --port         API server port (default: 8080)"
    echo "    --debug        Enable debug logging"
    echo "    --dev          Enable development mode"
    echo ""
    echo "  stop             Stop the running server"
    echo "  status           Check server status"
    echo "  test [-v]        Run unit tests (-v for verbose)"
    echo "  e2e [--mock]     Run end-to-end tests (--mock for mock data)"
    echo "  logs             Show server logs (follows output)"
    echo "  info             Show project information"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./main.sh run --dev --debug"
    echo "  ./main.sh e2e --mock"
    echo "  ./main.sh test -v"
}

# Main entry point
main() {
    local cmd="${1:-help}"
    shift
    
    case "$cmd" in
        run) cmd_run "$@" ;;
        stop) cmd_stop ;;
        status) cmd_status ;;
        test) cmd_test "$@" ;;
        e2e) cmd_e2e "$@" ;;
        logs) cmd_logs ;;
        info) cmd_info ;;
        help) cmd_help ;;
        *) 
            print_status "error" "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"