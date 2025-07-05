#!/usr/bin/env python3
"""
Quick Backend Connection Test
Tests if the backend is running and responding
"""

import requests
import time
import sys

def test_backend_connection():
    """Test if backend is running and responding"""
    print("🔍 Testing Backend Connection...")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test basic connection
    try:
        print("📡 Testing basic connection...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("✅ Backend is running!")
            data = response.json()
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend")
        print("   Make sure the backend is running: python start_backend.py")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    
    # Test API endpoints
    endpoints_to_test = [
        ("/api/slides", "Slides endpoint"),
        ("/api/document-summary", "Document summary endpoint"),
        ("/api/voice/status", "Voice status endpoint")
    ]
    
    print("\n🧪 Testing API endpoints...")
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code in [200, 404] else "❌"
            print(f"   {status} {description}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {description}: Error - {e}")
    
    print("\n🎉 Backend connection test complete!")
    return True

def wait_for_backend(max_wait=30):
    """Wait for backend to start up"""
    print(f"⏳ Waiting for backend to start (max {max_wait}s)...")
    
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/", timeout=2)
            if response.status_code == 200:
                print(f"✅ Backend ready after {i+1}s!")
                return True
        except:
            pass
        
        time.sleep(1)
        if i % 5 == 4:  # Print progress every 5 seconds
            print(f"   Still waiting... ({i+1}s)")
    
    print("❌ Backend did not start within timeout")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        # Wait for backend to start, then test
        if wait_for_backend():
            test_backend_connection()
    else:
        # Just test connection
        test_backend_connection()