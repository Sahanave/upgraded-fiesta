#!/usr/bin/env python3
"""
Test script for enhanced Study Buddy features:
- ElevenLabs conversation agent
- PDF figure extraction
- Enhanced slide generation with visuals
"""

import requests
import time
import json
import os
from pathlib import Path

# Configuration
BACKEND_URL = "https://study-buddy-bolt.onrender.com"  # Update with your actual backend URL
TEST_PDF_PATH = "NIPS-2017-attention-is-all-you-need-Paper.pdf"  # Update with a test PDF

def test_backend_connection():
    """Test basic backend connectivity"""
    print("🔍 Testing backend connection...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend connected: {data['message']}")
            print(f"🎯 Available features: {data['features']}")
            return True
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_elevenlabs_voice_system():
    """Test ElevenLabs voice system endpoints"""
    print("\n🎙️ Testing ElevenLabs Voice System...")
    
    # Test voice status
    try:
        response = requests.get(f"{BACKEND_URL}/api/voice/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ElevenLabs voice agent available: {data['voice_agent_available']}")
            print(f"📊 Total slides: {data['total_slides']}")
            
            # Check for ElevenLabs-specific features
            if 'voice_options' in data and data['voice_options']:
                voice_info = data['voice_options']
                print(f"🎤 Voice: {voice_info.get('voice_name', 'Adam')}")
                print(f"🏢 Provider: {voice_info.get('provider', 'elevenlabs_only')}")
                print(f"🎯 Features: TTS: {voice_info.get('features', {}).get('tts', True)}, STT: {voice_info.get('features', {}).get('stt', True)}, Conversation: {voice_info.get('features', {}).get('conversation', True)}")
        else:
            print(f"⚠️ Voice status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Voice status error: {e}")
    
    # Test ElevenLabs conversation processing
    try:
        test_question = {
            "question": "Can you explain the main concept of this paper?",
            "slideContext": {
                "title": "Introduction",
                "content": "This slide introduces the main concepts and methodology."
            },
            "documentContext": {
                "title": "Research Paper",
                "abstract": "This paper presents novel approaches to machine learning.",
                "main_topics": ["machine learning", "neural networks", "attention mechanisms"]
            }
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/voice/conversation",
            json=test_question,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ElevenLabs conversation processing works!")
            print(f"🤖 AI Response: {data['answer'][:100]}...")
            print(f"🎯 Confidence: {data['confidence']}")
            print(f"⏱️ Estimated duration: {data.get('estimated_duration', 'N/A')}s")
        else:
            print(f"⚠️ Conversation processing failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Conversation test error: {e}")

def test_elevenlabs_tts():
    """Test ElevenLabs text-to-speech generation"""
    print("\n🔊 Testing ElevenLabs TTS Generation...")
    
    try:
        test_data = {
            "text": "Hello! This is a test of the ElevenLabs voice system. The audio quality should be natural and conversational."
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/voice/speak",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ ElevenLabs TTS generation successful!")
            print(f"📊 Audio size: {len(response.content)} bytes")
            print(f"🎙️ Voice: Adam (ElevenLabs)")
            
            # Save audio file for testing
            with open("test_elevenlabs_audio.mp3", "wb") as f:
                f.write(response.content)
            print(f"💾 Audio saved as test_elevenlabs_audio.mp3")
            
        else:
            print(f"⚠️ ElevenLabs TTS generation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ ElevenLabs TTS test error: {e}")

def test_pdf_upload_and_figures():
    """Test PDF upload with figure extraction"""
    print("\n📄 Testing PDF upload with figure extraction...")
    
    if not os.path.exists(TEST_PDF_PATH):
        print(f"⚠️ Test PDF not found: {TEST_PDF_PATH}")
        print("📋 To test figure extraction, place a PDF file in the backend directory")
        return
    
    try:
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (TEST_PDF_PATH, f, 'application/pdf')}
            
            response = requests.post(
                f"{BACKEND_URL}/api/upload",
                files=files
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PDF upload successful!")
            print(f"📊 File: {data['filename']}")
            print(f"📄 Pages: {data['pages']}")
            print(f"⏱️ Processing time: {data['processingTime']}")
            print(f"🎯 Key topics: {data['keyTopics']}")
            
            if "figures" in data['message']:
                print(f"🖼️ Figures extracted successfully!")
                
        else:
            print(f"⚠️ PDF upload failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ PDF upload error: {e}")

def test_enhanced_slide_generation():
    """Test enhanced slide generation with figures"""
    print("\n🎯 Testing enhanced slide generation...")
    
    # First generate Q&A pairs
    try:
        response = requests.post(f"{BACKEND_URL}/api/generate-qa")
        if response.status_code == 200:
            qa_pairs = response.json()
            print(f"✅ Generated {len(qa_pairs)} Q&A pairs")
        else:
            print(f"⚠️ Q&A generation failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Q&A generation error: {e}")
        return
    
    # Then generate enhanced slides
    try:
        response = requests.post(f"{BACKEND_URL}/api/generate-slides")
        if response.status_code == 200:
            slides = response.json()
            print(f"✅ Generated {len(slides)} enhanced slides!")
            
            # Check for visual enhancements
            for i, slide in enumerate(slides[:3]):  # Check first 3 slides
                print(f"\n📊 Slide {i+1}: {slide['title']}")
                print(f"   📝 Content: {slide['content'][:100]}...")
                print(f"   🖼️ Visual description: {slide.get('image_description', 'None')[:100]}...")
                
        else:
            print(f"⚠️ Enhanced slide generation failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Enhanced slide generation error: {e}")

def test_slide_metadata():
    """Test slide metadata including visual information"""
    print("\n📊 Testing slide metadata...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/slides/metadata")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Slide metadata retrieved!")
            print(f"📄 Total slides: {data['total_slides']}")
            print(f"🎵 Has audio: {data['has_audio']}")
            print(f"🔊 Cached audio slides: {data['cached_slides']}")
            
        else:
            print(f"⚠️ Slide metadata failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Slide metadata error: {e}")

def main():
    """Run all enhanced feature tests"""
    print("🚀 Testing Enhanced Study Buddy Features")
    print("🎙️ ElevenLabs Voice Architecture (TTS + STT + Conversation)")
    print("=" * 60)
    
    # Test basic connectivity
    if not test_backend_connection():
        print("❌ Backend connection failed. Cannot proceed with tests.")
        return
    
    # Test ElevenLabs voice system
    test_elevenlabs_voice_system()
    
    # Test ElevenLabs TTS generation
    test_elevenlabs_tts()
    
    # Test PDF upload with figure extraction
    test_pdf_upload_and_figures()
    
    # Test enhanced slide generation
    test_enhanced_slide_generation()
    
    # Test slide metadata
    test_slide_metadata()
    
    print("\n✅ Enhanced feature testing complete!")
    print("\n💡 ElevenLabs Voice System Features:")
    print("   🔊 Text-to-Speech: Natural, conversational audio using Adam voice")
    print("   🎤 Speech-to-Text: High-quality transcription for voice questions")
    print("   💬 AI Conversation: Context-aware responses using ElevenLabs conversation API")
    print("   📝 Complete Flow: STT → AI Processing → TTS in one seamless experience")
    print("   🎯 100% ElevenLabs: No OpenAI dependencies for voice features")
    print("\n📋 Other Features:")
    print("   1. Upload a PDF to extract figures automatically")
    print("   2. Use the microphone button to ask questions during presentations") 
    print("   3. Technical slides automatically suggest visual diagrams")
    print("   4. Extracted PDF figures are integrated into relevant slides")

if __name__ == "__main__":
    # Allow customization of backend URL
    if len(os.sys.argv) > 1:
        BACKEND_URL = os.sys.argv[1]
        print(f"Using custom backend URL: {BACKEND_URL}")
    
    main()