#!/usr/bin/env python3
"""
Demo script showcasing Prometheus Metrics functionality.

This demo demonstrates:
- HTTP request metrics collection
- Custom business metrics
- Database connection monitoring
- Cache operation metrics
- Performance monitoring
- Metrics export and visualization
- Alerting scenarios
"""
import asyncio
import random
import time
from datetime import datetime
from typing import Dict, List, Any


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


class MockRequest:
    """Mock FastAPI Request for demonstration."""
    
    def __init__(self, method: str = "GET", path: str = "/api/test"):
        self.method = method
        self.url = type('URL', (), {'path': path})()


class MockResponse:
    """Mock FastAPI Response for demonstration."""
    
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


async def demo_http_metrics():
    """Demonstrate HTTP request metrics collection."""
    print_banner("HTTP Metrics Demo")
    
    from app.monitoring import (
        REQUEST_COUNT, REQUEST_DURATION, ACTIVE_CONNECTIONS,
        MetricsMiddleware
    )
    
    print("✓ HTTP metrics available:")
    print("  - http_requests_total (Counter): Total HTTP requests by method, endpoint, status")
    print("  - http_request_duration_seconds (Histogram): Request duration distribution")
    print("  - http_active_connections (Gauge): Current active connections")
    
    # Simulate various HTTP requests
    test_requests = [
        {"method": "GET", "path": "/api/v1/users", "status": 200, "duration": 0.05},
        {"method": "POST", "path": "/api/v1/users", "status": 201, "duration": 0.12},
        {"method": "GET", "path": "/api/v1/users/123", "status": 200, "duration": 0.03},
        {"method": "PUT", "path": "/api/v1/users/123", "status": 200, "duration": 0.08},
        {"method": "DELETE", "path": "/api/v1/users/123", "status": 204, "duration": 0.06},
        {"method": "GET", "path": "/api/v1/users/999", "status": 404, "duration": 0.02},
        {"method": "POST", "path": "/api/v1/login", "status": 401, "duration": 0.15},
        {"method": "GET", "path": "/api/v1/health", "status": 200, "duration": 0.01},
    ]
    
    print(f"\n✓ Simulating {len(test_requests)} HTTP requests:")
    
    for i, req_data in enumerate(test_requests, 1):
        # Simulate active connection
        ACTIVE_CONNECTIONS.inc()
        
        # Record request metrics
        REQUEST_COUNT.labels(
            method=req_data["method"],
            endpoint=req_data["path"],
            status_code=req_data["status"]
        ).inc()
        
        REQUEST_DURATION.labels(
            method=req_data["method"],
            endpoint=req_data["path"]
        ).observe(req_data["duration"])
        
        print(f"  {i}. {req_data['method']} {req_data['path']} -> {req_data['status']} ({req_data['duration']}s)")
        
        # Simulate request completion
        ACTIVE_CONNECTIONS.dec()
        
        await asyncio.sleep(0.01)  # Small delay
    
    # Show current metrics state
    print(f"\n✓ Current metrics state:")
    print(f"  Active connections: {ACTIVE_CONNECTIONS._value._value}")
    
    # Get metric samples for display
    request_count_samples = REQUEST_COUNT.collect()[0].samples
    duration_samples = REQUEST_DURATION.collect()[0].samples
    
    print(f"  Total requests recorded: {len(request_count_samples)}")
    print(f"  Duration observations: {len([s for s in duration_samples if s.name.endswith('_count')])}")


