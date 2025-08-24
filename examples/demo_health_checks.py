#!/usr/bin/env python3
"""
Demo script showcasing Health Check functionality.

This demo demonstrates:
- Basic health check endpoints
- Detailed component health monitoring
- Kubernetes liveness and readiness probes
- Dependency health checking (database, cache, external services)
- Health check aggregation and status determination
- Custom health check implementations
- Health metrics and monitoring
"""
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum


def print_banner(title: str):
    """Print a banner for the demo section."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Represents health status of a system component."""
    
    def __init__(self, name: str, status: HealthStatus, message: str = "", 
                 details: Dict[str, Any] = None, response_time: float = 0.0):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": round(self.response_time * 1000, 2),
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class HealthChecker:
    """Health checking service with component monitoring."""
    
    def __init__(self):
        self.components = {}
        self.app_version = "1.0.0"
        self.app_environment = "development"
    
    async def check_database(self) -> ComponentHealth:
        """Check database health."""
        start_time = time.time()
        
        try:
            # Simulate database check
            await asyncio.sleep(random.uniform(0.01, 0.05))  # Simulate DB latency
            
            # Randomly simulate database issues for demo
            if random.random() < 0.1:  # 10% chance of failure
                raise Exception("Connection timeout")
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="PostgreSQL connection successful",
                details={
                    "host": "localhost:5432",
                    "database": "fastapi_db",
                    "pool_size": "15/20",
                    "active_connections": 3
                },
                response_time=response_time
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                details={"error_type": "connection_error"},
                response_time=response_time
            )
    
    async def check_cache(self) -> ComponentHealth:
        """Check cache (Redis) health."""
        start_time = time.time()
        
        try:
            # Simulate cache check
            await asyncio.sleep(random.uniform(0.001, 0.01))  # Simulate Redis latency
            
            # Randomly simulate cache issues for demo
            if random.random() < 0.05:  # 5% chance of failure
                raise Exception("Redis connection refused")
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name="cache",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                details={
                    "host": "localhost:6379",
                    "memory_usage": "45MB",
                    "connected_clients": 8,
                    "hit_ratio": "87%"
                },
                response_time=response_time
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message=f"Cache unavailable: {str(e)}",
                details={"fallback": "in-memory cache active"},
                response_time=response_time
            )
    
    async def check_external_api(self, service_name: str, endpoint: str) -> ComponentHealth:
        """Check external API health."""
        start_time = time.time()
        
        try:
            # Simulate external API call
            await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate API latency
            
            # Randomly simulate API issues for demo
            failure_rate = {"payment_service": 0.15, "notification_service": 0.08, "auth_service": 0.03}
            if random.random() < failure_rate.get(service_name, 0.1):
                raise Exception("Service temporarily unavailable")
            
            response_time = time.time() - start_time
            
            return ComponentHealth(
                name=service_name,
                status=HealthStatus.HEALTHY,
                message=f"{service_name} responding normally",
                details={
                    "endpoint": endpoint,
                    "last_success": datetime.now(timezone.utc).isoformat(),
                    "api_version": "v2.1"
                },
                response_time=response_time
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ComponentHealth(
                name=service_name,
                status=HealthStatus.UNHEALTHY,
                message=f"{service_name} error: {str(e)}",
                details={"endpoint": endpoint, "error_count": 3},
                response_time=response_time
            )
    
    async def check_disk_space(self) -> ComponentHealth:
        """Check disk space health."""
        # Simulate disk usage check
        disk_usage = random.uniform(60, 95)  # Random usage between 60-95%
        
        if disk_usage > 90:
            status = HealthStatus.UNHEALTHY
            message = "Disk space critically low"
        elif disk_usage > 80:
            status = HealthStatus.DEGRADED
            message = "Disk space getting low"
        else:
            status = HealthStatus.HEALTHY
            message = "Disk space sufficient"
        
        return ComponentHealth(
            name="disk_space",
            status=status,
            message=message,
            details={
                "usage_percent": round(disk_usage, 1),
                "available_gb": round((100 - disk_usage) * 2, 1),  # Assuming 200GB total
                "mount_point": "/"
            }
        )
    
    async def check_memory_usage(self) -> ComponentHealth:
        """Check memory usage health."""
        # Simulate memory usage check
        memory_usage = random.uniform(40, 85)  # Random usage between 40-85%
        
        if memory_usage > 80:
            status = HealthStatus.DEGRADED
            message = "Memory usage high"
        else:
            status = HealthStatus.HEALTHY
            message = "Memory usage normal"
        
        return ComponentHealth(
            name="memory",
            status=status,
            message=message,
            details={
                "usage_percent": round(memory_usage, 1),
                "available_mb": round((100 - memory_usage) * 40, 1),  # Assuming 4GB total
                "processes": 45
            }
        )
    
    def aggregate_health_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Aggregate component health into overall status."""
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)
        
        # If any critical components are unhealthy, overall is unhealthy
        critical_components = {"database", "auth_service"}
        critical_unhealthy = any(c.name in critical_components and c.status == HealthStatus.UNHEALTHY 
                               for c in components)
        
        if critical_unhealthy or unhealthy_count > 2:
            return HealthStatus.UNHEALTHY
        elif unhealthy_count > 0 or degraded_count > 1:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def basic_health_check(self) -> Dict[str, Any]:
        """Basic health check - just overall status."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.app_version,
            "environment": self.app_environment
        }
    
    async def detailed_health_check(self) -> Dict[str, Any]:
        """Detailed health check with all component statuses."""
        components = []
        
        # Check all components concurrently
        tasks = [
            self.check_database(),
            self.check_cache(),
            self.check_external_api("payment_service", "https://payments.api.com/health"),
            self.check_external_api("notification_service", "https://notifications.api.com/status"),
            self.check_external_api("auth_service", "https://auth.api.com/ping"),
            self.check_disk_space(),
            self.check_memory_usage()
        ]
        
        components = await asyncio.gather(*tasks)
        
        # Aggregate overall status
        overall_status = self.aggregate_health_status(components)
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.app_version,
            "environment": self.app_environment,
            "components": {comp.name: comp.to_dict() for comp in components},
            "summary": {
                "total_components": len(components),
                "healthy": sum(1 for c in components if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in components if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
            }
        }
    
    async def liveness_probe(self) -> Dict[str, Any]:
        """Kubernetes liveness probe - basic application health."""
        # Liveness probe should only check if the application is running
        # and can accept requests, not external dependencies
        
        try:
            # Basic application health checks
            start_time = time.time()
            
            # Check if application can handle requests
            await asyncio.sleep(0.001)  # Minimal check
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": random.randint(3600, 86400),  # Simulated uptime
                "response_time_ms": round(response_time * 1000, 2)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def readiness_probe(self) -> Dict[str, Any]:
        """Kubernetes readiness probe - ready to serve traffic."""
        # Readiness probe should check if the application is ready to serve traffic
        # This includes critical dependencies like database
        
        try:
            # Check critical dependencies
            db_health = await self.check_database()
            
            # Application is ready if critical components are healthy
            if db_health.status == HealthStatus.HEALTHY:
                return {
                    "status": "ready",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Application ready to serve traffic"
                }
            else:
                return {
                    "status": "not_ready",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Waiting for critical dependencies",
                    "reason": db_health.message
                }
                
        except Exception as e:
            return {
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }


async def demo_basic_health_check():
    """Demonstrate basic health check functionality."""
    print_banner("Basic Health Check Demo")
    
    health_checker = HealthChecker()
    
    print("✓ Basic health check endpoint:")
    print("  Purpose: Quick application status check")
    print("  Endpoint: GET /health")
    print("  Use case: Load balancer health checks")
    
    # Perform basic health check
    health_result = await health_checker.basic_health_check()
    
    print(f"\n✓ Basic health check response:")
    print(json.dumps(health_result, indent=2))


async def demo_detailed_health_check():
    """Demonstrate detailed health check with component monitoring."""
    print_banner("Detailed Health Check Demo")
    
    health_checker = HealthChecker()
    
    print("✓ Detailed health check endpoint:")
    print("  Purpose: Comprehensive system status with component details")
    print("  Endpoint: GET /health/detailed")
    print("  Use case: Monitoring dashboards, troubleshooting")
    
    # Perform detailed health check
    print(f"\n✓ Checking all system components...")
    
    health_result = await health_checker.detailed_health_check()
    
    print(f"\n✓ Detailed health check response:")
    print(f"  Overall Status: {health_result['status'].upper()}")
    print(f"  Timestamp: {health_result['timestamp']}")
    print(f"  Version: {health_result['version']}")
    print(f"  Environment: {health_result['environment']}")
    
    # Show component summary
    summary = health_result['summary']
    print(f"\n✓ Component Summary:")
    print(f"  Total: {summary['total_components']}")
    print(f"  Healthy: {summary['healthy']}")
    print(f"  Degraded: {summary['degraded']}")
    print(f"  Unhealthy: {summary['unhealthy']}")
    
    # Show individual component statuses
    print(f"\n✓ Component Details:")
    for name, component in health_result['components'].items():
        status_icon = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}
        icon = status_icon.get(component['status'], "❓")
        
        print(f"  {icon} {name}: {component['status'].upper()}")
        print(f"     Message: {component['message']}")
        print(f"     Response Time: {component['response_time_ms']}ms")
        
        if component.get('details'):
            print(f"     Details: {component['details']}")


