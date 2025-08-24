# FastAPI Enterprise Microservice Template

A production-ready FastAPI template for building enterprise-grade microservices with comprehensive infrastructure support, security features, and developer productivity tools.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Git

### Create a New Microservice

```bash
# Clone the template
git clone <repository-url>
cd fastapi-template

# Create your new service
./setup.sh my-awesome-service
cd my-awesome-service

# Start infrastructure services
docker compose up -d postgres redis

# Activate virtual environment and run
source venv/bin/activate
alembic upgrade head
fastapi dev app.main:app
```

Your service will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🏗️ Architecture Overview

```
my-service/
├── app/
│   ├── business/         # 🎯 Your business logic goes here
│   │   ├── models/       # Domain models and DTOs
│   │   ├── services/     # Core business logic
│   │   ├── interfaces/   # Abstract interfaces
│   │   └── exceptions/   # Business-specific exceptions
│   ├── api/              # HTTP endpoints and routing
│   ├── auth/             # Authentication and authorization
│   ├── cache/            # Redis caching utilities
│   ├── middleware/       # Custom middleware (rate limiting, etc.)
│   ├── monitoring/       # Health checks and metrics
│   ├── models/           # Database entities and schemas
│   ├── repositories/     # Data access layer
│   └── services/         # Infrastructure services
├── alembic/              # Database migrations
├── examples/             # 💡 Example scripts and demos
├── tests/                # Test suite
├── docker-compose.yml    # Local development infrastructure
└── requirements.txt      # Python dependencies
```

## 📋 Features

### 🔐 Authentication & Security
- **JWT-based authentication** with refresh token support
- **User registration and login** endpoints
- **Password hashing** with bcrypt
- **Role-based access control** foundation
- **CORS configuration** for cross-origin requests
- **Input validation** with Pydantic models

### 🗄️ Database & Caching
- **PostgreSQL** with async SQLAlchemy
- **Redis** for caching and session storage
- **Alembic** database migrations
- **Connection pooling** for optimal performance
- **Automatic cache serialization** (JSON/pickle)
- **Configurable TTL** settings

### 📊 Monitoring & Observability
- **Prometheus metrics** for HTTP requests, database, and cache operations
- **Structured JSON logging** with request ID tracking
- **Health check endpoints** for Kubernetes liveness/readiness probes
- **Performance monitoring** with response time tracking
- **Error tracking** with detailed stack traces

### ⚡ Performance & Scalability
- **Async/await** throughout the application stack
- **Rate limiting** middleware with Redis backend
- **Database connection pooling** for high concurrency
- **Redis connection pooling** for cache performance
- **Horizontal scaling** ready (stateless design)

### 🛠️ Developer Experience
- **Automatic API documentation** with OpenAPI/Swagger
- **Hot reload** in development mode
- **Comprehensive test suite** with pytest
- **Pre-configured Docker** for local development
- **Type hints** throughout the codebase
- **Clear separation of concerns** between business logic and infrastructure

## 🔧 Configuration

### Environment Variables

Create a `.env` file in your service directory:

```env
# Application
APP_TITLE="My Awesome Service"
APP_VERSION="1.0.0"
ENVIRONMENT="development"

# Database
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="my_service_db"
DB_USER="postgres"
DB_PASSWORD="password"

# Redis
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"

# Security
SECRET_KEY="your-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Rate Limiting
RATE_LIMIT_REQUESTS="100"
RATE_LIMIT_WINDOW="60"
```

### Docker Compose Services

The template includes a complete Docker Compose setup:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: my_service_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app

# Run specific test file
python -m pytest tests/test_business_logic.py -v
```

### Test Categories
- **Unit tests**: Business logic and utilities
- **Integration tests**: Database and cache operations
- **API tests**: HTTP endpoints and authentication
- **Performance tests**: Load testing and benchmarks

## 🚀 Deployment

### Production Environment

1. **Update configuration**:
```env
ENVIRONMENT="production"
SECRET_KEY="your-production-secret-key"
DB_HOST="your-production-db-host"
REDIS_HOST="your-production-redis-host"
```

2. **Build and deploy**:
```bash
# Build Docker image
docker build -t my-service:latest .

