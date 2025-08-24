#!/bin/bash

# Passkey Demo Test Script
# This script sets up and tests the complete passkey authentication flow

set -e

echo "🔐 Starting Passkey Demo Setup and Testing"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000/api/v1"
FRONTEND_URL="http://localhost:8080"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running
check_service() {
    local url=$1
    local name=$2
    
    if curl -s --fail "$url" > /dev/null 2>&1; then
        print_success "$name is running"
        return 0
    else
        print_error "$name is not accessible at $url"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local name=$2
    local timeout=${3:-30}
    
    print_status "Waiting for $name to be ready..."
    for i in $(seq 1 $timeout); do
        if curl -s --fail "$url" > /dev/null 2>&1; then
            print_success "$name is ready"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo
    print_error "$name failed to start within $timeout seconds"
    return 1
}

# Function to test API endpoint
test_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=${4:-200}
    local headers=${5:-"Content-Type: application/json"}
    
    print_status "Testing $method $endpoint"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "$headers" -d "$data" "$API_BASE$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "$headers" "$API_BASE$endpoint")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "$expected_status" ]; then
        print_success "$method $endpoint returned $status_code"
        return 0
    else
        print_error "$method $endpoint returned $status_code, expected $expected_status"
        echo "Response: $body"
        return 1
    fi
}

# Main execution
main() {
    echo
    print_status "Step 1: Checking if services are running"
    echo "----------------------------------------"
    
    # Check if services are already running
    if ! check_service "$API_BASE/../../health" "FastAPI Backend"; then
        print_status "Starting backend services..."
        
        # Start database and Redis
        docker compose up -d postgres redis
        
        # Wait for services to be ready
        wait_for_service "http://localhost:5432" "PostgreSQL" 30
        wait_for_service "http://localhost:6379" "Redis" 30
        
        # Start FastAPI application in background
        print_status "Starting FastAPI application..."
        cd "$(dirname "$0")"
        
        if [ ! -d "venv" ]; then
            print_status "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install -r requirements.txt > /dev/null 2>&1
        
        # Run database migrations
        alembic upgrade head
        
        # Start the FastAPI server in background
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
        FASTAPI_PID=$!
        
        # Wait for FastAPI to start
        wait_for_service "$API_BASE/../../" "FastAPI Backend" 30
    fi
    
    echo
    print_status "Step 2: Testing Authentication Endpoints"
    echo "--------------------------------------"
    
    # Test basic health check
    test_api "GET" "/../health" "" 200
    
    # Test user registration
    TEST_USER_DATA='{"email":"testuser@example.com","username":"testuser","password":"testpassword123"}'
    test_api "POST" "/auth/register" "$TEST_USER_DATA" 201
    
    # Test traditional login
    LOGIN_DATA='{"username":"testuser","password":"testpassword123"}'
    login_response=$(curl -s -X POST -H "Content-Type: application/json" -d "$LOGIN_DATA" "$API_BASE/auth/login/json")
    ACCESS_TOKEN=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$ACCESS_TOKEN" ]; then
        print_success "Traditional login successful"
        AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
    else
        print_error "Failed to get access token"
        echo "Response: $login_response"
        exit 1
    fi
    
    # Test protected endpoint
    test_api "GET" "/auth/me" "" 200 "$AUTH_HEADER"
    
    echo
    print_status "Step 3: Testing Passkey Registration Flow"
    echo "---------------------------------------"
    
    # Test passkey registration begin
    PASSKEY_REG_DATA='{"username":"testuser"}'
    test_api "POST" "/passkey/register/begin" "$PASSKEY_REG_DATA" 200
    
    # Note: We can't test the complete WebAuthn flow without a real browser
    print_warning "Complete passkey registration requires WebAuthn API (browser interaction)"
    
    echo
    print_status "Step 4: Testing Passkey Authentication Flow"
    echo "------------------------------------------"
    
    # Test passkey authentication begin
    PASSKEY_AUTH_DATA='{"username":"testuser"}'
    test_api "POST" "/passkey/authenticate/begin" "$PASSKEY_AUTH_DATA" 200
    
    # Test usernameless flow
    test_api "POST" "/passkey/authenticate/begin" '{}' 200
    
    print_warning "Complete passkey authentication requires WebAuthn API (browser interaction)"
    
    echo
    print_status "Step 5: Testing Passkey Management Endpoints"
    echo "------------------------------------------"
    
    # Test list credentials
    test_api "GET" "/passkey/credentials" "" 200 "$AUTH_HEADER"
    
    echo
    print_status "Step 6: Starting Frontend Demo"
    echo "-----------------------------"
    
    # Start frontend if not already running
    if ! check_service "$FRONTEND_URL" "Frontend Demo"; then
        print_status "Starting frontend demo..."
        docker compose --profile demo up -d frontend
        wait_for_service "$FRONTEND_URL" "Frontend Demo" 30
    fi
    
    echo
    print_success "All tests completed successfully!"
    echo
    print_status "🎉 Passkey Demo is Ready!"
    echo "========================"
    echo
    echo "Services running:"
    echo "  • FastAPI Backend: http://localhost:8000"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Frontend Demo: $FRONTEND_URL"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo
    echo "Test the complete passkey flow:"
    echo "  1. Open $FRONTEND_URL in your browser"
    echo "  2. Register a new user or use existing: testuser/testpassword123"
    echo "  3. Login with traditional credentials"
    echo "  4. Register a passkey"
    echo "  5. Logout and login again using the passkey"
    echo
    echo "Make sure you're using a WebAuthn-compatible browser and device!"
    echo "Supported: Chrome/Edge/Safari on macOS/iOS/Android with biometrics"
    echo
    print_warning "Remember to stop services when done: docker compose down"
}

# Cleanup function
cleanup() {
    if [ -n "$FASTAPI_PID" ]; then
        print_status "Stopping FastAPI server..."
        kill $FASTAPI_PID 2>/dev/null || true
    fi
}

# Set up cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@"