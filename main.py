from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import PyPDF2
import io
import time
import os
import tempfile
from datetime import datetime
from data_models import SlideContent, LiveUpdate, DocumentSummary, UploadResult
from dotenv import load_dotenv
from fastapi.responses import JSONResponse, StreamingResponse
from io import BytesIO
import asyncio
import requests
try:
    from voice_conversation import voice_agent
    if voice_agent is None:
        print("⚠️ Voice agent not available - voice features will be limited")
except Exception as e:
    print(f"⚠️ Failed to import voice agent: {e}")
    voice_agent = None
# Chart service removed for simplicity

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Are You Taking Notes API", 
    version="1.0.0",
    # Increase timeout to handle long processing
    timeout=300  # 5 minutes
)

# Initialize OpenAI client
openai_client = None
vector_store_id = None
current_document_summary = None
current_qa_pairs = []

try:
    from openai import OpenAI
    import os
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        print("✅ OpenAI client initialized successfully")
    else:
        print("⚠️ OpenAI API key not set - slide generation and document processing features disabled")
        print("Set OPENAI_API_KEY environment variable to enable AI features")
except Exception as e:
    print(f"⚠️ OpenAI client not initialized: {e}")
    print("Set OPENAI_API_KEY environment variable to enable AI features")

# Enable CORS for frontend
cors_origins = [
    "http://localhost:5173", 
    "http://localhost:3000", 
    "http://127.0.0.1:5173",
    "https://bolt.new",
    "https://super-semifreddo-9dcd1f.netlify.app",
    "https://super-semifreddo-9dcd1f.netlify.app/",
    "https://study-buddy-for-me-and-you.site",
    "https://zp1v56uxy8rdx5ypatb0ockcb9tr6a-oci3--5173--9a8902a0.local-credentialless.webcontainer-api.io",
    os.getenv("FRONTEND_URL", ""),
]

# Filter out empty strings and add any additional origins from env
if os.getenv("CORS_ORIGINS"):
    cors_origins.extend(os.getenv("CORS_ORIGINS").split(","))

# Remove empty strings from cors_origins
cors_origins = [origin for origin in cors_origins if origin]