async def demo_kubernetes_probes():
    """Demonstrate Kubernetes liveness and readiness probes."""
    print_banner("Kubernetes Health Probes Demo")
    
    health_checker = HealthChecker()
    
    print("✓ Kubernetes Health Probes:")
    print("  Liveness Probe: Checks if application is running")
    print("  Readiness Probe: Checks if application is ready to serve traffic")
    
    # Liveness probe
    print(f"\n✓ Liveness Probe (GET /health/live):")
    liveness_result = await health_checker.liveness_probe()
    
    print(f"  Status: {liveness_result['status'].upper()}")
    print(f"  Uptime: {liveness_result.get('uptime_seconds', 0)} seconds")
    print(f"  Response Time: {liveness_result.get('response_time_ms', 0)}ms")
    
    # Readiness probe
    print(f"\n✓ Readiness Probe (GET /health/ready):")
    readiness_result = await health_checker.readiness_probe()
    
    print(f"  Status: {readiness_result['status'].upper()}")
    print(f"  Message: {readiness_result['message']}")
    
    if readiness_result['status'] == 'not_ready':
        print(f"  Reason: {readiness_result.get('reason', 'Unknown')}")
    
    # Show Kubernetes configuration examples
    print(f"\n✓ Sample Kubernetes Configuration:")
    
    k8s_config = """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: fastapi-app
    image: fastapi-enterprise:latest
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 2"""
    
    print(k8s_config)


async def demo_health_monitoring():
    """Demonstrate health monitoring and alerting scenarios."""
    print_banner("Health Monitoring Demo")
    
    health_checker = HealthChecker()
    
    print("✓ Health monitoring scenarios:")
    
    # Simulate multiple health checks over time
    scenarios = [
        "Normal operation",
        "Cache degradation", 
        "External service failure",
        "Database connection issues",
        "System recovery"
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n  Scenario {i}: {scenario}")
        
        # Perform health check
        health_result = await health_checker.detailed_health_check()
        
        status = health_result['status']
        summary = health_result['summary']
        
        print(f"    Overall Status: {status.upper()}")
        print(f"    Healthy Components: {summary['healthy']}/{summary['total_components']}")
        
        # Show which components are having issues
        unhealthy_components = [
            name for name, comp in health_result['components'].items() 
            if comp['status'] in ['degraded', 'unhealthy']
        ]
        
        if unhealthy_components:
            print(f"    Issues: {', '.join(unhealthy_components)}")
        
        # Simulate time passing
        await asyncio.sleep(0.1)
    
    print(f"\n✓ Health monitoring best practices:")
    practices = [
        "Monitor both liveness and readiness separately",
        "Set appropriate timeouts and retry counts",
        "Include dependency health in readiness checks",
        "Use circuit breakers for external service checks",
        "Implement health check caching for expensive operations",
        "Expose metrics for health check response times",
        "Alert on health check failures and recovery",
        "Include version and build information in health responses"
    ]
    
    for i, practice in enumerate(practices, 1):
        print(f"    {i}. {practice}")


async def demo_custom_health_checks():
    """Demonstrate custom health check implementations."""
    print_banner("Custom Health Checks Demo")
    
    print("✓ Custom health check patterns:")
    
    # Business logic health check
    class BusinessHealthCheck:
        async def check_critical_business_logic(self) -> ComponentHealth:
            """Check if critical business logic is working."""
            try:
                # Simulate business logic test
                await asyncio.sleep(0.01)
                
                # Example: Check if payment processing is working
                test_payment = {"amount": 1.00, "currency": "USD"}
                # ... simulate payment validation logic ...
                
                return ComponentHealth(
                    name="business_logic",
                    status=HealthStatus.HEALTHY,
                    message="Critical business logic operational",
                    details={"last_test": "payment_validation_passed"}
                )
                
            except Exception as e:
                return ComponentHealth(
                    name="business_logic",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Business logic error: {str(e)}",
                    details={"test_type": "payment_validation"}
                )
    
    # Queue health check
    class QueueHealthCheck:
        async def check_message_queue(self) -> ComponentHealth:
            """Check message queue health."""
            queue_depth = random.randint(0, 1000)
            processing_rate = random.uniform(50, 200)  # messages per second
            
            if queue_depth > 500:
                status = HealthStatus.DEGRADED
                message = f"Queue depth high: {queue_depth} messages"
            else:
                status = HealthStatus.HEALTHY
                message = f"Queue processing normally"
            
            return ComponentHealth(
                name="message_queue",
                status=status,
                message=message,
                details={
                    "queue_depth": queue_depth,
                    "processing_rate_per_sec": processing_rate,
                    "consumer_count": 3
                }
            )
    
    # Security health check
    class SecurityHealthCheck:
        async def check_security_status(self) -> ComponentHealth:
            """Check security-related health."""
            # Simulate security checks
            cert_expiry_days = random.randint(10, 365)
            failed_login_attempts = random.randint(0, 100)
            
            if cert_expiry_days < 30:
                status = HealthStatus.DEGRADED
                message = f"SSL certificate expires in {cert_expiry_days} days"
            elif failed_login_attempts > 50:
                status = HealthStatus.DEGRADED
                message = f"High failed login attempts: {failed_login_attempts}"
            else:
                status = HealthStatus.HEALTHY
                message = "Security status normal"
            
            return ComponentHealth(
                name="security",
                status=status,
                message=message,
                details={
                    "cert_expiry_days": cert_expiry_days,
                    "failed_logins_1h": failed_login_attempts,
                    "rate_limit_active": True
                }
            )
    
    # Run custom health checks
    business_checker = BusinessHealthCheck()
    queue_checker = QueueHealthCheck()
    security_checker = SecurityHealthCheck()
    
    custom_checks = await asyncio.gather(
        business_checker.check_critical_business_logic(),
        queue_checker.check_message_queue(),
        security_checker.check_security_status()
    )
    
    print(f"  Custom Health Check Results:")
    for check in custom_checks:
        status_icon = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}
        icon = status_icon.get(check.status.value, "❓")
        
        print(f"    {icon} {check.name}: {check.message}")
        if check.details:
            for key, value in check.details.items():
                print(f"       {key}: {value}")


async def main():
    """Run the complete health checks demo."""
    print_banner("Health Checks Demo")
    print("This demo showcases health monitoring and checking capabilities.")
    
    try:
        # Basic health check
        await demo_basic_health_check()
        
        # Detailed health check
        await demo_detailed_health_check()
        
        # Kubernetes probes
        await demo_kubernetes_probes()
        
        # Health monitoring
        await demo_health_monitoring()
        
        # Custom health checks
        await demo_custom_health_checks()
        
        print_banner("Health Checks Demo Complete")
        print("✓ All health check features demonstrated successfully!")
        print("\nKey Features Covered:")
        print("- Basic health check endpoints for load balancers")
        print("- Detailed component health monitoring")
        print("- Kubernetes liveness and readiness probes")
        print("- External dependency health checking")
        print("- Health status aggregation and determination")
        print("- Custom business logic health checks")
        print("- Health monitoring patterns and best practices")
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        raise


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())