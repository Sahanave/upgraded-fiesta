#!/usr/bin/env python3
"""
Test script to verify backend setup before deployment
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test FastAPI imports
        from fastapi import FastAPI
        print("✅ FastAPI imported successfully")
        
        # Test data models
        from data_models import SlideContent, LiveUpdate, DocumentSummary, UploadResult
        print("✅ Data models imported successfully")
        
        # Test main module
        import main
        print("✅ Main module imported successfully")
        
        # Test if app is defined
        if hasattr(main, 'app'):
            print("✅ FastAPI app found")
        else:
            print("❌ FastAPI app not found")
            return False
            
        # Test OpenAI (optional)
        try:
            from openai import OpenAI
            print("✅ OpenAI client available")
        except ImportError:
            print("⚠️ OpenAI client not available (but that's okay)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_file_structure():
    """Test that all required files are present"""
    print("\n📁 Testing file structure...")
    
    cwd = Path.cwd()
    print(f"Current directory: {cwd}")
    
    required_files = [
        "main.py",
        "data_models.py", 
        "requirements-minimal.txt",
        "start.py"
    ]
    
    all_present = True
    for file in required_files:
        file_path = cwd / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} missing")
            all_present = False
    
    return all_present

def test_environment():
    """Test environment variables"""
    print("\n🌍 Testing environment...")
    
    port = os.getenv("PORT", "8000")
    print(f"PORT: {port}")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not set'}")
    
    python_version = sys.version
    print(f"Python version: {python_version}")
    
    return True

def main():
    """Run all tests"""
    print("🎯 Backend Deployment Test")
    print("=" * 40)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Environment", test_environment)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
                all_passed = False
        except Exception as e:
            print(f"💥 {test_name} test ERROR: {e}")
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests PASSED! Backend is ready for deployment.")
        return 0
    else:
        print("❌ Some tests FAILED. Please fix issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 