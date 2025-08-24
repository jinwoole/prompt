#!/bin/bash

# FastAPI Microservice Template Setup Script
# Usage: ./setup.sh my-service-name
# 
# This script sets up a new microservice project based on this template

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check requirements
check_requirements() {
    print_info "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    required_version="3.8"
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python 3.8+ is required. Found: $python_version"
        exit 1
    fi
    
    # Check pip
    if ! command_exists pip3; then
        print_error "pip3 is required but not installed."
        exit 1
    fi
    
    # Check git
    if ! command_exists git; then
        print_error "git is required but not installed."
        exit 1
    fi
    
    print_success "All requirements satisfied"
}

# Function to validate service name
validate_service_name() {
    local name="$1"
    
    if [[ -z "$name" ]]; then
        print_error "Service name is required"
        echo "Usage: $0 <service-name>"
        exit 1
    fi
    
    # Check if name is valid (alphanumeric, hyphens, underscores)
    if [[ ! "$name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        print_error "Service name can only contain letters, numbers, hyphens, and underscores"
        exit 1
    fi
    
    # Check if directory already exists
    if [[ -d "$name" ]]; then
        print_error "Directory '$name' already exists"
        exit 1
    fi
}

# Function to copy template files
copy_template() {
    local service_name="$1"
    local current_dir=$(pwd)
    
    print_info "Creating new service directory: $service_name"
    
    # Create service directory
    mkdir -p "$service_name"
    
    # Copy all files except .git and the script itself
    print_info "Copying template files..."
    rsync -av --exclude='.git' --exclude='setup.sh' --exclude="$service_name" . "$service_name/"
    
    print_success "Template files copied"
}

# Function to update configuration files
update_config() {
    local service_name="$1"
    
    print_info "Updating configuration for service: $service_name"
    
    cd "$service_name"
    
    # Update .env.example
    if [[ -f ".env.example" ]]; then
        sed -i.bak "s/Enterprise FastAPI Application/$service_name/g" .env.example
        sed -i.bak "s/fastapi_db/${service_name}_db/g" .env.example
        rm .env.example.bak 2>/dev/null || true
    fi
    
    # Update docker-compose.yml
    if [[ -f "docker-compose.yml" ]]; then
        sed -i.bak "s/fastapi-app/$service_name/g" docker-compose.yml
        sed -i.bak "s/fastapi_db/${service_name}_db/g" docker-compose.yml
        rm docker-compose.yml.bak 2>/dev/null || true
    fi
    
    # Update Dockerfile
    if [[ -f "Dockerfile" ]]; then
        sed -i.bak "s/Enterprise FastAPI Application/$service_name/g" Dockerfile
        rm Dockerfile.bak 2>/dev/null || true
    fi
    
    # Create .env from .env.example
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_success "Created .env file from template"
    fi
    
    print_success "Configuration updated"
}

# Function to set up Python environment
setup_python_env() {
    local service_name="$1"
    
    print_info "Setting up Python virtual environment..."
    
    cd "$service_name"
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python environment set up"
}

# Function to initialize git repository
init_git() {
    local service_name="$1"
    
    print_info "Initializing git repository..."
    
    cd "$service_name"
    
    # Initialize git repo
    git init
    
    # Add all files
    git add .
    
    # Initial commit
    git commit -m "Initial commit: $service_name microservice from template"
    
    print_success "Git repository initialized"
}

# Function to run tests
run_tests() {
    local service_name="$1"
    
    print_info "Running tests to verify setup..."
    
    cd "$service_name"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run tests
    python -m pytest tests/test_main.py -v
    
    if [[ $? -eq 0 ]]; then
        print_success "All tests passed!"
    else
        print_warning "Some tests failed. Please check the configuration."
    fi
}

# Function to generate initial migration
setup_database() {
    local service_name="$1"
    
    print_info "Setting up database migrations..."
    
    cd "$service_name"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Generate initial migration
    print_info "Generating initial database migration..."
    alembic revision --autogenerate -m "Initial migration"
    
    print_success "Database migration created"
    print_info "To apply migrations, run: alembic upgrade head"
}

# Function to print final instructions
print_instructions() {
    local service_name="$1"
    
    echo ""
    print_success "🎉 Service '$service_name' has been successfully created!"
    echo ""
    echo "Next steps:"
    echo "1. Navigate to your service directory:"
    echo -e "   ${BLUE}cd $service_name${NC}"
    echo ""
    echo "2. Activate the virtual environment:"
    echo -e "   ${BLUE}source venv/bin/activate${NC}"
    echo ""
    echo "3. Update configuration in .env file as needed"
    echo ""
    echo "4. Start developing your business logic in:"
    echo -e "   ${BLUE}app/business/models/${NC}     - Domain models"
    echo -e "   ${BLUE}app/business/services/${NC}   - Business logic"
    echo -e "   ${BLUE}app/business/interfaces/${NC} - Abstract interfaces"
    echo ""
    echo "5. Run the development server:"
    echo -e "   ${BLUE}fastapi dev app.main:app${NC}"
    echo ""
    echo "6. Set up your database (if using PostgreSQL):"
    echo -e "   ${BLUE}docker-compose up -d postgres redis${NC}"
    echo -e "   ${BLUE}alembic upgrade head${NC}"
    echo ""
    echo "7. Access your API:"
    echo -e "   ${BLUE}http://127.0.0.1:8000${NC}      - API"
    echo -e "   ${BLUE}http://127.0.0.1:8000/docs${NC} - Swagger UI"
    echo ""
    echo "🚀 Happy coding!"
}

# Main function
main() {
    local service_name="$1"
    
    echo "🚀 FastAPI Microservice Template Setup"
    echo "======================================"
    echo ""
    
    # Validate inputs and requirements
    validate_service_name "$service_name"
    check_requirements
    
    # Setup process
    copy_template "$service_name"
    update_config "$service_name"
    setup_python_env "$service_name"
    init_git "$service_name"
    setup_database "$service_name"
    run_tests "$service_name"
    
    # Print final instructions
    print_instructions "$service_name"
}

# Run main function with all arguments
main "$@"