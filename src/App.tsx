import React, { useState, useEffect } from 'react';
import { Upload, FileText, Mic, MicOff, Play, Pause, SkipForward, SkipBack, Settings, Volume2, Download, MessageCircle, Loader2, CheckCircle, AlertCircle, Users, Clock, BookOpen, Brain, Zap } from 'lucide-react';

// Types
interface SlideContent {
  title: string;
  content: string;
  image_description: string;
  speaker_notes: string;
  slide_number: number;
  pdf_figure_index?: number;
  visual_type?: string;
  chart_url?: string;
}

interface DocumentSummary {
  title: string;
  abstract: string;
  key_points: string[];
  main_topics: string[];
  difficulty_level: string;
  estimated_read_time: string;
  document_type: string;
  authors: string[];
  publication_date: string;
}

interface UploadResult {
  success: boolean;
  message: string;
  filename: string;
  fileSize: string;
  pages: number;
  readingTime: string;
  topics: number;
  processingTime: string;
  keyTopics: string[];
  extractedSections: any[];
  generatedSlides: number;
  detectedLanguage: string;
  complexity: string;
  extractedText: string;
}

// Backend Service
class BackendService {
  private static baseUrl = 'http://localhost:8000';
  private static isConnected = false;

  static async checkConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      this.isConnected = response.ok;
      return this.isConnected;
    } catch {
      this.isConnected = false;
      return false;
    }
  }

  static async uploadPDF(file: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  static async getSlides(): Promise<SlideContent[]> {
    const response = await fetch(`${this.baseUrl}/api/slides`);
    if (!response.ok) throw new Error('Failed to fetch slides');
    return response.json();
  }

  static async generateSlides(): Promise<SlideContent[]> {
    const response = await fetch(`${this.baseUrl}/api/generate-slides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) throw new Error('Failed to generate slides');
    return response.json();
  }

  static async getDocumentSummary(): Promise<DocumentSummary> {
    const response = await fetch(`${this.baseUrl}/api/document-summary`);
    if (!response.ok) throw new Error('Failed to fetch document summary');
    return response.json();
  }

  static async getSlideAudio(slideNumber: number): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/slides/${slideNumber}/voice`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to generate audio');
    return response.blob();
  }

  static async transcribeAudio(audioBlob: Blob): Promise<{ transcript: string }> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');

    const response = await fetch(`${this.baseUrl}/api/voice/transcribe`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) throw new Error('Failed to transcribe audio');
    return response.json();
  }

  static async processVoiceConversation(data: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/voice/conversation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error('Failed to process conversation');
    return response.json();
  }
}

// Demo Data
const demoSlides: SlideContent[] = [
  {
    title: "Welcome to Study Buddy",
    content: "• AI-powered presentation system\n• Upload PDFs for instant analysis\n• Voice-enabled Q&A interactions",
    image_description: "Modern AI interface with document processing capabilities",
    speaker_notes: "Welcome to Study Buddy! This is a demonstration of our AI-powered presentation system that can transform your PDFs into interactive presentations.",
    slide_number: 1,
    visual_type: "text_emphasis"
  },
  {
    title: "Key Features",
    content: "• PDF document analysis\n• Automatic slide generation\n• ElevenLabs voice narration\n• Interactive Q&A system",
    image_description: "Feature overview diagram showing AI capabilities",
    speaker_notes: "Our system offers comprehensive document analysis, automatic slide generation, natural voice narration using ElevenLabs, and an interactive Q&A system for enhanced learning.",
    slide_number: 2,
    visual_type: "text_emphasis"
  },
  {
    title: "Getting Started",
    content: "• Upload your PDF document\n• Wait for AI processing\n• Generate presentation slides\n• Start interactive learning",
    image_description: "Step-by-step workflow diagram",
    speaker_notes: "Getting started is simple: upload your PDF, let our AI process it, generate slides automatically, and begin your interactive learning experience.",
    slide_number: 3,
    visual_type: "text_emphasis"
  }
];

const demoDocumentSummary: DocumentSummary = {
  title: "Study Buddy Demo",
  abstract: "This is a demonstration of the Study Buddy AI presentation system. Upload a PDF to see the full capabilities in action.",
  key_points: [
    "AI-powered document analysis",
    "Automatic slide generation",
    "Voice-enabled interactions",
    "Interactive Q&A system"
  ],
  main_topics: ["AI", "Education", "Document Processing", "Voice Technology"],
  difficulty_level: "beginner",
  estimated_read_time: "5 minutes",
  document_type: "demo",
  authors: ["Study Buddy Team"],
  publication_date: "2024"
};