async def demo_custom_business_metrics():
    """Demonstrate custom business metrics."""
    print_banner("Custom Business Metrics Demo")
    
    from prometheus_client import Counter, Gauge, Histogram, Summary
    
    # Define custom business metrics
    USER_REGISTRATIONS = Counter(
        'user_registrations_total',
        'Total user registrations',
        ['source', 'user_type']
    )
    
    ACTIVE_USERS = Gauge(
        'active_users_current',
        'Currently active users',
        ['user_type']
    )
    
    ORDER_VALUE = Histogram(
        'order_value_dollars',
        'Order value distribution in dollars',
        buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000, float('inf'))
    )
    
    API_RESPONSE_SIZE = Summary(
        'api_response_size_bytes',
        'API response size in bytes',
        ['endpoint']
    )
    
    FEATURE_USAGE = Counter(
        'feature_usage_total',
        'Feature usage count',
        ['feature_name', 'user_type']
    )
    
    print("✓ Custom business metrics defined:")
    print("  - user_registrations_total: Track user sign-ups by source")
    print("  - active_users_current: Monitor current active user count")
    print("  - order_value_dollars: Distribution of order values")
    print("  - api_response_size_bytes: Track API response sizes")
    print("  - feature_usage_total: Monitor feature adoption")
    
    # Simulate business events
    print(f"\n✓ Simulating business events:")
    
    # User registrations
    registration_sources = [
        ("web", "premium"), ("mobile", "free"), ("api", "enterprise"),
        ("web", "free"), ("mobile", "premium"), ("web", "free")
    ]
    
    for source, user_type in registration_sources:
        USER_REGISTRATIONS.labels(source=source, user_type=user_type).inc()
        print(f"  User registration: {source} -> {user_type}")
    
    # Update active users
    ACTIVE_USERS.labels(user_type="free").set(1250)
    ACTIVE_USERS.labels(user_type="premium").set(340)
    ACTIVE_USERS.labels(user_type="enterprise").set(85)
    print(f"  Updated active user counts")
    
    # Order values
    order_values = [15.99, 89.50, 234.00, 45.25, 567.80, 1200.00, 29.99, 156.75]
    for value in order_values:
        ORDER_VALUE.observe(value)
        print(f"  Order processed: ${value}")
    
    # API response sizes
    endpoints = ["/api/v1/users", "/api/v1/orders", "/api/v1/products"]
    for endpoint in endpoints:
        size = random.randint(512, 8192)
        API_RESPONSE_SIZE.labels(endpoint=endpoint).observe(size)
        print(f"  API response {endpoint}: {size} bytes")
    
    # Feature usage
    features = [
        ("search", "free"), ("export", "premium"), ("analytics", "enterprise"),
        ("sharing", "free"), ("automation", "premium"), ("search", "premium")
    ]
    
    for feature, user_type in features:
        FEATURE_USAGE.labels(feature_name=feature, user_type=user_type).inc()
        print(f"  Feature used: {feature} by {user_type} user")
    
    print(f"\n✓ Business metrics collected successfully")


async def demo_database_metrics():
    """Demonstrate database connection and query metrics."""
    print_banner("Database Metrics Demo")
    
    from prometheus_client import Gauge, Counter, Histogram
    from app.monitoring import DATABASE_CONNECTIONS
    
    # Define database-specific metrics
    DB_QUERY_DURATION = Histogram(
        'database_query_duration_seconds',
        'Database query execution time',
        ['query_type', 'table']
    )
    
    DB_CONNECTIONS_TOTAL = Counter(
        'database_connections_total',
        'Total database connections created',
        ['database', 'status']
    )
    
    DB_QUERY_ERRORS = Counter(
        'database_query_errors_total',
        'Database query errors',
        ['error_type', 'table']
    )
    
    DB_POOL_SIZE = Gauge(
        'database_pool_size',
        'Database connection pool size',
        ['database']
    )
    
    print("✓ Database metrics defined:")
    print("  - database_connections_active: Current active connections")
    print("  - database_query_duration_seconds: Query execution time distribution")
    print("  - database_connections_total: Total connections created")
    print("  - database_query_errors_total: Query error count by type")
    print("  - database_pool_size: Connection pool size")
    
    # Simulate database operations
    print(f"\n✓ Simulating database operations:")
    
    # Connection pool management
    DATABASE_CONNECTIONS.set(15)
    DB_POOL_SIZE.labels(database="postgresql").set(20)
    print(f"  Connection pool: 15/20 active connections")
    
    # Successful database operations
    db_operations = [
        {"type": "SELECT", "table": "users", "duration": 0.025, "status": "success"},
        {"type": "INSERT", "table": "orders", "duration": 0.045, "status": "success"},
        {"type": "UPDATE", "table": "users", "duration": 0.032, "status": "success"},
        {"type": "SELECT", "table": "products", "duration": 0.018, "status": "success"},
        {"type": "DELETE", "table": "sessions", "duration": 0.015, "status": "success"},
        {"type": "SELECT", "table": "users", "duration": 2.5, "status": "timeout"},
        {"type": "INSERT", "table": "orders", "duration": 0.0, "status": "constraint_error"},
    ]
    
    for op in db_operations:
        if op["status"] == "success":
            # Record successful query
            DB_QUERY_DURATION.labels(
                query_type=op["type"],
                table=op["table"]
            ).observe(op["duration"])
            
            DB_CONNECTIONS_TOTAL.labels(
                database="postgresql",
                status="success"
            ).inc()
            
            print(f"  ✓ {op['type']} {op['table']}: {op['duration']}s")
        else:
            # Record error
            DB_QUERY_ERRORS.labels(
                error_type=op["status"],
                table=op["table"]
            ).inc()
            
            DB_CONNECTIONS_TOTAL.labels(
                database="postgresql", 
                status="error"
            ).inc()
            
            print(f"  ✗ {op['type']} {op['table']}: {op['status']}")
    
    # Simulate connection scaling
    print(f"\n✓ Simulating connection pool scaling:")
    for i in range(3):
        current_conn = 15 + i * 2
        DATABASE_CONNECTIONS.set(current_conn)
        print(f"  Connection scaling: {current_conn}/20 active")
        await asyncio.sleep(0.1)