print(f"🌐 CORS enabled for origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Generated slides storage
sample_slides = []

# Audio storage for slides
slide_audio_cache = {}

# Extracted figures storage
extracted_figures = []

# Conversation history storage (in production, use Redis or database)
conversation_sessions = {}

sample_live_updates = [
    LiveUpdate(
        message="Backend is online and ready for document processing",
        timestamp=datetime.now().isoformat(),
        type="info"
    ),
    LiveUpdate(
        message="AI features available with OpenAI integration",
        timestamp=datetime.now().isoformat(),
        type="announcement"
    ),
    LiveUpdate(
        message="ElevenLabs voice conversation agent ready",
        timestamp=datetime.now().isoformat(),
        type="info"
    )
]

sample_document_summary = DocumentSummary(
    title="No Document Uploaded",
    abstract="Upload a PDF document to begin AI-powered analysis and presentation generation.",
    key_points=[
        "Upload PDF documents for analysis",
        "Generate Q&A pairs automatically",
        "Create presentation slides from content",
                    "Voice narration with ElevenLabs TTS",
        "Interactive voice conversations with ElevenLabs"
    ],
    main_topics=[
        "Document Analysis",
        "AI Processing",
        "Presentation Generation",
        "Voice Synthesis",
        "Interactive Conversations"
    ],
    difficulty_level="intermediate",
    estimated_read_time="0 minutes",
    document_type="system",
    authors=["Backend System"],
    publication_date=datetime.now().strftime("%Y-%m-%d")
)

# Rate limiting for ElevenLabs API (max 4 concurrent requests to stay under 5 limit)
ELEVENLABS_SEMAPHORE = asyncio.Semaphore(4)

# Helper Functions
async def generate_audio_for_slide(slide: SlideContent) -> tuple[int, bytes | None]:
    """Generate audio for a single slide with rate limiting"""
    async with ELEVENLABS_SEMAPHORE:  # Limit concurrent requests
        try:
            # Use speaker notes for more natural narration, fallback to content if no notes
            narration_text = slide.speaker_notes or f"{slide.title}. {slide.content}"
            
            if not voice_agent:
                print(f"⚠️ Voice agent not available for slide {slide.slide_number}")
                return slide.slide_number, None
            
            print(f"🎙️ Generating audio for slide {slide.slide_number} (concurrent limit: 4)")
            audio_content = await voice_agent.generate_speech(narration_text)
            print(f"✅ Generated audio for slide {slide.slide_number} using ElevenLabs SDK")
            return slide.slide_number, audio_content
            
        except Exception as e:
            print(f"⚠️ ElevenLabs voice generation failed for slide {slide.slide_number}: {e}")
            return slide.slide_number, None

async def generate_audio_for_all_slides(slides: List[SlideContent]) -> None:
    """Generate audio files for all slides in parallel and cache them"""
    global slide_audio_cache
    
    if not voice_agent:
        print("⚠️ Voice agent not available, skipping audio generation")
        return
    
    print(f"🎙️ Generating audio for {len(slides)} slides in parallel (max 4 concurrent to avoid 429 errors)...")
    slide_audio_cache.clear()
    
    try:
        # Create tasks for all slides to run in parallel
        tasks = [generate_audio_for_slide(slide) for slide in slides]
        
        # Execute all audio generation tasks simultaneously
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update cache
        successful_count = 0
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Audio generation task failed: {result}")
                continue
                
            slide_number, audio_content = result
            if audio_content:
                slide_audio_cache[slide_number] = audio_content
                successful_count += 1
            else:
                print(f"⚠️ Failed to generate audio for slide {slide_number}")
        
        print(f"🎉 Rate-limited parallel audio generation complete! Generated audio for {successful_count}/{len(slides)} slides")
        print(f"⚡ Performance: {len(slides)} slides processed in batches of 4 (avoiding 429 rate limit errors)")
        
    except Exception as e:
        print(f"❌ Parallel audio generation failed: {e}")

def get_slide_audio(slide_number: int) -> Optional[bytes]:
    """Get cached audio for a specific slide"""
    return slide_audio_cache.get(slide_number)

def reset_all_context():
    """Complete context reset - clear ALL cached data and state"""
    global sample_slides, slide_audio_cache, extracted_figures, current_qa_pairs
    global vector_store_id, current_document_summary, conversation_sessions
    
    # Clear all content caches
    sample_slides.clear()
    slide_audio_cache.clear()
    extracted_figures.clear()
    current_qa_pairs.clear()
    conversation_sessions.clear()
    
    # Reset document-specific state
    vector_store_id = None
    current_document_summary = None
    
    print("🧹 COMPLETE CONTEXT RESET: Cleared all slides, audio, figures, Q&A pairs, conversations, and document state")

def clear_slide_cache():
    """Legacy function - use reset_all_context() for complete reset"""
    reset_all_context()

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Are You Taking Notes API is running!",
        "status": "online",
        "version": "1.0.0",
        "features": {
            "openai_available": openai_client is not None,
            "elevenlabs_available": voice_agent.elevenlabs_available if voice_agent else False,
            "pdf_processing": True,
            "voice_generation": voice_agent is not None,
            "voice_conversation": voice_agent is not None,
            "slide_generation": openai_client is not None,
            "chart_generation": False,
            "antv_charts": False
        }
    }

@app.options("/")
async def options_root():
    """Handle OPTIONS request for root endpoint"""
    return {"message": "CORS preflight successful"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_available": openai_client is not None,
        "elevenlabs_available": voice_agent.elevenlabs_available if voice_agent else False,
        "voice_features": voice_agent.get_voice_info() if voice_agent else None
    }

@app.options("/health")
async def options_health():
    """Handle CORS preflight for health endpoint"""
    return {"status": "ok"}