// Main App Component
function App() {
  // State
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [slides, setSlides] = useState<SlideContent[]>(demoSlides);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [documentSummary, setDocumentSummary] = useState<DocumentSummary>(demoDocumentSummary);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGeneratingSlides, setIsGeneratingSlides] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [pdfUrl, setPdfUrl] = useState('');
  const [showUrlInput, setShowUrlInput] = useState(false);

  // Check backend connection on mount
  useEffect(() => {
    const checkBackend = async () => {
      const connected = await BackendService.checkConnection();
      setIsBackendConnected(connected);
      if (!connected) {
        setIsDemoMode(true);
      }
    };
    checkBackend();
  }, []);

  // Audio management
  useEffect(() => {
    return () => {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.src = '';
      }
    };
  }, [currentAudio]);

  // Handlers
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || file.type !== 'application/pdf') {
      alert('Please select a PDF file');
      return;
    }

    if (!isBackendConnected) {
      alert('Backend not connected. Running in demo mode.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const result = await BackendService.uploadPDF(file);
      
      if (result.success) {
        const summary = await BackendService.getDocumentSummary();
        setDocumentSummary(summary);
        setIsDemoMode(false);
        alert(`PDF uploaded successfully! ${result.message}`);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleUrlUpload = async () => {
    if (!pdfUrl.trim()) {
      alert('Please enter a PDF URL');
      return;
    }

    if (!isBackendConnected) {
      alert('Backend not connected. Running in demo mode.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Send URL to backend for processing
      const response = await fetch(`${BackendService['baseUrl']}/api/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: pdfUrl })
      });

      if (!response.ok) {
        throw new Error(`URL upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        const summary = await BackendService.getDocumentSummary();
        setDocumentSummary(summary);
        setIsDemoMode(false);
        setPdfUrl('');
        setShowUrlInput(false);
        alert(`PDF from URL processed successfully! ${result.message}`);
      }
    } catch (error) {
      console.error('URL upload failed:', error);
      alert('URL upload failed. Please check the URL and try again.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleGenerateSlides = async () => {
    if (!isBackendConnected) {
      alert('Backend not connected. Using demo slides.');
      return;
    }

    setIsGeneratingSlides(true);
    try {
      const newSlides = await BackendService.generateSlides();
      setSlides(newSlides);
      setCurrentSlide(0);
      setIsDemoMode(false);
    } catch (error) {
      console.error('Slide generation failed:', error);
      alert('Slide generation failed. Please try again.');
    } finally {
      setIsGeneratingSlides(false);
    }
  };

  const handlePlayAudio = async () => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setIsPlaying(false);
      return;
    }

    if (!isBackendConnected) {
      // Demo mode - simulate audio playback
      setIsPlaying(true);
      setTimeout(() => setIsPlaying(false), 3000);
      return;
    }

    try {
      const audioBlob = await BackendService.getSlideAudio(slides[currentSlide].slide_number);
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsPlaying(false);
        setCurrentAudio(null);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.play();
      setCurrentAudio(audio);
      setIsPlaying(true);
    } catch (error) {
      console.error('Audio playback failed:', error);
      alert('Audio generation failed. Please try again.');
    }
  };

  const handleVoiceRecording = async () => {
    if (!isBackendConnected) {
      alert('Voice features require backend connection.');
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setIsRecording(true);
      
      // Simulate recording for demo
      setTimeout(() => {
        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());
      }, 3000);
    } catch (error) {
      console.error('Microphone access failed:', error);
      alert('Microphone access denied.');
    }
  };

  const nextSlide = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1);
      if (currentAudio) {
        currentAudio.pause();
        setCurrentAudio(null);
        setIsPlaying(false);
      }
    }
  };

  const prevSlide = () => {
    if (currentSlide > 0) {
      setCurrentSlide(currentSlide - 1);
      if (currentAudio) {
        currentAudio.pause();
        setCurrentAudio(null);
        setIsPlaying(false);
      }
    }
  };

  const currentSlideData = slides[currentSlide];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-indigo-600" />
              <h1 className="text-2xl font-bold text-gray-900">Study Buddy</h1>
              <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full">
                Built with Bolt.new ⚡
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Backend Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isBackendConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">
                  {isBackendConnected ? 'Backend Connected' : 'Demo Mode'}
                </span>
              </div>

              {/* Upload Button */}
              <div className="flex items-center space-x-2">
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                  <div className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    <span>{isUploading ? 'Processing...' : 'Upload PDF'}</span>
                  </div>
                </label>

                <button
                  onClick={() => setShowUrlInput(!showUrlInput)}
                  className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                  disabled={isUploading}
                >
                  <FileText className="h-4 w-4" />
                  <span>PDF URL</span>
                </button>
              </div>

              {/* Settings */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* PDF URL Input Modal */}
      {showUrlInput && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <FileText className="h-5 w-5 mr-2 text-green-600" />
              Enter PDF URL
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PDF URL
                </label>
                <input
                  type="url"
                  value={pdfUrl}
                  onChange={(e) => setPdfUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  placeholder="https://example.com/document.pdf"
                  disabled={isUploading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Enter a direct link to a PDF file
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowUrlInput(false);
                    setPdfUrl('');
                  }}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900"
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUrlUpload}
                  disabled={isUploading || !pdfUrl.trim()}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      <span>Process PDF</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Document Summary Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <FileText className="h-5 w-5 mr-2 text-indigo-600" />
                Document Summary
              </h2>
              
              <div className="space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900">{documentSummary.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{documentSummary.abstract}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center">
                    <Clock className="h-4 w-4 mr-1 text-gray-400" />
                    <span>{documentSummary.estimated_read_time}</span>
                  </div>
                  <div className="flex items-center">
                    <BookOpen className="h-4 w-4 mr-1 text-gray-400" />
                    <span>{documentSummary.difficulty_level}</span>
                  </div>
                  <div className="flex items-center">
                    <Users className="h-4 w-4 mr-1 text-gray-400" />
                    <span>{documentSummary.authors.join(', ')}</span>
                  </div>
                  <div className="flex items-center">
                    <Zap className="h-4 w-4 mr-1 text-gray-400" />
                    <span>{documentSummary.document_type}</span>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Key Topics</h4>
                  <div className="flex flex-wrap gap-2">
                    {documentSummary.main_topics.map((topic, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-indigo-100 text-indigo-800 text-xs rounded-full"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Key Points</h4>
                  <ul className="space-y-1">
                    {documentSummary.key_points.slice(0, 4).map((point, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start">
                        <span className="text-indigo-600 mr-2">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Generate Slides Button */}
            <button
              onClick={handleGenerateSlides}
              disabled={isGeneratingSlides || !isBackendConnected}
              className="w-full bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {isGeneratingSlides ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating Slides...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  <span>Generate AI Slides</span>
                </>
              )}
            </button>
          </div>

          {/* Main Presentation Area */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              
              {/* Slide Content */}
              <div className="p-8 min-h-[500px] flex flex-col justify-center">
                <div className="text-center mb-8">
                  <h1 className="text-3xl font-bold text-gray-900 mb-4">
                    {currentSlideData.title}
                  </h1>
                  
                  {/* Visual Content Area */}
                  <div className="mb-6 p-6 bg-gray-50 rounded-lg min-h-[200px] flex items-center justify-center">
                    {currentSlideData.visual_type === 'pdf_figure' ? (
                      <div className="text-center">
                        <FileText className="h-16 w-16 text-gray-400 mx-auto mb-2" />
                        <p className="text-gray-600">PDF Figure</p>
                      </div>
                    ) : (
                      <div className="text-center">
                        <Brain className="h-16 w-16 text-indigo-400 mx-auto mb-2" />
                        <p className="text-gray-600">{currentSlideData.image_description}</p>
                      </div>
                    )}
                  </div>
                  
                  {/* Text Content */}
                  <div className="text-left max-w-2xl mx-auto">
                    <div className="prose prose-lg">
                      {currentSlideData.content.split('\n').map((line, index) => (
                        <p key={index} className="text-gray-700 mb-2">
                          {line}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="bg-gray-50 px-8 py-4 border-t">
                <div className="flex items-center justify-between">
                  
                  {/* Navigation */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={prevSlide}
                      disabled={currentSlide === 0}
                      className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <SkipBack className="h-5 w-5" />
                    </button>
                    
                    <span className="text-sm text-gray-600 px-3">
                      {currentSlide + 1} / {slides.length}
                    </span>
                    
                    <button
                      onClick={nextSlide}
                      disabled={currentSlide === slides.length - 1}
                      className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <SkipForward className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Audio Controls */}
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={handlePlayAudio}
                      className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                      {isPlaying ? (
                        <>
                          <Pause className="h-4 w-4" />
                          <span>Pause</span>
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          <span>Play Audio</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleVoiceRecording}
                      className={`p-2 rounded-lg transition-colors ${
                        isRecording 
                          ? 'bg-red-600 text-white' 
                          : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                      }`}
                    >
                      {isRecording ? (
                        <MicOff className="h-5 w-5" />
                      ) : (
                        <Mic className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Demo Mode Notice */}
            {isDemoMode && (
              <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mr-2" />
                  <p className="text-yellow-800">
                    <strong>Demo Mode:</strong> Upload a PDF and connect to the backend for full AI features including slide generation and voice interactions.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Backend URL
                </label>
                <input
                  type="text"
                  value={BackendService['baseUrl']}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="http://localhost:8000"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;