async def demo_cache_metrics():
    """Demonstrate cache operation metrics."""
    print_banner("Cache Metrics Demo")
    
    from app.monitoring import CACHE_OPERATIONS, record_cache_operation
    from prometheus_client import Histogram, Gauge
    
    # Define additional cache metrics
    CACHE_HIT_RATIO = Gauge(
        'cache_hit_ratio',
        'Cache hit ratio percentage',
        ['cache_type']
    )
    
    CACHE_SIZE = Gauge(
        'cache_size_bytes',
        'Cache size in bytes',
        ['cache_type']
    )
    
    CACHE_LATENCY = Histogram(
        'cache_operation_duration_seconds',
        'Cache operation latency',
        ['operation', 'cache_type']
    )
    
    print("✓ Cache metrics defined:")
    print("  - cache_operations_total: Cache operations by type and result")
    print("  - cache_hit_ratio: Cache hit ratio percentage")
    print("  - cache_size_bytes: Current cache size")
    print("  - cache_operation_duration_seconds: Operation latency")
    
    # Simulate cache operations
    print(f"\n✓ Simulating cache operations:")
    
    cache_operations = [
        {"op": "get", "result": "hit", "latency": 0.001, "cache": "redis"},
        {"op": "get", "result": "miss", "latency": 0.002, "cache": "redis"},
        {"op": "set", "result": "success", "latency": 0.005, "cache": "redis"},
        {"op": "get", "result": "hit", "latency": 0.001, "cache": "redis"},
        {"op": "delete", "result": "success", "latency": 0.003, "cache": "redis"},
        {"op": "get", "result": "hit", "latency": 0.001, "cache": "memory"},
        {"op": "set", "result": "success", "latency": 0.0001, "cache": "memory"},
        {"op": "get", "result": "miss", "latency": 0.0002, "cache": "memory"},
    ]
    
    hits = 0
    total_ops = 0
    
    for op_data in cache_operations:
        # Record operation
        record_cache_operation(op_data["op"], op_data["result"])
        
        # Record latency
        CACHE_LATENCY.labels(
            operation=op_data["op"],
            cache_type=op_data["cache"]
        ).observe(op_data["latency"])
        
        # Track hit ratio
        if op_data["op"] == "get":
            total_ops += 1
            if op_data["result"] == "hit":
                hits += 1
        
        print(f"  {op_data['cache']} {op_data['op']}: {op_data['result']} ({op_data['latency']*1000:.2f}ms)")
    
    # Update hit ratio
    if total_ops > 0:
        hit_ratio = (hits / total_ops) * 100
        CACHE_HIT_RATIO.labels(cache_type="redis").set(hit_ratio)
        print(f"\n  Cache hit ratio: {hit_ratio:.1f}% ({hits}/{total_ops})")
    
    # Update cache sizes
    CACHE_SIZE.labels(cache_type="redis").set(1024 * 1024 * 50)  # 50MB
    CACHE_SIZE.labels(cache_type="memory").set(1024 * 1024 * 10)  # 10MB
    print(f"  Cache sizes: Redis=50MB, Memory=10MB")


async def demo_metrics_export():
    """Demonstrate metrics export and visualization."""
    print_banner("Metrics Export Demo")
    
    from app.monitoring import get_metrics, get_metrics_content_type
    
    print("✓ Metrics export capabilities:")
    print(f"  Content-Type: {get_metrics_content_type()}")
    print("  Format: Prometheus text exposition format")
    print("  Endpoint: /metrics")
    
    # Get current metrics
    metrics_output = get_metrics()
    
    print(f"\n✓ Sample metrics output:")
    
    # Parse and display some metrics
    lines = metrics_output.decode('utf-8').split('\n')
    
    metrics_found = {}
    for line in lines:
        if line.startswith('#'):
            if 'HELP' in line:
                metric_name = line.split()[2]
                description = ' '.join(line.split()[3:])
                metrics_found[metric_name] = description
        elif line and not line.startswith('#'):
            # Sample metric line
            if len(metrics_found) < 10:  # Show first 10 metrics
                parts = line.split()
                if len(parts) >= 2:
                    metric_name = parts[0].split('{')[0]
                    if metric_name in metrics_found:
                        print(f"  {metric_name}: {metrics_found[metric_name]}")
                        del metrics_found[metric_name]
    
    print(f"\n✓ Metrics integration points:")
    print("  - Prometheus server scraping")
    print("  - Grafana dashboard visualization")
    print("  - Alert manager for threshold monitoring")
    print("  - Custom monitoring solutions")
    
    # Show sample Prometheus config
    print(f"\n✓ Sample Prometheus scrape config:")
    prometheus_config = """
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s"""
    
    print(prometheus_config)


