# Testing Guide

This document explains how to run tests for the Enterprise FastAPI Application, including both mock database tests and real PostgreSQL integration tests.

## Test Types

### 1. Unit Tests (Mock Database)
- **File**: `tests/test_main.py`
- **Database**: Mock in-memory storage
- **Purpose**: Fast unit tests for business logic validation
- **Environment**: Uses `.env.mock` configuration

### 2. Integration Tests (Real PostgreSQL)
- **File**: `tests/test_integration.py`
- **Database**: Real PostgreSQL 16 database
- **Purpose**: End-to-end testing with actual database operations
- **Environment**: Uses `.env.test` configuration

## Prerequisites

### For Unit Tests (Mock Database)
```bash
pip install -r requirements.txt
```

### For Integration Tests (Real PostgreSQL)
1. Install PostgreSQL dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start PostgreSQL using Docker Compose:
   ```bash
   # Start test database only
   docker-compose --profile testing up -d postgres_test
   
   # Or start both development and test databases
   docker-compose up -d postgres postgres_test
   ```

3. Verify PostgreSQL is running:
   ```bash
   docker-compose ps
   ```

## Running Tests

### Quick Start - Unit Tests Only
```bash
# Run unit tests with mock database (fast)
pytest tests/test_main.py -v

# Run with coverage
pytest tests/test_main.py --cov=app --cov-report=html
```

### Integration Tests with Real PostgreSQL
```bash
# 1. Start PostgreSQL test database
docker-compose --profile testing up -d postgres_test

# 2. Wait for database to be ready (check logs)
docker-compose logs postgres_test

# 3. Run integration tests
pytest tests/test_integration.py -v

# 4. Run all tests (unit + integration)
pytest tests/ -v

# 5. Stop test database
docker-compose --profile testing down
```

### Running Tests in Different Environments

#### Using Environment Files
```bash
# Unit tests with mock database
pytest tests/test_main.py --envfile=.env.mock -v

# Integration tests with real database
pytest tests/test_integration.py --envfile=.env.test -v
```

#### Manual Environment Setup
```bash
# For mock database tests
export USE_MOCK_DB=true
pytest tests/test_main.py -v

# For integration tests
export USE_MOCK_DB=false
export DB_HOST=localhost
export DB_PORT=5433
export DB_NAME=fastapi_test_db
pytest tests/test_integration.py -v
```

## Test Coverage

### Unit Tests Cover:
- ✅ API endpoint functionality
- ✅ Business logic validation
- ✅ Error handling
- ✅ Request/response validation
- ✅ Pagination logic
- ✅ Search functionality
- ✅ Mock database operations

### Integration Tests Cover:
- ✅ Real PostgreSQL database operations
- ✅ Database transactions and rollbacks
- ✅ Connection pooling
- ✅ Concurrent operations
- ✅ Database constraints
- ✅ Full-text search
- ✅ Performance under load

## Docker-based Testing

### Full Stack Testing
```bash
# Start all services (app + databases)
docker-compose --profile full-stack up -d

# Run tests against the containerized application
export FASTAPI_URL=http://localhost:8000
pytest tests/test_integration.py -v

# Clean up
docker-compose --profile full-stack down
```

### Database-only Testing
```bash
# Start only test database
docker-compose --profile testing up -d postgres_test

# Run local app against containerized database
pytest tests/test_integration.py -v

# Clean up
docker-compose --profile testing down
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_main.py -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: fastapi_test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5433:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_integration.py -v
        env:
          USE_MOCK_DB: false
          DB_HOST: localhost
          DB_PORT: 5433
          DB_NAME: fastapi_test_db
          DB_USER: postgres
          DB_PASSWORD: password
```

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres_test

# Test connection manually
docker-compose exec postgres_test psql -U postgres -d fastapi_test_db -c "SELECT 1;"

# Reset database if needed
docker-compose down postgres_test
docker-compose --profile testing up -d postgres_test
```

### Common Issues

1. **Port conflicts**: Change port in `docker-compose.yml` if 5433 is in use
2. **Permission denied**: Ensure Docker has proper permissions
3. **Database not ready**: Wait for health check to pass before running tests
4. **Dependency conflicts**: Use virtual environment and clean install

### Performance Testing
```bash
# Install additional testing tools
pip install pytest-benchmark pytest-xdist

# Run tests in parallel
pytest -n auto test_main.py test_integration.py

# Benchmark specific operations
pytest tests/test_integration.py::test_concurrent_operations --benchmark-only
```

## Test Data Management

### Automatic Cleanup
- Unit tests: Automatic reset of mock storage between tests
- Integration tests: Automatic database cleanup using transactions

### Manual Cleanup
```bash
# Reset test database
docker-compose exec postgres_test psql -U postgres -d fastapi_test_db -c "TRUNCATE TABLE items RESTART IDENTITY;"

# Or restart the database container
docker-compose restart postgres_test
```

## Validation Checklist

Before marking tests as complete, verify:
- [ ] All unit tests pass with mock database
- [ ] All integration tests pass with real PostgreSQL
- [ ] Database schema matches entity models
- [ ] Performance tests complete within acceptable time
- [ ] Concurrent operations handle properly
- [ ] Error handling works correctly
- [ ] Health checks return accurate status
- [ ] Cleanup works properly between tests