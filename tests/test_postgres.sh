#!/bin/bash

# PostgreSQL Integration Testing Script
# This script automates the setup and execution of tests with real PostgreSQL

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration
COMPOSE_FILE="docker-compose.yml"
TEST_DB_SERVICE="postgres_test"
DEV_DB_SERVICE="postgres"
INTEGRATION_TEST_FILE="test_integration.py"
UNIT_TEST_FILE="test_main.py"

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not running or not installed"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed or not available"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are available"
}

# Check if PostgreSQL test database is running
check_postgres_test() {
    if docker compose ps $TEST_DB_SERVICE | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for PostgreSQL service '$service_name' to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T $service_name pg_isready -U postgres &> /dev/null; then
            print_success "PostgreSQL service '$service_name' is ready"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "PostgreSQL service '$service_name' failed to become ready within timeout"
    return 1
}

# Start PostgreSQL test database
start_test_db() {
    print_status "Starting PostgreSQL test database..."
    
    if check_postgres_test; then
        print_warning "PostgreSQL test database is already running"
    else
        docker compose --profile testing up -d $TEST_DB_SERVICE
        
        if wait_for_postgres $TEST_DB_SERVICE; then
            print_success "PostgreSQL test database started successfully"
        else
            print_error "Failed to start PostgreSQL test database"
            exit 1
        fi
    fi
}

# Stop PostgreSQL test database
stop_test_db() {
    print_status "Stopping PostgreSQL test database..."
    docker compose --profile testing down
    print_success "PostgreSQL test database stopped"
}

# Run unit tests with mock database
run_unit_tests() {
    print_status "Running unit tests with mock database..."
    
    export USE_MOCK_DB=true
    
    if pytest $UNIT_TEST_FILE -v --tb=short; then
        print_success "Unit tests passed"
        return 0
    else
        print_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests with real PostgreSQL
run_integration_tests() {
    print_status "Running integration tests with real PostgreSQL..."
    
    # Set environment variables for integration tests
    export USE_MOCK_DB=false
    export DB_HOST=localhost
    export DB_PORT=5433
    export DB_NAME=fastapi_test_db
    export DB_USER=postgres
    export DB_PASSWORD=password
    
    local database_result=0
    local api_result=0
    
    # Run direct database tests first
    print_status "Running direct database tests..."
    if python test_database_direct.py; then
        print_success "Direct database tests passed"
    else
        print_error "Direct database tests failed"
        database_result=1
    fi
    
    # Run API integration tests
    print_status "Running API integration tests..."
    if python test_api_integration.py; then
        print_success "API integration tests passed"
    else
        print_error "API integration tests failed"
        api_result=1
    fi
    
    if [ $database_result -eq 0 ] && [ $api_result -eq 0 ]; then
        print_success "Integration tests passed"
        return 0
    else
        print_error "Some integration tests failed"
        return 1
    fi
}

# Run all tests
run_all_tests() {
    print_status "Running comprehensive test suite..."
    
    local unit_result=0
    local integration_result=0
    
    # Run unit tests first (faster)
    run_unit_tests || unit_result=1
    
    # Run integration tests
    run_integration_tests || integration_result=1
    
    if [ $unit_result -eq 0 ] && [ $integration_result -eq 0 ]; then
        print_success "All tests passed!"
        return 0
    else
        print_error "Some tests failed"
        [ $unit_result -ne 0 ] && print_error "Unit tests failed"
        [ $integration_result -ne 0 ] && print_error "Integration tests failed"
        return 1
    fi
}

# Clean up test database
cleanup_test_db() {
    print_status "Cleaning up test database..."
    
    if check_postgres_test; then
        docker compose exec -T $TEST_DB_SERVICE psql -U postgres -d fastapi_test_db -c "TRUNCATE TABLE items RESTART IDENTITY CASCADE;" &> /dev/null || true
        print_success "Test database cleaned up"
    else
        print_warning "Test database is not running, skipping cleanup"
    fi
}

# Show database status
show_status() {
    print_status "Database Services Status:"
    echo ""
    
    # Check if test database is running
    if check_postgres_test; then
        echo -e "  ${GREEN}✓${NC} PostgreSQL Test Database (port 5433): Running"
    else
        echo -e "  ${RED}✗${NC} PostgreSQL Test Database (port 5433): Stopped"
    fi
    
    # Check if dev database is running
    if docker compose ps $DEV_DB_SERVICE | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} PostgreSQL Dev Database (port 5432): Running"
    else
        echo -e "  ${RED}✗${NC} PostgreSQL Dev Database (port 5432): Stopped"
    fi
    
    echo ""
}

# Show help
show_help() {
    echo "PostgreSQL Integration Testing Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start-db      Start PostgreSQL test database"
    echo "  stop-db       Stop PostgreSQL test database"
    echo "  unit          Run unit tests with mock database"
    echo "  integration   Run integration tests with real PostgreSQL"
    echo "  all           Run all tests (unit + integration)"
    echo "  cleanup       Clean up test database"
    echo "  status        Show database services status"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all                 # Run complete test suite"
    echo "  $0 start-db            # Start test database"
    echo "  $0 integration         # Run integration tests"
    echo "  $0 cleanup && $0 all   # Clean and run all tests"
    echo ""
}

# Main script logic
main() {
    local command=${1:-help}
    
    # Check prerequisites
    check_docker_compose
    
    case $command in
        "start-db")
            start_test_db
            ;;
        "stop-db")
            stop_test_db
            ;;
        "unit")
            run_unit_tests
            ;;
        "integration")
            start_test_db
            run_integration_tests
            ;;
        "all")
            start_test_db
            run_all_tests
            ;;
        "cleanup")
            cleanup_test_db
            ;;
        "status")
            show_status
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Trap to ensure cleanup on script exit
trap 'print_status "Script interrupted. Use \"$0 stop-db\" to stop test database if needed."' INT TERM

# Run main function
main "$@"