async def demo_alerting_scenarios():
    """Demonstrate alerting scenarios based on metrics."""
    print_banner("Alerting Scenarios Demo")
    
    from prometheus_client import Gauge
    
    # Define alerting metrics
    ERROR_RATE = Gauge('error_rate_percent', 'Error rate percentage')
    RESPONSE_TIME_P95 = Gauge('response_time_p95_seconds', '95th percentile response time')
    CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')
    MEMORY_USAGE = Gauge('memory_usage_percent', 'Memory usage percentage')
    DISK_USAGE = Gauge('disk_usage_percent', 'Disk usage percentage')
    
    print("✓ Common alerting scenarios:")
    
    scenarios = [
        {
            "name": "High Error Rate",
            "description": "Error rate > 5%",
            "metric": ERROR_RATE,
            "threshold": 5.0,
            "current_value": 8.5,
            "severity": "critical"
        },
        {
            "name": "Slow Response Time",
            "description": "95th percentile > 2 seconds",
            "metric": RESPONSE_TIME_P95,
            "threshold": 2.0,
            "current_value": 3.2,
            "severity": "warning"
        },
        {
            "name": "High CPU Usage",
            "description": "CPU usage > 80%",
            "metric": CPU_USAGE,
            "threshold": 80.0,
            "current_value": 85.5,
            "severity": "warning"
        },
        {
            "name": "High Memory Usage",
            "description": "Memory usage > 90%",
            "metric": MEMORY_USAGE,
            "threshold": 90.0,
            "current_value": 75.2,
            "severity": "info"
        },
        {
            "name": "Disk Space Low",
            "description": "Disk usage > 85%",
            "metric": DISK_USAGE,
            "threshold": 85.0,
            "current_value": 92.1,
            "severity": "critical"
        }
    ]
    
    for scenario in scenarios:
        # Set metric value
        scenario["metric"].set(scenario["current_value"])
        
        # Check if alert should fire
        is_alerting = scenario["current_value"] > scenario["threshold"]
        alert_status = "🔥 FIRING" if is_alerting else "✅ OK"
        
        print(f"\n  {scenario['name']} ({scenario['severity'].upper()}):")
        print(f"    Rule: {scenario['description']}")
        print(f"    Current: {scenario['current_value']}")
        print(f"    Threshold: {scenario['threshold']}")
        print(f"    Status: {alert_status}")
    
    print(f"\n✓ Sample Prometheus alert rules:")
    
    alert_rules = """
groups:
  - name: fastapi-app-alerts
    rules:
      - alert: HighErrorRate
        expr: error_rate_percent > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: SlowResponseTime
        expr: response_time_p95_seconds > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times detected"
          
      - alert: HighResourceUsage
        expr: cpu_usage_percent > 80 or memory_usage_percent > 90
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High resource usage detected"
"""
    
    print(alert_rules)


async def main():
    """Run the complete metrics demo."""
    print_banner("Prometheus Metrics Demo")
    print("This demo showcases metrics collection and monitoring capabilities.")
    
    try:
        # HTTP metrics
        await demo_http_metrics()
        
        # Custom business metrics
        await demo_custom_business_metrics()
        
        # Database metrics
        await demo_database_metrics()
        
        # Cache metrics
        await demo_cache_metrics()
        
        # Metrics export
        await demo_metrics_export()
        
        # Alerting scenarios
        await demo_alerting_scenarios()
        
        print_banner("Prometheus Metrics Demo Complete")
        print("✓ All metrics features demonstrated successfully!")
        print("\nKey Features Covered:")
        print("- HTTP request metrics (count, duration, active connections)")
        print("- Custom business metrics (registrations, orders, feature usage)")
        print("- Database metrics (connections, query performance, errors)")
        print("- Cache metrics (operations, hit ratio, latency)")
        print("- Metrics export in Prometheus format")
        print("- Alerting scenarios and rule examples")
        print("- Integration with monitoring stack (Prometheus, Grafana)")
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        raise


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())