@app.get("/api/slides", response_model=List[SlideContent])
async def get_slides():
    """Get all presentation slides"""
    return sample_slides

@app.get("/api/slides/metadata")
async def get_slides_metadata():
    """Get slide metadata including total count"""
    return {
        "total_slides": len(sample_slides),
        "available_slides": [slide.slide_number for slide in sample_slides],
        "has_audio": len(slide_audio_cache) > 0,
        "cached_audio_slides": list(slide_audio_cache.keys()),
        "has_figures": len(extracted_figures) > 0,
        "figure_count": len(extracted_figures)
    }

@app.get("/api/slides/{slide_number}", response_model=SlideContent)
async def get_slide(slide_number: int):
    """Get a specific slide by number"""
    for slide in sample_slides:
        if slide.slide_number == slide_number:
            return slide
    
    raise HTTPException(status_code=404, detail=f"Slide {slide_number} not found")

@app.get("/api/figures/{index}")
async def get_figure(index: str):
    """Get a specific figure by index"""
    global extracted_figures
    
    # Handle null/invalid index values
    if index == "null" or index == "undefined" or not index:
        raise HTTPException(status_code=400, detail="Invalid figure index: cannot be null or undefined")
    
    # Convert string to integer
    try:
        index_int = int(index)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid figure index '{index}': must be a valid integer")
    
    if not extracted_figures:
        raise HTTPException(status_code=404, detail="No figures available")
    
    if index_int < 0 or index_int >= len(extracted_figures):
        raise HTTPException(status_code=404, detail=f"Figure index {index_int} out of range (0-{len(extracted_figures)-1})")
    
    try:
        figure = extracted_figures[index_int]
        if not figure.get("data"):
            raise HTTPException(status_code=404, detail="Figure data not found")
        
        import base64
        image_data = base64.b64decode(figure["data"])
        
        return StreamingResponse(
            BytesIO(image_data),
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=figure_{index_int}.png",
                "Cache-Control": "max-age=3600"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve figure: {str(e)}")

@app.options("/api/figures/{index}")
async def options_figure(index: str):
    """Handle CORS preflight for figures endpoint"""
    return {"status": "ok"}

@app.get("/api/figures")
async def get_figures_list():
    """Get list of available figures"""
    global extracted_figures
    
    if not extracted_figures:
        return {"count": 0, "figures": []}
    
    figure_list = []
    for i, figure in enumerate(extracted_figures):
        figure_list.append({
            "index": i,
            "caption": figure.get("caption", f"Figure {i+1}"),
            "page": figure.get("page", "Unknown"),
            "bbox": figure.get("bbox", []),
            "has_data": bool(figure.get("data"))
        })
    
    return {"count": len(extracted_figures), "figures": figure_list}

@app.get("/api/live-updates", response_model=List[LiveUpdate])
async def get_live_updates():
    """Get live updates and announcements"""
    return sample_live_updates

@app.get("/api/document-summary", response_model=DocumentSummary)
async def get_document_summary():
    """Get summary of the document being discussed"""
    if current_document_summary:
        return current_document_summary
    return sample_document_summary

@app.post("/api/generate-qa", response_model=List[dict])
async def generate_qa_pairs(use_current_document: bool = True):
    """Generate Q&A pairs from the currently uploaded document"""
    global current_document_summary, vector_store_id, current_qa_pairs
    
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured")
    
    if not current_document_summary:
        raise HTTPException(status_code=400, detail="No document summary available. Please upload a document first.")
    
    try:
        from parsing_info_from_pdfs import generate_qa_pairs_from_document
        
        if vector_store_id:
            qa_pairs = generate_qa_pairs_from_document(
                client=openai_client,
                summary=current_document_summary,
                vector_store_id=vector_store_id
            )
        else:
            qa_pairs = [
                {
                    "question": f"What is the main topic of {current_document_summary.title}?",
                    "answer": current_document_summary.abstract,
                    "question_number": 1
                },
                {
                    "question": "What are the key points discussed?",
                    "answer": ". ".join(current_document_summary.key_points),
                    "question_number": 2
                }
            ]
        
        current_qa_pairs = qa_pairs
        return qa_pairs
        
    except Exception as e:
        print(f"Error generating Q&A pairs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Q&A pairs: {str(e)}")

@app.get("/api/qa-pairs", response_model=List[dict])
async def get_qa_pairs():
    """Get the current Q&A pairs for the uploaded document"""
    global current_qa_pairs
    return current_qa_pairs if current_qa_pairs else []

@app.post("/api/generate-slides", response_model=List[SlideContent])
async def generate_slides_from_qa():
    """Generate slides based on Q&A pairs from the uploaded document"""
    global openai_client, current_document_summary, current_qa_pairs, vector_store_id, sample_slides, extracted_figures
    
    print(f"🔄 Generate slides request received")
    # Clear previous slides and audio to ensure fresh generation (keep document state)
    global sample_slides, slide_audio_cache
    sample_slides.clear()
    slide_audio_cache.clear()
    print("🧹 Cleared slides and audio cache for fresh slide generation")
    start_time = time.time()
    
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured")
    
    if not current_document_summary:
        raise HTTPException(status_code=400, detail="No document summary available. Please upload a PDF document first.")
    
    try:
        from parsing_info_from_pdfs import generate_qa_pairs_from_document, generate_slides_from_qa_pairs
        
        if not current_qa_pairs:
            print(f"🔄 No Q&A pairs found, generating them first...")
            if vector_store_id:
                current_qa_pairs = generate_qa_pairs_from_document(
                    client=openai_client,
                    summary=current_document_summary,
                    vector_store_id=vector_store_id
                )
            else:
                current_qa_pairs = [
                    {
                        "question": f"What is {current_document_summary.title} about?",
                        "answer": current_document_summary.abstract,
                        "question_number": 1
                    }
                ]
            print(f"✅ Generated {len(current_qa_pairs)} Q&A pairs")
        
        print(f"🎯 Generating slides from {len(current_qa_pairs)} Q&A pairs...")
        
        slides = generate_slides_from_qa_pairs(
            client=openai_client,
            qa_pairs=current_qa_pairs,
            document_summary=current_document_summary
        )
        
        print(f"✅ Generated {len(slides)} slides successfully")
        
        # Optimize slides for visual learners using PDF figures only
        if extracted_figures:
            print(f"🎨 Optimizing slides with {len(extracted_figures)} PDF figures for visual learners...")
            from parsing_info_from_pdfs import assign_visuals_to_slides
            
            # Get document text for context
            document_text = current_document_summary.abstract if current_document_summary else ""
            
            # Assign PDF figures to relevant slides
            slides = assign_visuals_to_slides(slides, extracted_figures, document_text)
        else:
            print("📝 No PDF figures available, using text-based slides")
            # Set all slides to text emphasis
            for slide in slides:
                slide.visual_type = "text_emphasis"
        
        sample_slides = slides
        
        # Auto-generate audio for all slides
        await generate_audio_for_all_slides(slides)
        
        # Log total processing time
        total_time = time.time() - start_time
        print(f"🎉 Slide generation complete! Total time: {total_time:.1f}s")
        
        return slides
        
    except Exception as e:
        error_msg = f"Failed to generate slides: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/upload", response_model=UploadResult)
