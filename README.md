# Are You Taking Notes? 📚🤖

An AI-powered presentation and document analysis platform that transforms PDFs into interactive presentations with **ElevenLabs voice narration**, intelligent Q&A generation, and AI research assistance.

## ✨ Features

### 🎯 Core Functionality
- **PDF Upload & Analysis** - Upload PDFs and get AI-powered analysis with semantic search
- **Intelligent Q&A Generation** - Automatically generate questions and answers from documents
- **AI Presentation Creation** - Convert documents into engaging slide presentations (50/50 layout)
- **ElevenLabs Voice System** - Complete voice solution with TTS, STT, and conversation
- **Research Assistant** - AI agent for document exploration and interactive Q&A

### 🚀 Advanced Features
- **Backend Integration** - Full Python FastAPI backend with AI processing
- **Vector Store** - Semantic search and retrieval for document Q&A
- **Live Presentations** - Interactive presentation mode with balanced image/text layout
- **Voice Conversation** - Real-time voice interaction using ElevenLabs technology
- **Intelligent Audio** - Context-aware voice responses and slide narration
- **Demo Mode** - Full functionality even without backend connection

## 🏗️ Architecture

```
Frontend (React/TypeScript)
    ↓ HTTP API calls
Backend (FastAPI/Python)
    ↓ AI Processing
OpenAI API (GPT-4, Embeddings) - REQUIRED for slide generation
ElevenLabs API (TTS, STT, Conversation) - REQUIRED for voice features
    ↓ Vector Storage
Vector Store (Document Q&A)
    ↓ Deployment
Render.com (Production Backend)
```

## 🚀 Local Development Setup

### Prerequisites
- **Node.js** (v16 or higher)
- **Python** (3.11 or higher)  
- **OpenAI API Key** (REQUIRED for slide generation and document processing)
- **ElevenLabs API Key** (REQUIRED for voice features)

### 🎯 Step-by-Step Setup

#### 1. Clone Repository
```bash
git clone <your-repo-url>
cd Study_buddy_bolt
```

#### 2. Backend Setup 
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp env-template.txt .env

# Edit .env and add your API keys:
# OPENAI_API_KEY=sk-your-actual-openai-key (REQUIRED)
# ELEVENLABS_API_KEY=sk_your-elevenlabs-key (REQUIRED)
```

#### 3. Frontend Setup
```bash
# Navigate back to root directory 
cd ..

# Install Node.js dependencies
npm install
```

### 🏃‍♂️ Running the Application

#### Terminal 1 - Start Backend (Port 8000)
```bash
cd backend
python start_backend.py
```

✅ **Backend Success Indicators:**
- Should show: `✅ OpenAI client initialized successfully`
- Should show: `✅ ElevenLabs voice system initialized`
- Running on: `http://localhost:8000`
- Check: `curl http://localhost:8000/health` should return backend status

#### Terminal 2 - Start Frontend (Port 5173)
```bash
# In project root directory
npm run dev
```

✅ **Frontend Success Indicators:**
- Should show: `Local: http://localhost:5173/`
- Open browser to `http://localhost:5173`
- Backend status indicator should show "Backend Connected" ✅

### 🔑 Environment Variables

Create `backend/.env` with:
```env
# REQUIRED for slide generation and document processing
OPENAI_API_KEY=sk-your-actual-openai-key

# REQUIRED for voice features
ELEVENLABS_API_KEY=sk_your-elevenlabs-key

# Local development settings
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
PORT=8000
ENVIRONMENT=development
```

### 🧪 Testing Your Setup

#### 1. Test Backend Connection
```bash
cd backend
python start_backend.py
# Should show both OpenAI and ElevenLabs initialization status
```

#### 2. Test Full Workflow
1. Open `http://localhost:5173` in browser
2. Upload a PDF document
3. Wait for processing (should show progress)
4. Generate slides and test voice features
5. Try voice conversation with microphone button

#### 3. Test Voice Features
```bash
cd backend/test_backend_files
python test_elevenlabs_voice_agent.py  # Test complete voice system
python test_voice_speaker_notes.py     # Test slide narration
```

### 🔧 Troubleshooting

#### "Slide generation failed" Error
This error occurs when the OpenAI API key is not configured:

```bash
# Check if OpenAI API key is set
cd backend
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OpenAI Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"

# If not set, add it to backend/.env:
echo "OPENAI_API_KEY=sk-your-actual-openai-key" >> .env
```

#### Backend Won't Start
```bash
# Check if port 8000 is in use
lsof -ti:8000

# Kill existing process if needed
kill $(lsof -ti:8000)

# Try starting again
cd backend && python start_backend.py
```

#### Missing Dependencies
```bash
# If missing python-multipart or other packages
cd backend
pip install -r requirements.txt
```

#### Frontend Can't Connect to Backend
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify `CORS_ORIGINS` includes `http://localhost:5173`

#### Voice Features Not Working  
- Verify `ELEVENLABS_API_KEY` is set correctly in `backend/.env`
- Check ElevenLabs API quota/billing
- Look for voice agent initialization errors in backend terminal

### 🌐 Production Deployment

The application is optimized for **Render.com** deployment:

