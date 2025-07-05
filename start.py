#!/usr/bin/env python3
"""
Root-level startup script for Render deployment
This script navigates to the backend directory and starts the application
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Navigate to backend directory and start the application"""
    print("🎯 Study Buddy Root Startup Script")
    print("=" * 50)
    
    # Get current working directory
    cwd = Path.cwd()
    print(f"📁 Current working directory: {cwd}")
    
    # Navigate to backend directory
    backend_dir = cwd / "backend"
    if backend_dir.exists():
        print(f"✅ Found backend directory: {backend_dir}")
        os.chdir(backend_dir)
        print(f"📁 Changed to backend directory: {Path.cwd()}")
    else:
        print(f"❌ Backend directory not found: {backend_dir}")
        print("📋 Available directories:")
        for item in cwd.iterdir():
            if item.is_dir():
                print(f"  - {item.name}")
        sys.exit(1)
    
    # Check if main.py exists in backend directory
    main_py = Path.cwd() / "main.py"
    if main_py.exists():
        print("✅ main.py found in backend directory")
    else:
        print("❌ main.py not found in backend directory")
        sys.exit(1)
    
    # Get port from environment
    port = os.getenv("PORT", "8000")
    print(f"🌐 Using port: {port}")
    
    # Start the application
    print("🚀 Starting FastAPI application...")
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", port
        ]
        
        print(f"📋 Running command: {' '.join(cmd)}")
        print("=" * 50)
        
        # Execute the command
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1) 