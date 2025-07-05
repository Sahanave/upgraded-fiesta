# Data models
from pydantic import BaseModel
from typing import List, Optional

class SlideContent(BaseModel):
    title: str
    content: str
    image_description: str
    speaker_notes: str
    slide_number: int
    pdf_figure_index: Optional[int] = None
    visual_type: Optional[str] = "text_emphasis"  # "pdf_figure", "generated_chart", "text_emphasis"
    chart_url: Optional[str] = None

class LiveUpdate(BaseModel):
    message: str
    timestamp: str
    type: str  # "info", "question", "announcement"

class SectionMultimodalEnhancement(BaseModel):
    summary: Optional[str] = None
    questions: Optional[List[str]] = []
    audio_explanation_url: Optional[str] = None
    image_visualizations: Optional[List[str]] = []  # e.g. diagram URLs or Base64
    
class ResearchPaperSection(BaseModel):
    title: str
    abstract: Optional[str] = None
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    conclusion: Optional[str] = None
    figures: Optional[List[str]] = []
    references: Optional[List[str]] = []
    rest: Optional[str] = None

    # New: section-wise enrichment
    introduction_enhanced: Optional[SectionMultimodalEnhancement] = None
    methods_enhanced: Optional[SectionMultimodalEnhancement] = None
    results_enhanced: Optional[SectionMultimodalEnhancement] = None
    conclusion_enhanced: Optional[SectionMultimodalEnhancement] = None

class DocumentSummary(BaseModel):
    title: str
    abstract: str
    key_points: List[str]
    main_topics: List[str]
    difficulty_level: str  # "beginner", "intermediate", "advanced"
    estimated_read_time: str
    document_type: str  # "research_paper", "tutorial", "book_chapter", "article"
    authors: List[str]
    publication_date: str
    sections: Optional[ResearchPaperSection] = None

class UploadResult(BaseModel):
    success: bool
    message: str
    filename: str
    fileSize: str
    pages: int
    readingTime: str
    topics: int
    processingTime: str
    keyTopics: List[str]
    extractedSections: List[dict]
    generatedSlides: int
    detectedLanguage: str
    complexity: str
    extractedText: str  # Full text content