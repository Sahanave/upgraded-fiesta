#!/usr/bin/env python3
"""
Quick Backend Test
Tests basic functionality without requiring a PDF upload
"""

import sys
import os
from dotenv import load_dotenv

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing Python imports...")
    
    try:
        import fastapi
        print("✅ FastAPI available")
    except ImportError:
        print("❌ FastAPI not installed: pip install fastapi")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn available")
    except ImportError:
        print("❌ Uvicorn not installed: pip install uvicorn")
        return False
    
    try:
        import openai
        print("✅ OpenAI library available")
    except ImportError:
        print("❌ OpenAI not installed: pip install openai")
        return False
    
    try:
        import PyPDF2
        print("✅ PyPDF2 available")
    except ImportError:
        print("❌ PyPDF2 not installed: pip install PyPDF2")
        return False
    
    return True

def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing environment...")
    
    load_dotenv()
    
    # Test ElevenLabs API key (primary for voice features)
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    elevenlabs_configured = elevenlabs_key and len(elevenlabs_key) > 10
    
    # Test OpenAI API key (optional for some features)
    openai_key = os.getenv('OPENAI_API_KEY')
    openai_configured = openai_key and openai_key.startswith('sk-')
    
    if elevenlabs_configured:
        print("✅ ElevenLabs API key configured (voice features available)")
    else:
        print("⚠️ ElevenLabs API key not configured")
        print("   Set ELEVENLABS_API_KEY in .env file for voice features")
    
    if openai_configured:
        print("✅ OpenAI API key configured (additional features available)")
    else:
        print("⚠️ OpenAI API key not configured (some features may be limited)")
    
    # Return True if at least ElevenLabs is configured
    return elevenlabs_configured

def test_backend_modules():
    """Test if backend modules can be imported"""
    print("\n📦 Testing backend modules...")
    
    try:
        from main import app
        print("✅ Main FastAPI app can be imported")
    except Exception as e:
        print(f"❌ Error importing main app: {e}")
        return False
    
    try:
        from data_models import SlideContent, DocumentSummary
        print("✅ Data models available")
    except Exception as e:
        print(f"❌ Error importing data models: {e}")
        return False
    
    try:
        from parsing_info_from_pdfs import generate_summary
        print("✅ PDF parsing functions available")
    except Exception as e:
        print(f"❌ Error importing PDF functions: {e}")
        return False
    
    try:
        from voice_conversation import voice_agent
        if voice_agent:
            print("✅ ElevenLabs voice agent available")
        else:
            print("⚠️ Voice agent not initialized (likely missing ELEVENLABS_API_KEY)")
    except Exception as e:
        print(f"⚠️ Voice agent import issue: {e}")
        print("   Voice features may not be available")
    
    return True

def test_elevenlabs_voice():
    """Test ElevenLabs voice agent functionality"""
    print("\n🎙️ Testing ElevenLabs voice system...")
    
    try:
        from voice_conversation import voice_agent
        
        if not voice_agent:
            print("⚠️ ElevenLabs voice agent not available")
            print("   Configure ELEVENLABS_API_KEY for voice features")
            return False
        
        # Test voice info
        voice_info = voice_agent.get_voice_info()
        print(f"✅ ElevenLabs voice agent ready")
        print(f"   Voice: {voice_info['voice_name']} ({voice_info['voice_id']})")
        print(f"   Provider: {voice_info['provider']}")
        print(f"   Features: TTS={voice_info['features']['tts']}, STT={voice_info['features']['stt']}, Conversation={voice_info['features']['conversation']}")
        return True
        
    except Exception as e:
        print(f"❌ ElevenLabs voice test failed: {e}")
        print("   Check your ELEVENLABS_API_KEY and internet connection")
        return False

def main():
    """Run all tests"""
    print("🧪 Quick Backend Test")
    print("=" * 40)
    
    tests = [
        ("Python Imports", test_imports),
        ("Environment", test_environment),
        ("Backend Modules", test_backend_modules),
        ("ElevenLabs Voice", test_elevenlabs_voice)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Backend is ready to run.")
        print("   Start with: python start_backend.py")
        print("🎙️ ElevenLabs voice system fully operational!")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("   Install missing dependencies: pip install -r requirements.txt")
        print("   Configure .env file with your ELEVENLABS_API_KEY for voice features")
        print("   Optionally add OPENAI_API_KEY for additional functionality")

if __name__ == "__main__":
    main()