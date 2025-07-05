#!/usr/bin/env python3
"""
Backend Health Check Script
Quick script to verify if the backend is running and accessible
"""

import requests
import sys
import time

def check_backend_health():
    """Check if backend is healthy and responding"""
    urls_to_check = [
        'http://localhost:8000',
        'http://127.0.0.1:8000'
    ]
    
    print("🏥 Backend Health Check")
    print("=" * 30)
    
    for url in urls_to_check:
        print(f"\n🔍 Testing: {url}")
        
        try:
            # Test basic connectivity
            response = requests.get(f"{url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Backend is healthy!")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Message: {data.get('message', 'No message')}")
                
                # Test additional endpoints
                endpoints_to_test = [
                    ("/", "Root endpoint"),
                    ("/docs", "API documentation")
                ]
                
                for endpoint, description in endpoints_to_test:
                    try:
                        test_response = requests.get(f"{url}{endpoint}", timeout=3)
                        status = "✅" if test_response.status_code == 200 else "⚠️"
                        print(f"   {status} {description}: {test_response.status_code}")
                    except:
                        print(f"   ❌ {description}: Failed")
                
                return True
            else:
                print(f"❌ Backend returned status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect - server may not be running")
        except requests.exceptions.Timeout:
            print(f"❌ Connection timeout - server may be overloaded")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n💡 To start the backend:")
    print(f"   cd backend")
    print(f"   python start_server.py")
    
    return False

if __name__ == "__main__":
    is_healthy = check_backend_health()
    sys.exit(0 if is_healthy else 1)