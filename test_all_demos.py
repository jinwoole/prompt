#!/usr/bin/env python3
"""
Comprehensive Demo Verification Script

This script tests all demo files to ensure they work properly with the
Docker Compose infrastructure (PostgreSQL and Redis).
"""
import asyncio
import subprocess
import sys
import time
from pathlib import Path


def print_banner(title: str):
    """Print a banner for the test section."""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_test_result(demo_name: str, success: bool, output: str = "", error: str = ""):
    """Print test result with formatting."""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"\n{status} {demo_name}")
    
    if success:
        print(f"   Demo completed successfully")
        if output:
            # Show first few lines of output
            lines = output.strip().split('\n')[:5]
            for line in lines:
                print(f"   > {line[:60]}{'...' if len(line) > 60 else ''}")
    else:
        print(f"   Error: {error}")
        if output:
            # Show last few lines of output for debugging
            lines = output.strip().split('\n')[-3:]
            for line in lines:
                print(f"   > {line}")


def test_infrastructure():
    """Test that PostgreSQL and Redis are accessible."""
    print_banner("Testing Infrastructure")
    
    # Test PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="fastapi_db", 
            user="postgres",
            password="password"
        )
        conn.close()
        print("✓ PostgreSQL connection successful")
        postgres_ok = True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        postgres_ok = False
    
    # Test Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis connection successful")
        redis_ok = True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        redis_ok = False
    
    return postgres_ok, redis_ok


def run_demo(demo_file: str) -> tuple[bool, str, str]:
    """Run a demo file and return success status, output, and error."""
    try:
        # Set timeout to 60 seconds per demo
        result = subprocess.run(
            [sys.executable, f"examples/{demo_file}"],
            cwd="/home/runner/work/tmp/tmp",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        success = result.returncode == 0
        output = result.stdout
        error = result.stderr if not success else ""
        
        return success, output, error
        
    except subprocess.TimeoutExpired:
        return False, "", "Demo timed out after 60 seconds"
    except Exception as e:
        return False, "", f"Failed to run demo: {str(e)}"


def main():
    """Main test function."""
    print_banner("FastAPI Enterprise Demo Verification")
    
    print("""
🔍 This script verifies that all demo scripts work properly with 
   the Docker Compose infrastructure setup.
   
   Prerequisites:
   - PostgreSQL running on localhost:5432
   - Redis running on localhost:6379
   - Python dependencies installed
""")
    
    # Test infrastructure first
    postgres_ok, redis_ok = test_infrastructure()
    
    if not postgres_ok or not redis_ok:
        print("\n❌ Infrastructure tests failed. Please ensure Docker services are running:")
        print("   docker compose up -d postgres redis")
        return False
    
    # List of all demo files to test
    demo_files = [
        "demo_overview.py",
        "demo.py", 
        "demo_authentication.py",
        "demo_webauthn.py",
        "demo_caching.py",
        "demo_rate_limiting.py",
        "demo_metrics.py",
        "demo_health_checks.py",
        "demo_items_api.py"
    ]
    
    print_banner("Running Demo Tests")
    
    results = {}
    total_demos = len(demo_files)
    passed_demos = 0
    
    for demo_file in demo_files:
        print(f"\n🧪 Testing {demo_file}...")
        
        # Check if file exists
        demo_path = Path(f"/home/runner/work/tmp/tmp/examples/{demo_file}")
        if not demo_path.exists():
            print_test_result(demo_file, False, error=f"File not found: {demo_path}")
            results[demo_file] = False
            continue
        
        # Run the demo
        success, output, error = run_demo(demo_file)
        print_test_result(demo_file, success, output, error)
        
        results[demo_file] = success
        if success:
            passed_demos += 1
        
        # Brief pause between tests
        time.sleep(1)
    
    # Print summary
    print_banner("Test Summary")
    
    print(f"\n📊 Results: {passed_demos}/{total_demos} demos passed")
    
    # Show detailed results
    for demo_file, success in results.items():
        status = "✓" if success else "✗"
        print(f"   {status} {demo_file}")
    
    success_rate = (passed_demos / total_demos) * 100
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if passed_demos == total_demos:
        print("\n🎉 All demos passed! The enterprise features are working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_demos - passed_demos} demo(s) failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)