# Run with docker-compose
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-service
  template:
    metadata:
      labels:
        app: my-service
    spec:
      containers:
      - name: my-service
        image: my-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
```

## 🔨 Development Guide

### Adding Business Logic

1. **Create domain models** in `app/business/models/`:
```python
from pydantic import BaseModel

class BlogPost(BaseModel):
    title: str
    content: str
    author_id: int
```

2. **Implement business services** in `app/business/services/`:
```python
from app.business.interfaces.blog_repository import BlogRepository

class BlogService:
    def __init__(self, repository: BlogRepository):
        self.repository = repository
    
    async def create_post(self, post: BlogPost) -> BlogPost:
        # Your business logic here
        return await self.repository.create(post)
```

3. **Add API endpoints** in `app/api/`:
```python
from fastapi import APIRouter, Depends
from app.business.services.blog_service import BlogService

router = APIRouter()

@router.post("/posts")
async def create_post(
    post: BlogPost,
    service: BlogService = Depends()
):
    return await service.create_post(post)
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add blog posts table"

# Apply migrations
alembic upgrade head

# Rollback to previous version
alembic downgrade -1
```

### Custom Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        response = await call_next(request)
        # Post-processing
        return response
```

## 📊 Monitoring

### Prometheus Metrics

Available metrics:
- `http_requests_total` - Total HTTP requests by endpoint, method, status
- `http_request_duration_seconds` - Request duration histogram
- `database_connections_active` - Active database connections
- `cache_operations_total` - Cache operations (hit/miss)
- `redis_connections_total` - Redis connection pool stats

### Health Checks

- **`/health`** - Basic health status
- **`/health/detailed`** - Detailed component health
- **`/health/live`** - Kubernetes liveness probe
- **`/health/ready`** - Kubernetes readiness probe

### Logging

Structured JSON logging example:
```json
{
  "timestamp": "2025-07-26T12:00:00.000Z",
  "level": "INFO",
  "logger": "app.business.services",
  "message": "Blog post created",
  "user_id": 123,
  "post_id": 456,
  "request_id": "req_abc123"
}
```

## 🔐 Security

### Authentication Flow

1. **Register user**:
```bash
curl -X POST /api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "secure123"}'
```

2. **Login and get token**:
```bash
curl -X POST /api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "secure123"}'
```

3. **Use token in requests**:
```bash
curl -H "Authorization: Bearer <token>" /api/v1/protected-endpoint
```

### Rate Limiting

Configure rate limits per endpoint:
```python
from app.middleware.rate_limit import rate_limit

@router.get("/api/v1/data")
@rate_limit(requests=100, window=60)  # 100 requests per minute
async def get_data():
    return {"data": "value"}
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database connection failed**:
   - Check PostgreSQL is running: `docker compose ps`
   - Verify database exists: `docker compose exec postgres psql -U postgres -l`

2. **Redis connection failed**:
   - Check Redis is running: `docker compose ps`
   - Test connection: `docker compose exec redis redis-cli ping`

3. **Migration errors**:
   - Reset migrations: `alembic downgrade base && alembic upgrade head`
   - Check database schema: `docker compose exec postgres psql -U postgres -d dbname -c "\dt"`

4. **Authentication issues**:
   - Verify SECRET_KEY is set
   - Check token expiration settings
   - Ensure password meets requirements

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL="DEBUG"
DEBUG="true"
```

### Performance Issues

1. **Database slow queries**:
   - Check connection pool settings
   - Add database indexes
   - Use `EXPLAIN ANALYZE` for query optimization

2. **Cache misses**:
   - Check Redis connection
   - Verify TTL settings
   - Monitor cache hit ratio in metrics

## 📚 Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Alembic Migrations**: https://alembic.sqlalchemy.org/
- **Prometheus Monitoring**: https://prometheus.io/docs/
- **Redis Documentation**: https://redis.io/documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This template is released under the MIT License. See LICENSE file for details.

---

**Need help?** Open an issue or check the [evaluation report](docs/evaluation-report.md) for detailed testing results and recommendations.