- **Backend**: Deployed on Render using `backend/render.yaml`
- **Frontend**: Can be deployed on any static hosting platform
- **Guide**: See `backend/RENDER_DEPLOY_GUIDE.md` for detailed instructions

**Important**: Set both `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` in your Render environment variables.

## 🧪 Testing

### Test Backend
```bash
cd backend/test_backend_files
python test_backend.py           # Test basic functionality
python test_connection.py        # Test API connectivity
python test_enhanced_features.py # Test AI features
```

### Test Voice Features
```bash
cd backend/test_backend_files
python test_elevenlabs_voice_agent.py  # Complete voice system test
python test_voice_speaker_notes.py     # Slide narration test
```

## 📡 API Endpoints

### Core Endpoints
- `GET /health` - Backend health check
- `POST /api/upload` - Upload PDF for processing
- `GET /api/document-summary` - Get document summary
- `POST /api/generate-qa` - Generate Q&A pairs
- `POST /api/generate-slides` - Generate presentation slides
- `GET /api/slides` - Get all slides
- `POST /api/slides/{slide_number}/voice` - Generate voice narration

### Voice System (ElevenLabs)
- `GET /api/voice/status` - Voice system status
- `POST /api/voice/transcribe` - Audio transcription (STT)
- `POST /api/voice/speak` - Text-to-speech (TTS)
- `POST /api/voice/conversation` - Interactive voice conversation
- `DELETE /api/voice/conversation/{session_id}` - Clear conversation

## 🎭 Advanced Features

### OpenAI Integration (Required)
Core functionality powered by OpenAI:
- **Document Processing**: PDF analysis and content extraction
- **Q&A Generation**: Intelligent question-answer pair creation
- **Slide Generation**: AI-powered presentation creation
- **Vector Store**: Semantic search and document understanding

### ElevenLabs Voice System (Required)
Complete voice solution including:
- **Text-to-Speech (TTS)**: Natural voice narration for slides
- **Speech-to-Text (STT)**: Voice input transcription
- **Voice Conversation**: Interactive Q&A with voice responses
- **Context Awareness**: Responses based on current slide and document

### Balanced Presentation Layout
- **50/50 Split**: Equal space for images and text content
- **Optimized Images**: Better aspect ratios, no stretching
- **Professional Styling**: Clean, modern presentation interface
- **Interactive Controls**: Play, pause, skip, voice interaction

## 🔧 Configuration Options

### Environment Variables
```env
# REQUIRED for slide generation and document processing
OPENAI_API_KEY=sk-your-actual-openai-key

# REQUIRED for voice features
ELEVENLABS_API_KEY=sk_your-elevenlabs-key

# Backend configuration
PORT=8000
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
```

### Frontend Configuration
The frontend automatically:
- Detects backend availability
- Falls back to demo mode if backend unavailable
- Configures backend URL based on environment
- Persists backend settings in localStorage

## 🛠️ Development Workflow

1. **Upload PDF** - Upload document via frontend interface
2. **AI Processing** - Backend processes with OpenAI and vector store creation
3. **Generate Slides** - Create balanced presentation slides using OpenAI
4. **Voice Narration** - Generate ElevenLabs audio for each slide
5. **Present** - Interactive presentation with voice controls
6. **Voice Q&A** - Use microphone for interactive questions

## 🐛 Troubleshooting

### Backend Issues
```bash
# Check if backend is running
cd backend/test_backend_files
python test_connection.py

# Test OpenAI integration
python test_enhanced_features.py

# Test ElevenLabs integration
python test_elevenlabs_voice_agent.py

# Check logs
cd backend && python start_backend.py  # Look for error messages
```

### Common Issues
- **"Slide generation failed"**: OpenAI API key not set in backend/.env
- **Backend not connecting**: Ensure it's running on port 8000
- **Voice features not working**: Check ELEVENLABS_API_KEY in .env
- **Missing packages**: Run `pip install -r requirements.txt`

### Demo Mode
If backend is unavailable, the frontend runs in demo mode with:
- Simulated PDF processing
- Mock slide generation
- Placeholder audio
- Sample Q&A pairs

## 📊 Performance Tips

- **Vector Store**: Enables fast semantic search for Q&A
- **Audio Caching**: Generated audio is cached for better performance
- **Optimized Processing**: Faster slide generation (4-6 slides vs 8-12)
- **Efficient PDF Parsing**: Smart text extraction and chunking
- **Connection Timeouts**: 5-minute timeout for long operations

## 🛡️ Security

- API keys stored in environment variables
- No sensitive data logged
- Vector stores isolated per document
- Temporary file cleanup
- CORS configured for frontend integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (frontend + backend)
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API (core slide generation and document processing)
- **ElevenLabs** for advanced TTS, STT, and voice technology
- **Render.com** for reliable backend hosting
- **FastAPI** for the backend framework
- **React** for the frontend framework

---

**Ready to transform your documents into intelligent presentations?** 🚀

**Required Setup:**
1. Get OpenAI API key from https://platform.openai.com/api-keys
2. Get ElevenLabs API key from https://elevenlabs.io/
3. Add both keys to `backend/.env`
4. Start with: `npm run dev` (frontend) and `cd backend && python start_backend.py` (backend)