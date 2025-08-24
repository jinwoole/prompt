# Docker
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for PostgreSQL
RUN pip install --no-cache-dir \
    asyncpg==0.29.0 \
    sqlalchemy[asyncio]==2.0.36 \
    python-dotenv==1.0.1 \
    structlog==24.4.0 \
    pydantic-settings==2.6.1

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]