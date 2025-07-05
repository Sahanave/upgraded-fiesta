#!/usr/bin/env python3
"""
Backend Startup Script
Starts the FastAPI backend server with proper configuration
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'PyPDF2',
        'pydantic',
        'python-multipart',
        'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("📦 Install with: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Start the backend server"""
    load_dotenv()
    
    print("🚀 Starting Study Buddy Backend with ElevenLabs Voice")
    print("=" * 55)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n💡 To fix this:")
        print("   cd backend")
        print("   pip install -r requirements.txt")
        print("   python start_backend.py")
        sys.exit(1)
    
    # Check for ElevenLabs API key (primary for voice features)
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    if not elevenlabs_key:
        print("⚠️  Warning: ELEVENLABS_API_KEY not found in environment")
        print("   Set it in .env file for voice features (TTS, STT, Conversation)")
        print("   Voice features will be disabled without this key")
    else:
        print("✅ ElevenLabs API key configured (voice features enabled)")
    
    # Check for OpenAI API key (optional)
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print("✅ OpenAI API key configured (additional features available)")
    else:
        print("ℹ️  OpenAI API key not set (optional for additional features)")
    
    print("\n📡 Starting server on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    print("🔄 Auto-reload enabled for development")
    print("🛑 Press Ctrl+C to stop the server")
    print("\n" + "=" * 50)
    
    try:
        # Start the server
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check if port 8000 is already in use")
        print("   2. Verify all dependencies are installed")
        print("   3. Check the error message above")

if __name__ == "__main__":
    main()