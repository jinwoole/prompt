# Enterprise FastAPI Microservice Template

A complete, production-ready FastAPI microservice template with enterprise-grade features. This template provides everything you need to build, deploy, and maintain a robust microservice.

## 🚀 Quick Start

```bash
git clone <repository-url>
cd tmp
./setup.sh my-service
cd my-service
source venv/bin/activate
fastapi dev main.py
```

Visit http://127.0.0.1:8000/docs to see your API documentation.

## ✨ Features

### Core Features
- 🏗️ **Clean Architecture**: Separation of concerns with layered architecture
- 🗄️ **PostgreSQL Integration**: Async database connections with connection pooling
- 🔍 **Enterprise Logging**: Structured JSON logging with request tracking
- ⚡ **High Performance**: Async/await throughout the application
- 🛡️ **Error Handling**: Comprehensive error handling with custom exceptions
- 📝 **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- ✅ **Data Validation**: Pydantic models with business rule validation
- 🔄 **Health Checks**: Database and application health monitoring

### Enterprise Features
- 🔐 **JWT Authentication**: Complete auth system with login, registration, and token refresh
- 📊 **Request Tracking**: Unique request IDs for tracing
- 🏭 **Configuration Management**: Environment-based configuration with validation
- 🔒 **Security Middleware**: CORS, rate limiting, and input validation
- 📈 **Production Ready**: Connection pooling, graceful shutdown
- 🧪 **Comprehensive Testing**: Full test coverage with async support
- 📋 **API Standards**: RESTful design with proper HTTP status codes
- ⚡ **Redis Caching**: Async Redis integration for high-performance caching
- 🚦 **Rate Limiting**: Configurable rate limiting per IP or user
- 📊 **Metrics & Monitoring**: Prometheus metrics and health checks
- 🗄️ **Database Migrations**: Alembic integration for schema management
- 🎯 **Business Logic Structure**: Organized folder structure for domain logic

## 🏗️ Architecture

```
app/
├── api/              # API endpoints and routes
│   ├── auth.py       # Authentication endpoints  
│   ├── items.py      # Sample CRUD endpoints
│   └── monitoring.py # Health checks and metrics
├── auth/             # Authentication system
│   ├── models.py     # Auth data models
│   ├── security.py   # JWT and password utilities
│   └── dependencies.py # Auth dependencies
├── business/         # 🎯 Your business logic goes here
│   ├── models/       # Domain models and DTOs
│   ├── services/     # Core business logic
│   ├── interfaces/   # Abstract interfaces
│   └── exceptions/   # Business exceptions
├── cache/            # Redis caching
├── config/           # Configuration management
├── middleware/       # Custom middleware
├── models/           # Database models and schemas
├── monitoring/       # Metrics and monitoring
├── repositories/     # Data access layer
├── services/         # Application services
└── utils/            # Utilities (logging, errors)
```

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (optional - uses mock DB by default)
- Redis (optional - caching features)
- Git

### Using the Setup Script (Recommended)

The easiest way to create a new service:

```bash
./setup.sh my-awesome-service
cd my-awesome-service
source venv/bin/activate
fastapi dev main.py
```

The setup script will:
- ✅ Create a new project directory
- ✅ Set up Python virtual environment
- ✅ Install all dependencies  
- ✅ Configure environment files
- ✅ Initialize git repository
- ✅ Set up database migrations
- ✅ Run tests to verify setup

### Manual Setup

If you prefer manual setup:

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd tmp
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Set up database (optional):**
```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head
```

4. **Start the application:**
```bash
fastapi dev main.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_TITLE` | Application title | `Enterprise FastAPI Application` |
| `ENVIRONMENT` | Environment (development/staging/production) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `SECRET_KEY` | JWT secret key | `change-in-production` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `fastapi_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `password` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database | `0` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | CORS allowed origins | `*` |
| `RATE_LIMIT_REQUESTS` | Requests per minute | `100` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | `30` |

## 🔐 Authentication

The template includes a complete JWT authentication system:

### Register a new user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "username": "testuser",
       "password": "securepassword"
     }'
```

### Login:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=securepassword"
```

### Use authenticated endpoints:
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer <your-token>"
```

## 📊 API Endpoints

### Authentication
- **POST** `/api/v1/auth/register` - Register new user
- **POST** `/api/v1/auth/login` - Login (form data)
- **POST** `/api/v1/auth/login/json` - Login (JSON)
- **GET** `/api/v1/auth/me` - Get current user info
- **POST** `/api/v1/auth/refresh` - Refresh access token

### Items Management (Sample CRUD)
- **GET** `/api/v1/items` - List items with pagination
- **POST** `/api/v1/items` - Create new item
- **GET** `/api/v1/items/{item_id}` - Get item by ID
- **PUT** `/api/v1/items/{item_id}` - Update item
- **DELETE** `/api/v1/items/{item_id}` - Delete item
- **GET** `/api/v1/items/search?q={query}` - Search items

### Health & Monitoring
- **GET** `/api/v1/health` - Basic health check
- **GET** `/health/detailed` - Detailed component health
- **GET** `/health/live` - Kubernetes liveness probe
- **GET** `/health/ready` - Kubernetes readiness probe
- **GET** `/metrics` - Prometheus metrics

## 🎯 Developing Business Logic

The template provides a clean structure for your business logic in `app/business/`:

### 1. Define Domain Models
```python
# app/business/models/product.py
from decimal import Decimal
from typing import Optional

class Product:
    def __init__(self, name: str, price: Decimal, category: str):
        self.name = name
        self.price = price
        self.category = category
    
    def apply_discount(self, percentage: Decimal) -> Decimal:
        return self.price * (1 - percentage / 100)
```

### 2. Create Business Services
```python
# app/business/services/product_service.py
from app.business.models.product import Product
from app.business.interfaces.product_repository import ProductRepository

class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository
    
    async def create_product(self, product_data: dict) -> Product:
        # Business validation
        if product_data['price'] <= 0:
            raise ValueError("Price must be positive")
        
        product = Product(**product_data)
        return await self.repository.save(product)
```

### 3. Define Interfaces
```python
# app/business/interfaces/product_repository.py
from abc import ABC, abstractmethod
from app.business.models.product import Product

class ProductRepository(ABC):
    @abstractmethod
    async def save(self, product: Product) -> Product:
        pass
    
    @abstractmethod
    async def find_by_id(self, product_id: int) -> Optional[Product]:
        pass
```

### 4. Handle Business Exceptions
```python
# app/business/exceptions/product_exceptions.py
class InsufficientInventoryError(Exception):
    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient inventory: requested {requested}, available {available}")
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest test_main.py -v

# Run with coverage
python -m pytest test_main.py --cov=app --cov-report=html

# Run specific test
python -m pytest test_main.py::test_create_item -v
```

Tests cover:
- ✅ API endpoint functionality
- ✅ Authentication flows
- ✅ Business logic validation
- ✅ Error handling scenarios
- ✅ Database integration
- ✅ Cache operations
- ✅ Rate limiting
- ✅ Request/response formats

## 🐳 Docker & Deployment

### Development with Docker Compose
```bash
# Start all services (PostgreSQL, Redis, App)
docker-compose up

# Start only databases
docker-compose up -d postgres redis
```

### Production Deployment
```bash
# Build production image
docker build -t my-service .

# Run with environment variables
docker run -e DB_HOST=prod-db -e REDIS_HOST=prod-redis my-service
```

### Kubernetes Ready
The template includes health check endpoints for Kubernetes:
- Liveness probe: `GET /health/live`
- Readiness probe: `GET /health/ready`

## 📊 Monitoring & Observability

### Metrics
The application exposes Prometheus metrics at `/metrics`:
- HTTP request counts and durations
- Active connections
- Database connection pool stats
- Cache hit/miss rates
- Custom business metrics

### Logging
Structured JSON logging with:
- Request ID tracking
- Performance metrics
- Error categorization
- Database query logging

### Health Checks
Multiple health check endpoints:
- `/api/v1/health` - Basic health status
- `/health/detailed` - Component-wise health
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

## 🔄 Database Migrations

The template uses Alembic for database schema management:

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

## 🚀 Production Considerations

### Security
- ✅ JWT token-based authentication
- ✅ Password hashing with bcrypt
- ✅ CORS configuration
- ✅ Rate limiting
- ✅ Input validation
- ✅ SQL injection prevention
- ⚠️ Change `SECRET_KEY` in production
- ⚠️ Use HTTPS in production
- ⚠️ Configure proper CORS origins

### Performance
- ✅ Async/await throughout
- ✅ Database connection pooling
- ✅ Redis caching
- ✅ Request/response compression
- ✅ Prometheus metrics

### Deployment
- ✅ Docker containerization
- ✅ Health checks for orchestrators
- ✅ Environment-based configuration
- ✅ Graceful shutdown
- ✅ Database migrations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.