async def upload_pdf(file: UploadFile = File(...)):
    """Process uploaded PDF and extract content for presentation generation"""
    global current_document_summary, vector_store_id, extracted_figures, current_qa_pairs
    
    # COMPLETE CONTEXT RESET for new document upload - ensure no content carries over
    reset_all_context()
    print("🔄 Starting fresh document processing with complete context reset")
    
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_contents = await file.read()
    file_size_mb = len(file_contents) / (1024 * 1024)
    
    if file_size_mb > 10:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    start_time = time.time()
    
    try:
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf_path, 'wb') as temp_file:
            temp_file.write(file_contents)
        
        # Extract figures from PDF
        try:
            from parsing_info_from_pdfs import extract_pdf_figures
            extracted_figures = extract_pdf_figures(file_contents)
            print(f"🖼️ Extracted {len(extracted_figures)} figures from PDF")
        except Exception as e:
            print(f"⚠️ Figure extraction failed: {e}")
            extracted_figures = []

        # Create vector store and upload PDF for Q&A functionality
        if openai_client:
            print(f"🔄 Creating vector store for: {file.filename}")
            
            from parsing_info_from_pdfs import create_vector_store, upload_single_pdf, generate_summary
            
            store_name = f"document_store_{file.filename.replace('.pdf', '')}_{int(time.time())}"
            vector_store_details = create_vector_store(openai_client, store_name)
            
            if vector_store_details and 'id' in vector_store_details:
                vector_store_id = vector_store_details['id']
                print(f"✅ Vector store created: {vector_store_id}")
                
                upload_result = upload_single_pdf(openai_client, temp_pdf_path, vector_store_id)
                
                if upload_result['status'] == 'success':
                    print(f"✅ PDF uploaded to vector store successfully")
                else:
                    print(f"⚠️ PDF upload to vector store failed")
            
            current_document_summary = generate_summary(openai_client, temp_pdf_path)
            print(f"✅ AI summary generated for: {file.filename}")
        
        extracted_text, page_count = extract_text_from_pdf(file_contents)
        analysis = analyze_document_content(extracted_text, file.filename)
        processing_time = round(time.time() - start_time, 2)
        
        os.remove(temp_pdf_path)
        os.rmdir(temp_dir)
        
        result = UploadResult(
            success=True,
            message=f"Successfully processed '{file.filename}' with AI analysis and figure extraction",
            filename=file.filename,
            fileSize=f"{file_size_mb:.2f} MB",
            pages=page_count,
            readingTime=analysis["reading_time"],
            topics=len(analysis["detected_topics"]),
            processingTime=f"{processing_time} seconds",
            keyTopics=analysis["detected_topics"],
            extractedSections=analysis["sections"],
            generatedSlides=analysis["estimated_slides"],
            detectedLanguage="English",
            complexity=analysis["complexity"],
            extractedText=extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text
        )
        
        print(f"📄 PDF Processed: {file.filename} ({file_size_mb:.2f}MB) in {processing_time}s")
        return result
        
    except Exception as e:
        print(f"❌ PDF Processing Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.post("/api/slides/{slide_number}/voice")
async def generate_slide_narration(slide_number: int):
    """Get voice narration for a specific slide"""
    try:
        # Debug logging
        print(f"🎙️ Voice request for slide {slide_number}, total slides: {len(sample_slides)}")
        
        cached_audio = get_slide_audio(slide_number)
        
        if cached_audio:
            print(f"✅ Serving cached audio for slide {slide_number}")
            audio_bytes = BytesIO(cached_audio)
            return StreamingResponse(
                audio_bytes,
                media_type="audio/mpeg",
                headers={"Content-Disposition": f"attachment; filename=slide_{slide_number}_narration.mp3"}
            )
        
        if not sample_slides:
            raise HTTPException(status_code=404, detail="No slides available. Please generate slides first.")
        
        slide = next((s for s in sample_slides if s.slide_number == slide_number), None)
        if not slide:
            available_slides = [s.slide_number for s in sample_slides]
            raise HTTPException(
                status_code=404, 
                detail=f"Slide {slide_number} not found. Available slides: {available_slides}"
            )
        
        # Use speaker notes for more natural narration, fallback to content if no notes  
        narration_text = slide.speaker_notes or f"{slide.title}. {slide.content}"
        
        # Use voice agent for better quality
        if not voice_agent:
            raise HTTPException(status_code=503, detail="Voice agent not available. Please check ElevenLabs configuration.")
        
        try:
            # Rate limit individual slide requests to prevent 429 errors
            async with ELEVENLABS_SEMAPHORE:
                print(f"🎙️ Generating audio for slide {slide_number} (rate-limited)")
                audio_content = await voice_agent.generate_speech(narration_text)
                print(f"✅ Generated audio for slide {slide_number} using ElevenLabs SDK")
        except Exception as e:
            print(f"⚠️ ElevenLabs voice generation failed: {e}")
            raise HTTPException(status_code=503, detail="ElevenLabs TTS not available. Please configure ELEVENLABS_API_KEY.")
        
        slide_audio_cache[slide_number] = audio_content
        
        audio_bytes = BytesIO(audio_content)
        return StreamingResponse(
            audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename=slide_{slide_number}_narration.mp3"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")

@app.options("/api/slides/{slide_number}/voice")
async def options_slide_voice(slide_number: int):
    """Handle CORS preflight for slide voice endpoint"""
    return {"status": "ok"}

# Voice Conversation Endpoints
@app.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio using ElevenLabs STT"""
    if not voice_agent:
        raise HTTPException(status_code=503, detail="Voice agent not available. Please check configuration.")
    
    try:
        audio_content = await file.read()
        transcript = await voice_agent.transcribe_audio(audio_content)
        
        return {
            "transcript": transcript,
            "success": True,
            "word_count": len(transcript.split())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/voice/conversation")
async def process_voice_conversation(request: dict):
    """Process voice conversation with context"""
    if not voice_agent:
        raise HTTPException(status_code=503, detail="Voice agent not available. Please check configuration.")
    
    try:
        question = request.get("question", "")
        slide_context = request.get("slideContext", {})
        document_context = request.get("documentContext", {})
        session_id = request.get("sessionId", "default")
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        # Get conversation history
        conversation_history = conversation_sessions.get(session_id, [])
        
        # Enhanced context with Q&A pairs and vector store access
        enhanced_context = {
            **document_context,
            "qa_pairs": current_qa_pairs[:10],  # Include top 10 Q&A pairs
            "vector_store_id": vector_store_id,
            "document_summary": current_document_summary.__dict__ if current_document_summary else None
        }
        
        # Process conversation
        result = await voice_agent.process_conversation(
            question=question,
            slide_context=slide_context,
            document_context=enhanced_context,
            conversation_history=conversation_history
        )
        
        # Update conversation history
        conversation_history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": result["answer"]}
        ])
        conversation_sessions[session_id] = conversation_history[-10:]  # Keep last 5 exchanges
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation processing failed: {str(e)}")

@app.post("/api/voice/speak")
async def generate_speech_response(request: dict):
    """Generate speech from text using ElevenLabs TTS"""
    if not voice_agent:
        raise HTTPException(status_code=503, detail="Voice agent not available. Please check ElevenLabs configuration.")
    
    try:
        text = request.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Generate speech with rate limiting to prevent 429 errors
        async with ELEVENLABS_SEMAPHORE:
            print(f"🎙️ Generating TTS response (rate-limited, max 4 concurrent)")
            audio_content = await voice_agent.generate_speech(text)
        
        audio_bytes = BytesIO(audio_content)
        
        return StreamingResponse(
            audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=response_elevenlabs.mp3",
                "X-Audio-Source": "ElevenLabs SDK"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

@app.get("/api/voice/status")
async def get_voice_agent_status():
    """Get current voice agent and slides status"""
    if not voice_agent:
        return {
            "voice_agent_available": False,
            "error": "Voice agent not initialized",
            "elevenlabs_available": False,
            "openai_available": openai_client is not None,
            "features": {
                "tts": False,
                "transcription": False,
                "conversation": False
            }
        }
    
    voice_info = voice_agent.get_voice_info()
    
    return {
        "voice_agent_available": True,
        "elevenlabs_available": voice_agent.elevenlabs_available,
        "total_slides": len(sample_slides),
        "current_slide": 1 if sample_slides else 0,
        "document_title": current_document_summary.title if current_document_summary else "No document",
        "slides_available": len(sample_slides) > 0,
        "slides_list": [{"number": s.slide_number, "title": s.title} for s in sample_slides],
        "voice_info": voice_info,
        "ready_for_narration": len(sample_slides) > 0,
        "audio_cache_size": len(slide_audio_cache),
        "cached_slides": list(slide_audio_cache.keys()),
        "conversation_sessions": len(conversation_sessions),
        "extracted_figures": len(extracted_figures)
    }

@app.delete("/api/voice/conversation/{session_id}")
async def clear_conversation_session(session_id: str):
    """Clear conversation history for a session"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return {"success": True, "message": f"Conversation session {session_id} cleared"}
    else:
        return {"success": False, "message": "Session not found"}

@app.post("/api/reset-context")
async def reset_context():
    """COMPLETE CONTEXT RESET - Clear all cached data and state (for debugging/fresh start)"""
    reset_all_context()
    return {
        "success": True, 
        "message": "Complete context reset performed - all slides, audio, figures, Q&A pairs, conversations, and document state cleared",
        "timestamp": datetime.now().isoformat(),
        "reset_items": {
            "slides": "cleared",
            "audio_cache": "cleared", 
            "figures": "cleared",
            "qa_pairs": "cleared",
            "conversations": "cleared",
            "vector_store_id": "reset",
            "document_summary": "reset"
        }
    }

# Chart endpoints removed - using PDF figures only for better performance

# Helper functions
def extract_text_from_pdf(file_contents: bytes) -> tuple[str, int]:
    """Extract text from PDF and return text + page count"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_contents))
        text = ""
        page_count = len(pdf_reader.pages)
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text, page_count
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")

def analyze_document_content(text: str, filename: str) -> dict:
    """Analyze extracted text and generate insights"""
    words = text.split()
    word_count = len(words)
    
    reading_minutes = max(1, word_count // 200)
    reading_time = f"{reading_minutes} minutes" if reading_minutes < 60 else f"{reading_minutes // 60}h {reading_minutes % 60}m"
    
    common_tech_terms = [
        "machine learning", "artificial intelligence", "neural network", "deep learning",
        "algorithm", "data science", "python", "tensorflow", "pytorch", "model",
        "training", "prediction", "classification", "regression", "clustering"
    ]
    
    text_lower = text.lower()
    detected_topics = [term for term in common_tech_terms if term in text_lower]
    
    sections = []
    if "introduction" in text_lower:
        sections.append({"title": "Introduction", "pages": "1-2"})
    if "method" in text_lower or "approach" in text_lower:
        sections.append({"title": "Methodology", "pages": "3-5"})
    if "result" in text_lower or "finding" in text_lower:
        sections.append({"title": "Results", "pages": "6-8"})
    if "conclusion" in text_lower:
        sections.append({"title": "Conclusion", "pages": "9-10"})
    
    if not sections:
        sections = [
            {"title": "Content Overview", "pages": "1-3"},
            {"title": "Main Discussion", "pages": "4-7"},
            {"title": "Summary", "pages": "8-10"}
        ]
    
    complexity = "beginner"
    if word_count > 5000:
        complexity = "intermediate"
    if word_count > 10000 or len(detected_topics) > 5:
        complexity = "advanced"
    
    return {
        "word_count": word_count,
        "reading_time": reading_time,
        "detected_topics": detected_topics[:8],
        "sections": sections,
        "complexity": complexity,
        "estimated_slides": min(12, max(4, len(sections) * 2))
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    print("🛑 Shutting down backend services...")
    print("✅ Cleanup complete")

if __name__ == "__main__":
    print("🚀 Starting Are You Taking Notes Backend with Enhanced Features")
    print("📡 Server will be available at http://localhost:8000")
    print("📖 API documentation at http://localhost:8000/docs")
    print(f"🎙️ ElevenLabs available: {voice_agent.elevenlabs_available if voice_agent else False}")
    print("📊 Using PDF figures for visual content")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )