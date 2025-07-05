import asyncio
import json
import os
import tempfile
import requests
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class ElevenLabsVoiceAgent:
    """ElevenLabs voice agent with enhanced retry logic and rate limiting"""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "sk_2de27f890bb19712af77d1bcdc66695963b9cdee5742b362")
        if not self.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        
        # Voice configuration - using Adam (conversational)
        self.voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - natural, conversational
        self.voice_name = "Adam"
        
        # ElevenLabs API endpoints
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        self.stt_url = "https://api.elevenlabs.io/v1/speech-to-text"
        
        # Conversational AI endpoints
        self.conversation_url = "https://api.elevenlabs.io/v1/convai/conversations"
        self.agent_url = "https://api.elevenlabs.io/v1/convai/agents"
        
        self.headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        
        # Store agent ID for conversations
        self.agent_id = None
        self.conversation_id = None
        
        # Retry configuration
        self.max_retries = 3
        self.initial_retry_delay = 1.0  # seconds
        self.max_retry_delay = 8.0  # seconds
        self.backoff_multiplier = 2.0
        
        logger.info(f"🎙️ ElevenLabs Voice Agent initialized with voice: {self.voice_name}")
    
    @property
    def elevenlabs_available(self) -> bool:
        """Check if ElevenLabs is available and properly configured"""
        return self.elevenlabs_api_key is not None and len(self.elevenlabs_api_key) > 0
    
    async def _retry_with_backoff(self, operation, operation_name: str, *args, **kwargs):
        """Generic retry wrapper with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.initial_retry_delay * (self.backoff_multiplier ** (attempt - 1)),
                        self.max_retry_delay
                    )
                    logger.info(f"🔄 Retrying {operation_name} in {delay:.1f}s (attempt {attempt}/{self.max_retries})")
                    await asyncio.sleep(delay)
                
                # Execute the operation
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"✅ {operation_name} succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Check if this is a retryable error
                is_rate_limit = '429' in error_msg or 'rate limit' in error_msg or 'too many requests' in error_msg
                is_server_error = any(code in error_msg for code in ['500', '502', '503', '504'])
                is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
                is_network_error = 'network' in error_msg or 'connection' in error_msg
                
                is_retryable = is_rate_limit or is_server_error or is_timeout or is_network_error
                
                # Don't retry on authentication or client errors (except rate limits)
                is_auth_error = '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg
                is_client_error = '400' in error_msg or 'bad request' in error_msg
                
                if is_auth_error or is_client_error:
                    logger.error(f"❌ {operation_name} failed with non-retryable error: {e}")
                    raise e
                
                if not is_retryable and attempt == 0:
                    logger.error(f"❌ {operation_name} failed with non-retryable error: {e}")
                    raise e
                
                if attempt == self.max_retries:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries} retries: {e}")
                    raise e
                
                logger.warning(f"⚠️ {operation_name} attempt {attempt + 1} failed: {e}")
                
                # Add extra delay for rate limit errors
                if is_rate_limit and attempt < self.max_retries:
                    extra_delay = 2.0 * (attempt + 1)  # Additional delay for rate limits
                    logger.info(f"⏰ Rate limit detected, adding extra {extra_delay:.1f}s delay")
                    await asyncio.sleep(extra_delay)
        
        # This should never be reached, but just in case
        raise last_exception or Exception(f"{operation_name} failed after all retries")
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using ElevenLabs STT with retry logic"""
        async def _transcribe():
            files = {
                'audio': ('audio.wav', audio_data, 'audio/wav')
            }
            
            headers = {
                "xi-api-key": self.elevenlabs_api_key
            }
            
            response = await asyncio.to_thread(
                lambda: requests.post(
                    self.stt_url, 
                    files=files, 
                    headers=headers, 
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get('text', '').strip()
                logger.info(f"🎤 Transcribed: {transcript[:50]}...")
                return transcript
            else:
                error_msg = f"ElevenLabs STT error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
        
        return await self._retry_with_backoff(_transcribe, "Audio transcription")
    
    async def process_conversation(
        self, 
        question: str, 
        slide_context: Dict[str, Any], 
        document_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process conversation using intelligent OpenAI-based responses with retry logic"""
        async def _process():
            logger.info(f"🧠 Processing intelligent conversation: {question[:50]}...")
            return await self._fallback_text_processing(question, slide_context, document_context)
        
        return await self._retry_with_backoff(_process, "Conversation processing")
    
    async def _fallback_text_processing(
        self, 
        question: str, 
        slide_context: Dict[str, Any], 
        document_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Intelligent fallback using OpenAI with vector store context"""
        try:
            # Get OpenAI client from global scope (imported from main.py)
            try:
                from main import openai_client
            except ImportError:
                openai_client = None
            
            if not openai_client:
                # Even more basic fallback if no OpenAI
                return {
                    "answer": "I'm currently in basic mode. The voice assistant requires OpenAI API access to provide detailed answers. Please configure OPENAI_API_KEY for intelligent responses.",
                    "context_used": False,
                    "slide_title": slide_context.get('title', ''),
                    "confidence": 0.3,
                    "word_count": 20,
                    "estimated_duration": 8.0
                }
            
            # Enhanced context with vector store search
            enhanced_context = document_context.copy()
            
            # Try to get specific answer from vector store if available
            vector_store_id = document_context.get('vector_store_id')
            if vector_store_id:
                try:
                    from parsing_info_from_pdfs import get_answer_using_file_search
                    vector_answer = await asyncio.to_thread(
                        lambda: get_answer_using_file_search(openai_client, question, vector_store_id, max_results=3)
                    )
                    enhanced_context['vector_search_result'] = vector_answer
                    logger.info(f"📚 Vector store search completed for: {question[:50]}...")
                except Exception as e:
                    logger.warning(f"Vector store search failed: {e}")
            
            # Build comprehensive context for OpenAI
            system_prompt = self._build_intelligent_system_prompt(slide_context, enhanced_context)
            user_prompt = self._build_user_prompt(question, slide_context, enhanced_context)
            
            # Call OpenAI for intelligent response with retry logic
            async def _openai_call():
                return await asyncio.to_thread(
                    lambda: openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=200,
                        temperature=0.7
                    )
                )
            
            response = await self._retry_with_backoff(_openai_call, "OpenAI conversation")
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "context_used": True,
                "slide_title": slide_context.get('title', ''),
                "confidence": 0.95,
                "word_count": len(answer.split()),
                "estimated_duration": len(answer.split()) / 2.5,
                "sources_used": ["document_qa", "vector_store", "slide_context"] if vector_store_id else ["document_qa", "slide_context"]
            }
                
        except Exception as e:
            logger.error(f"Intelligent fallback processing failed: {e}")
            # Last resort fallback
            return {
                "answer": f"I understand you're asking about '{question}'. While I'm having some technical difficulties accessing the full document context right now, I can see we're discussing '{slide_context.get('title', 'this topic')}'. Could you rephrase your question or ask something more specific about the current slide content?",
                "context_used": False,
                "slide_title": slide_context.get('title', ''),
                "confidence": 0.5,
                "word_count": 30,
                "estimated_duration": 12.0
            }
    
    def _build_intelligent_system_prompt(self, slide_context: Dict, document_context: Dict) -> str:
        """Build a comprehensive system prompt for intelligent responses"""
        prompt_parts = [
            "You are an intelligent AI teaching assistant helping students understand academic content.",
            "You have access to the full document context, Q&A pairs, and current slide information.",
            "Provide detailed, helpful answers that go beyond just the slide content.",
            "Use the Q&A pairs to provide specific examples and detailed explanations.",
            "Use your knowledge to explain concepts, provide examples, and connect ideas.",
            "Keep responses conversational but informative, around 100-150 words.",
            "Prioritize information from the Q&A pairs and document context over general knowledge."
        ]
        
        # Add document context
        if document_context.get('title'):
            prompt_parts.append(f"DOCUMENT: {document_context['title']}")
        
        if document_context.get('abstract'):
            prompt_parts.append(f"ABSTRACT: {document_context['abstract']}")
        
        if document_context.get('main_topics'):
            prompt_parts.append(f"KEY TOPICS: {', '.join(document_context['main_topics'])}")
        
        if document_context.get('key_points'):
            prompt_parts.append(f"KEY POINTS: {', '.join(document_context['key_points'][:5])}")
        
        # Add Q&A pairs for rich context
        qa_pairs = document_context.get('qa_pairs', [])
        if qa_pairs:
            prompt_parts.append("RELEVANT Q&A FROM DOCUMENT:")
            for i, qa in enumerate(qa_pairs[:5], 1):  # Top 5 Q&A pairs
                q = qa.get('question', 'Unknown question')
                a = qa.get('answer', 'No answer')[:200] + "..." if len(qa.get('answer', '')) > 200 else qa.get('answer', 'No answer')
                prompt_parts.append(f"Q{i}: {q}")
                prompt_parts.append(f"A{i}: {a}")
        
        # Add vector store search results if available
        vector_result = document_context.get('vector_search_result')
        if vector_result:
            prompt_parts.append(f"DIRECT DOCUMENT SEARCH RESULT: {vector_result[:300]}...")
        
        # Add current slide context
        if slide_context.get('title'):
            prompt_parts.append(f"CURRENT SLIDE: {slide_context['title']}")
        
        if slide_context.get('content'):
            prompt_parts.append(f"SLIDE CONTENT: {slide_context['content']}")
            
        if slide_context.get('speaker_notes'):
            prompt_parts.append(f"SPEAKER NOTES: {slide_context['speaker_notes']}")
        
        return "\n".join(prompt_parts)
    
    def _build_user_prompt(self, question: str, slide_context: Dict, document_context: Dict) -> str:
        """Build the user prompt with question and context"""
        context_sources = []
        if document_context.get('qa_pairs'):
            context_sources.append("Q&A pairs from the document")
        if document_context.get('vector_search_result'):
            context_sources.append("direct document search results")
        if slide_context.get('title'):
            context_sources.append("current slide content")
        
        sources_text = ", ".join(context_sources) if context_sources else "available context"
        
        return f"""Student Question: "{question}"

You have access to {sources_text}. Please provide a helpful, detailed answer that:
1. Uses the specific Q&A pairs and document search results when relevant
2. Goes beyond just repeating slide points 
3. Explains concepts clearly with examples
4. Makes connections between ideas
5. Helps the student truly understand the material

Prioritize information from the document's Q&A pairs and direct search results over general knowledge. 
If the question relates to something specific in the document, reference that content directly."""
    
    async def generate_speech(self, text: str) -> bytes:
        """Generate speech using ElevenLabs TTS with retry logic"""
        async def _generate():
            tts_headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            response = await asyncio.to_thread(
                lambda: requests.post(
                    self.tts_url, 
                    json=data, 
                    headers=tts_headers, 
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                logger.info(f"🎵 TTS generated: {len(response.content)} bytes")
                return response.content
            else:
                error_msg = f"ElevenLabs TTS error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
        
        return await self._retry_with_backoff(_generate, "Text-to-speech generation")
    
    async def process_voice_conversation(
        self,
        audio_data: bytes,
        slide_context: Dict[str, Any],
        document_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Complete voice conversation flow: STT -> Conversation -> TTS with retry logic"""
        try:
            # Step 1: Transcribe audio to text
            question = await self.transcribe_audio(audio_data)
            
            # Step 2: Process conversation
            conversation_result = await self.process_conversation(
                question, slide_context, document_context, conversation_history
            )
            
            # Step 3: Generate speech response
            answer_audio = await self.generate_speech(conversation_result["answer"])
            
            return {
                "transcribed_question": question,
                "answer_text": conversation_result["answer"],
                "answer_audio": answer_audio,
                "context_used": conversation_result["context_used"],
                "slide_title": conversation_result["slide_title"],
                "estimated_duration": conversation_result["estimated_duration"]
            }
            
        except Exception as e:
            logger.error(f"Voice conversation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Voice conversation failed: {str(e)}")
    
    def get_voice_info(self) -> Dict[str, Any]:
        """Get information about the voice agent"""
        return {
            "voice_name": self.voice_name,
            "voice_id": self.voice_id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "features": {
                "tts": True,
                "stt": True,
                "conversation": True,
                "conversational_ai": True,
                "retry_logic": True,
                "rate_limiting": True
            },
            "provider": "elevenlabs_conversational_ai",
            "model": "eleven_monolingual_v1",
            "retry_config": {
                "max_retries": self.max_retries,
                "initial_delay": self.initial_retry_delay,
                "max_delay": self.max_retry_delay,
                "backoff_multiplier": self.backoff_multiplier
            }
        }
    
    async def reset_conversation(self):
        """Reset the current conversation"""
        self.conversation_id = None
        logger.info("🔄 Conversation reset")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.conversation_id:
            # You might want to implement conversation cleanup here
            pass
        logger.info("🧹 Voice agent cleaned up")

# Global instance
try:
    voice_agent = ElevenLabsVoiceAgent()
    logger.info("✅ ElevenLabs Voice agent initialized successfully with retry logic")
except ValueError as e:
    if "ELEVENLABS_API_KEY" in str(e):
        logger.error(f"⚠️ Voice agent initialization failed: {e}")
        logger.error("💡 Set ELEVENLABS_API_KEY environment variable to enable voice features")
    else:
        logger.error(f"⚠️ Voice agent initialization failed: {e}")
    voice_agent = None
except Exception as e:
    logger.error(f"⚠️ Voice agent initialization failed: {e}")
    voice_agent = None