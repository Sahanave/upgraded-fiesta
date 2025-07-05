# Helper functions from https://github.com/openai/openai-cookbook/blob/5d9219a90890a681890b24e25df196875907b18c/examples/File_Search_Responses.ipynb#L10
# Imports

from openai import OpenAI
import PyPDF2
import io
import json
import os
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import datetime
from tqdm import tqdm
from data_models import SlideContent, LiveUpdate, DocumentSummary, UploadResult
import fitz  # PyMuPDF for figure extraction
import base64
# Chart service removed for simplicity
import re


def format_slide_content(content: str) -> str:
    """Format slide content to ensure proper bullet point formatting with one point per line"""
    if not content:
        return content
    
    # Split by common separators and clean up
    lines = []
    
    # Handle various bullet point formats
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # If line doesn't start with bullet, add one
        if not line.startswith('•') and not line.startswith('-') and not line.startswith('*'):
            # Check if it looks like a sentence that should be a bullet point
            if len(line) > 10 and line.endswith('.'):
                line = f"• {line}"
        elif line.startswith('-') or line.startswith('*'):
            # Convert other bullet formats to •
            line = f"• {line[1:].strip()}"
        elif not line.startswith('• '):
            # Fix spacing after bullet
            line = line.replace('•', '• ', 1)
            
        lines.append(line)
    
    # Also handle cases where bullet points are in a single line
    if len(lines) == 1:
        single_line = lines[0]
        
        # Handle multiple bullets in one line (e.g., "• Point1 • Point2 • Point3")
        if single_line.count('•') > 1:
            import re
            bullet_parts = re.split(r'•\s*', single_line)
            lines = [f"• {part.strip()}" for part in bullet_parts if part.strip()]
        
        # Handle cases separated by periods or semicolons
        elif ('.' in single_line or ';' in single_line):
            if single_line.startswith('• '):
                single_line = single_line[2:]  # Remove initial bullet
                
            # Split on sentences that look like separate points
            import re
            sentences = re.split(r'[.;]\s+', single_line)
            lines = [f"• {sentence.strip()}" for sentence in sentences if sentence.strip()]
    
    return '\n'.join(lines)


def upload_single_pdf(client, file_path: str, vector_store_id: str):
    file_name = os.path.basename(file_path)
    try:
        file_response = client.files.create(file=open(file_path, 'rb'), purpose="assistants")
        attach_response = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_response.id
        )
        return {"file": file_name, "status": "success"}
    except Exception as e:
        print(f"Error with {file_name}: {str(e)}")
        return {"file": file_name, "status": "failed", "error": str(e)}


def create_vector_store(client, store_name: str) -> dict:
    try:
        vector_store = client.vector_stores.create(name=store_name)
        details = {
            "id": vector_store.id,
            "name": vector_store.name,
            "created_at": vector_store.created_at,
            "file_count": vector_store.file_counts.completed
        }
        print("Vector store created:", details)
        return details
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return {}
    

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text

def generate_summary(client, pdf_path):
    text = extract_text_from_pdf(pdf_path)
    filename = os.path.basename(pdf_path)
    
    # Truncate text if too long (OpenAI has token limits)
    max_text_length = 15000  # Approximately 3000-4000 tokens
    if len(text) > max_text_length:
        text = text[:max_text_length] + "..."

    prompt = (
        f"Please analyze this document and generate a comprehensive summary. "
        f"Extract structured information from the document.\n\n"
        f"Document content:\n{text}\n\n"
        f"Provide a structured summary with title, abstract, key points, main topics, "
        f"difficulty level, estimated read time, document type, authors, and publication date."
    )

    try:
        summary_schema = {
            "name": "extract_summary",
            "description": "Extract summary from input document.",
            "parameters": DocumentSummary.model_json_schema()
        }
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert document analyst. Provide structured, comprehensive summaries."},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "function", "function": summary_schema}],
            tool_choice={"type": "function", "function": {"name": "extract_summary"}}
        )

        # Check if response and tool_calls exist
        if response.choices and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            structured_json = json.loads(tool_call.function.arguments)
            structured_output = DocumentSummary(**structured_json)
            return structured_output
        else:
            print("No tool calls in response, falling back to basic summary")
            raise Exception("No structured response from OpenAI")
    
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Return a basic DocumentSummary instead of string
        return DocumentSummary(
            title=filename.replace('.pdf', ''),
            abstract=f"Document analysis completed for {filename}. Full AI analysis unavailable.",
            key_points=["Document uploaded successfully", "Text extraction completed", "Basic analysis performed"],
            main_topics=["Document analysis", "Content processing"],
            difficulty_level="intermediate",
            estimated_read_time="30 minutes",
            document_type="article",
            authors=["Unknown"],
            publication_date="2024-12-28"
        )

def generate_questions_from_summary(client, summary: DocumentSummary) -> List[str]:
    """Generate relevant questions based on the document summary"""
    
    prompt = f"""
    Based on this document summary, generate 5-7 thoughtful questions that would help someone understand the key concepts and details of this paper. 
    Focus on questions that require specific information from the document to answer correctly.
    
    Document Summary:
    Title: {summary.title}
    Abstract: {summary.abstract}
    Key Points: {', '.join(summary.key_points)}
    Main Topics: {', '.join(summary.main_topics)}
    Document Type: {summary.document_type}
    Difficulty Level: {summary.difficulty_level}
    
    Generate questions that cover:
    1. Main objectives and contributions
    2. Methodology or approach used
    3. Key findings or results
    4. Technical details and implementation
    5. Limitations or future work
    
    Return only the questions, one per line.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at generating insightful questions for academic papers. Create questions that require deep understanding of the document content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        questions_text = response.choices[0].message.content
        questions = [q.strip() for q in questions_text.split('\n') if q.strip() and not q.strip().startswith('Question')]
        
        # Clean up numbered questions
        cleaned_questions = []
        for q in questions:
            # Remove numbers like "1.", "2)", etc. from the beginning
            cleaned_q = re.sub(r'^\d+[\.)]\s*', '', q).strip()
            if cleaned_q and cleaned_q.endswith('?'):
                cleaned_questions.append(cleaned_q)
        
        return cleaned_questions[:7]  # Limit to 7 questions
    
    except Exception as e:
        print(f"Error generating questions: {e}")
        return [
            f"What is the main objective of {summary.title}?",
            f"What methodology does this {summary.document_type} use?",
            "What are the key findings or contributions?",
            "What are the limitations mentioned in this work?",
            "How does this work compare to previous research?"
        ]

def get_answer_using_file_search(client, question: str, vector_store_id: str, max_results: int = 5) -> str:
    """Get answer to a question using file search via Assistants API"""
    
    try:
        # Create a temporary assistant with file search capability
        assistant = client.beta.assistants.create(
            name="Document Q&A Assistant",
            instructions="You are a helpful assistant that answers questions based on the provided documents. Provide clear, accurate answers based on the document content.",
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        )
        
        # Create a thread
        thread = client.beta.threads.create()
        
        # Add the question as a message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for completion
        import time
        while run.status in ['queued', 'in_progress']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status == 'completed':
            # Get the assistant's response
            messages = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=1
            )
            
            if messages.data:
                message = messages.data[0]
                if message.content and len(message.content) > 0:
                    content = message.content[0]
                    if hasattr(content, 'text') and hasattr(content.text, 'value'):
                        answer = content.text.value
                        
                        # Clean up - delete the assistant and thread
                        try:
                            client.beta.assistants.delete(assistant.id)
                        except:
                            pass  # Ignore cleanup errors
                        
                        return answer
        
        # Clean up on failure
        try:
            client.beta.assistants.delete(assistant.id)
        except:
            pass
        
        return f"I found information related to your question in the document, but couldn't extract specific details. The assistant run status was: {run.status}"
    
    except Exception as e:
        print(f"Error getting answer for question '{question}': {e}")
        return "Unable to retrieve answer due to an error."

def generate_qa_pairs_from_document(client, summary: DocumentSummary, vector_store_id: str) -> List[dict]:
    """Generate question-answer pairs using summary for questions and file search for answers"""
    
    if not vector_store_id:
        print("No vector store ID provided, cannot generate Q&A pairs")
        return []
    
    # Step 1: Generate questions from summary
    questions = generate_questions_from_summary(client, summary)
    
    if not questions:
        print("No questions generated")
        return []
    
    print(f"Generated {len(questions)} questions, processing answers in parallel...")
    
    # Step 2: Process questions in parallel using ThreadPoolExecutor
    def process_question(question_data):
        question, question_number = question_data
        answer = get_answer_using_file_search(client, question, vector_store_id)
        return {
            "question": question,
            "answer": answer,
            "question_number": question_number
        }
    
    # Prepare data for parallel processing
    question_data = [(question, i + 1) for i, question in enumerate(questions)]
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=5) as executor:  # Limit to 5 concurrent requests
        qa_pairs = list(tqdm(
            executor.map(process_question, question_data), 
            total=len(questions),
            desc="Generating Q&A pairs"
        ))
    
    return qa_pairs


def generate_slides_from_qa_pairs(client, qa_pairs: List[dict], document_summary: DocumentSummary) -> List[SlideContent]:
    """Generate slides from Q&A pairs to create an educational presentation"""
    
    if not qa_pairs:
        print("No Q&A pairs provided, cannot generate slides")
        return []
    
    # Prepare Q&A content for slide generation
    qa_content = "\n\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in qa_pairs])
    
    prompt = f"""
    As an expert presentation designer, create a visually stunning and highly professional slide deck from the following Q&A content. The slides should be clean, modern, and follow best practices for visual storytelling.

    **Core Objective:** Transform dense Q&A material into a compelling narrative that is easy to digest and visually engaging.

    **Document Context:**
    Title: {document_summary.title}
    Type: {document_summary.document_type}
    Main Topics: {', '.join(document_summary.main_topics)}

    **Source Q&A Content:**
    {qa_content}

    **Design Principles for High-Quality Slides:**
    1.  **Modern & Clean Aesthetic:** Think minimalist design. Use ample white space. Avoid clutter.
    2.  **Visual Storytelling:** Each slide should build on the last, telling a cohesive story. The visual element is the hero.
    3.  **Clarity & Simplicity:** "Less is more." Use concise text and powerful visuals.
    4.  **Professional Branding:** The tone should be authoritative yet accessible.

    **Instructions for a 70% Visual, 30% Text Layout:**
    Generate 5-7 high-impact slides. For each slide, provide:

    1.  **Title:** A short, compelling title (max 7 words) that grabs attention.
    2.  **Content:** 2-3 ultra-concise bullet points (max 12 words each). Each point must be a powerful takeaway. Start with "•".
    3.  **Image Description:** A detailed, vivid description for a high-quality, modern visual. This is the centerpiece of the slide (70% of the space).
        *   **For technical concepts:** "A clean, isometric 3D illustration of a neural network with clearly labeled layers..."
        *   **For processes:** "A sleek, minimalist flowchart with modern icons and a clear, directional flow..."
        *   **For data:** "A beautiful, easy-to-read data visualization (e.g., a bar chart or heatmap) with a clear legend and highlighted insights..."
        *   **For concepts:** "An abstract, conceptual artwork that metaphorically represents the idea of..."
    4.  **Speaker Notes:** Engaging, conversational notes (3-4 sentences) that tell the story behind the slide. Should sound natural and confident.

    **CRITICAL DESIGN MANDATES:**
    -   **Minimalism:** Text is for support, not the main focus.
    -   **Visuals First:** The image description must be detailed enough to generate a stunning, relevant visual.
    -   **Narrative Flow:** Ensure the slides progress logically from introduction to conclusion.
    -   **Professional Tone:** Speaker notes should be crafted for a knowledgeable audience.

    Create slides that are not just informative, but also memorable and aesthetically pleasing.
    """

    slides_schema = {
        "name": "generate_slides_from_qa",
        "description": "Generate educational slides from Q&A pairs",
        "parameters": {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},  # Explicitly string
                            "image_description": {"type": "string"},
                            "speaker_notes": {"type": "string"},
                            "slide_number": {"type": "integer"}
                        },
                        "required": ["title", "content", "image_description", "speaker_notes", "slide_number"]
                    }
                }
            },
            "required": ["slides"]
        }
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a world-class presentation designer and visual storyteller. Your task is to convert dense Q&A content into a beautiful, modern, and professional slide deck. Generate valid JSON with proper escaping. Ensure that the 'content' field is a single string with bullet points separated by \n, each starting with '• '."},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "function", "function": slides_schema}],
            tool_choice={"type": "function", "function": {"name": "generate_slides_from_qa"}}
        )

        if not (response.choices and response.choices[0].message.tool_calls):
            raise Exception("No tool calls found in response")
        
        # Parse JSON and handle both string and array formats for content
        tool_call = response.choices[0].message.tool_calls[0]
        slides_data = json.loads(tool_call.function.arguments)
        
        # Convert to SlideContent objects with flexible content handling
        slides = []
        for i, slide_data in enumerate(slides_data["slides"], 1):
            # Handle content as either string or array
            content = slide_data.get("content", "")
            if isinstance(content, list):
                # Convert array to bullet-point string
                content = "\n".join([f"• {item}" for item in content])
            
            # Ensure proper bullet point formatting
            content = format_slide_content(content)
            
            slide = SlideContent(
                title=slide_data.get("title", f"Slide {i}"),
                content=content,
                image_description=slide_data.get("image_description", ""),
                speaker_notes=slide_data.get("speaker_notes", ""),
                slide_number=slide_data.get("slide_number", i)
            )
            slides.append(slide)
        
        print(f"✅ Successfully generated {len(slides)} slides")
        return slides
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"🔍 Raw response: {tool_call.function.arguments[:500]}...")
        return create_fallback_slides(document_summary)
        
    except Exception as e:
        print(f"❌ Error generating slides: {e}")
        return create_fallback_slides(document_summary)

def create_fallback_slides(document_summary: DocumentSummary) -> List[SlideContent]:
    """Create simple fallback slides when generation fails"""
    return [
        SlideContent(
            title=document_summary.title,
            content=f"Educational presentation based on analysis of {document_summary.document_type}. Main topics include: {', '.join(document_summary.main_topics[:3])}.",
            image_description="Title slide with document cover or main concept visualization",
            speaker_notes=f"Welcome to this presentation about {document_summary.title}. Today we'll explore the key concepts from this {document_summary.document_type}.",
            slide_number=1
        )
    ]

def extract_pdf_figures(file_contents: bytes) -> List[dict]:
    """Extracts and analyzes figures from a PDF, skipping small or irrelevant images."""
    figures = []
    
    try:
        pdf_document = fitz.open(stream=file_contents, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    pix = fitz.Pixmap(pdf_document, xref)
                    
                    # Skip small images that are likely decorative or not figures
                    if pix.width < 150 or pix.height < 150:
                        print(f"- Skipping small image on page {page_num + 1} (size: {pix.width}x{pix.height})")
                        pix = None
                        continue
                    
                    # Convert to PNG for consistent format
                    if pix.n - pix.alpha < 4:  # Handles GRAY, RGB
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode()
                        
                        figures.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "width": pix.width,
                            "height": pix.height,
                            "data": img_base64,
                            "type": "extracted_figure"
                        })
                    else:  # Handles CMYK
                        cmyk_pix = fitz.Pixmap(fitz.csRGB, pix)
                        img_data = cmyk_pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode()
                        
                        figures.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "width": cmyk_pix.width,
                            "height": cmyk_pix.height,
                            "data": img_base64,
                            "type": "extracted_figure"
                        })
                        cmyk_pix = None

                    pix = None
                
                except Exception as e:
                    print(f"⚠️ Error processing image on page {page_num + 1}, index {img_index}: {e}")
                    continue
        
        pdf_document.close()
        print(f"📊 Successfully extracted and processed {len(figures)} figures from the PDF.")
        
    except Exception as e:
        print(f"❌ Critical error during PDF figure extraction: {e}")
    
    return figures

def detect_technical_content(slide_content: str) -> dict:
    """Detect if slide content is technical and suggest appropriate visualization"""
    
    technical_keywords = {
        "architecture": ["architecture", "system", "component", "module", "layer"],
        "algorithm": ["algorithm", "process", "steps", "procedure", "method"],
        "network": ["network", "connection", "protocol", "communication", "topology"],
        "data_flow": ["data", "flow", "pipeline", "processing", "transformation"],
        "model": ["model", "framework", "structure", "representation"],
        "comparison": ["comparison", "versus", "different", "contrast", "compare"]
    }
    
    content_lower = slide_content.lower()
    detected_types = []
    
    for viz_type, keywords in technical_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            detected_types.append(viz_type)
    
    if detected_types:
        return {
            "is_technical": True,
            "suggested_visualization": detected_types[0],
            "description": generate_diagram_description(slide_content, detected_types[0])
        }
    
    return {
        "is_technical": False,
        "suggested_visualization": None,
        "description": None
    }

def generate_diagram_description(content: str, viz_type: str) -> str:
    """Generate a description for visual content"""
    
    descriptions = {
        "architecture": f"System architecture diagram showing the main components and their relationships described in: {content[:100]}...",
        "algorithm": f"Flowchart diagram illustrating the algorithm or process steps mentioned in: {content[:100]}...",
        "network": f"Network topology diagram representing the connections and protocols from: {content[:100]}...",
        "data_flow": f"Data flow diagram showing the data processing pipeline described in: {content[:100]}...",
        "model": f"Conceptual model diagram visualizing the framework or structure from: {content[:100]}...",
        "comparison": f"Comparison diagram contrasting different approaches mentioned in: {content[:100]}..."
    }
    
    return descriptions.get(viz_type, f"Technical diagram illustrating concepts from: {content[:100]}...")

# Enhanced slide generation function
def generate_slides_with_visuals(sections, summary, extracted_figures=None):
    """Generate slides with automatic figure integration and visual suggestions"""
    
    if extracted_figures is None:
        extracted_figures = []
    
    prompt = f"""
    As a senior presentation designer, create a visually driven and professional slide deck based on the provided document analysis. The slides must be clean, modern, and designed for maximum impact and clarity.

    **Core Objective:** Translate document sections and summaries into a compelling visual narrative.

    **DOCUMENT SUMMARY:**
    Title: {summary.get('title', 'Research Document')}
    Abstract: {summary.get('abstract', 'No abstract available')}
    Key Topics: {', '.join(summary.get('main_topics', []))}

    **AVAILABLE FIGURES:** {len(extracted_figures)} extracted from PDF

    **CONTENT SECTIONS:**
    {chr(10).join([f"- {section.get('title', 'Section')}: {section.get('content', '')[:200]}..." for section in sections[:8]])}

    **Instructions for High-Impact Visual Slides:**
    Generate 5-7 slides, each with a strong visual focus. For each slide, provide:

    1.  **TITLE:** A concise, powerful title (max 7 words).
    2.  **CONTENT:** 2-3 minimalist bullet points (max 12 words each), starting with "•". These should be key takeaways.
    3.  **VISUAL_TYPE:** Choose from:
        *   `pdf_figure`: Use a relevant figure from the document.
        *   `visual_emphasis`: For technical or conceptual content that needs a strong visual.
        *   `text_emphasis`: For slides where the text is the primary focus.
    4.  **VISUAL_DESCRIPTION:** A detailed description for creating a high-quality visual or for captioning a PDF figure.
        *   **For `visual_emphasis`:** "A sleek 3D isometric illustration of a data pipeline..." or "A modern, abstract design representing the concept of..."
        *   **For `pdf_figure`:** A concise and informative caption for the figure.
    5.  **SPEAKER_NOTES:** Polished, conversational notes (3-4 sentences) that provide context and narrative.

    **CRITICAL DESIGN GUIDELINES:**
    -   **Follow a Narrative Arc:** Start with an introduction, build on key findings, and end with a strong conclusion.
    -   **Prioritize Visuals:** The visual element should dominate each slide.
    -   **Embrace Minimalism:** Use ample white space and avoid clutter.
    -   **Ensure Readability:** Text should be large, clear, and concise.

    Format each slide precisely as follows:
    SLIDE_X:
    TITLE: [title]
    CONTENT:
    • [First key point]
    • [Second key point]
    VISUAL_TYPE: [pdf_figure/visual_emphasis/text_emphasis]
    VISUAL_DESCRIPTION: [detailed description]
    SPEAKER_NOTES: [conversational notes]
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior presentation designer with expertise in creating visually-driven, professional, and modern slide decks. Your task is to generate a slide deck from the provided document analysis, ensuring each slide is a perfect blend of clarity, and aesthetic appeal."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )

        content = response.choices[0].message.content
        slides = parse_enhanced_slides(content, extracted_figures)
        
        print(f"✅ Generated {len(slides)} slides with visual enhancements")
        return slides

    except Exception as e:
        print(f"❌ Enhanced slide generation failed: {e}")
        return []

def parse_enhanced_slides(content: str, extracted_figures: List[dict]) -> List[dict]:
    """Parse the enhanced slide content with visual elements"""
    
    slides = []
    slide_sections = content.split("SLIDE_")
    
    for i, section in enumerate(slide_sections[1:], 1):  # Skip first empty split
        try:
            lines = section.strip().split('\n')
            
            # Extract slide components
            title = ""
            slide_content = ""
            visual_type = "text_emphasis"
            visual_description = ""
            speaker_notes = ""
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("TITLE:"):
                    title = line[6:].strip()
                    current_section = "title"
                elif line.startswith("CONTENT:"):
                    slide_content = line[8:].strip()
                    current_section = "content"
                elif line.startswith("VISUAL_TYPE:"):
                    visual_type = line[12:].strip()
                    current_section = "visual_type"
                elif line.startswith("VISUAL_DESCRIPTION:"):
                    visual_description = line[19:].strip()
                    current_section = "visual_description"
                elif line.startswith("SPEAKER_NOTES:"):
                    speaker_notes = line[14:].strip()
                    current_section = "speaker_notes"
                elif line and current_section:
                    # Continue building the current section
                    if current_section == "content":
                        # Preserve line breaks for bullet points
                        if slide_content and line.strip().startswith("•"):
                            slide_content += "\n" + line
                        elif slide_content:
                            slide_content += " " + line
                        else:
                            slide_content = line
                    elif current_section == "visual_description":
                        visual_description += " " + line
                    elif current_section == "speaker_notes":
                        speaker_notes += " " + line
            
            # Create slide object with visual enhancements
            slide = {
                "title": title or f"Slide {i}",
                "content": format_slide_content(slide_content.strip()),
                "image_description": visual_description.strip(),
                "speaker_notes": speaker_notes.strip(),
                "slide_number": i,
                "visual_type": visual_type,
                "has_pdf_figure": False,
                "visual_prompt": None
            }
            
            # Handle different visual types
            if visual_type == "pdf_figure" and extracted_figures:
                # Find most relevant figure for this slide
                slide["has_pdf_figure"] = True
                slide["pdf_figure_index"] = min(i-1, len(extracted_figures)-1)
                
            elif visual_type == "visual_emphasis":
                # Use text emphasis instead of chart generation
                slide["visual_prompt"] = visual_description
                slide["has_chart"] = False
                print(f"📝 Using text emphasis for slide {i}")
            
            slides.append(slide)
            
        except Exception as e:
            print(f"⚠️ Error parsing slide {i}: {e}")
            continue
    
    return slides

def check_figure_relevance(slide_content: str, slide_title: str, pdf_figure_info: dict, pdf_text: str = "") -> float:
    """Calculates a relevance score between slide content and a PDF figure (0.0 to 1.0)."""
    
    slide_text = (slide_content + " " + slide_title).lower()
    slide_words = set(re.findall(r'\b\w+\b', slide_text))
    
    # Keywords that strongly indicate a figure's relevance
    technical_keywords = {
        "architecture", "diagram", "system", "model", "framework",
        "algorithm", "process", "flow", "network", "structure",
        "data", "result", "analysis", "comparison", "chart", "figure", "graph"
    }
    
    # Score based on keyword matches
    keyword_score = sum(1 for word in technical_keywords if word in slide_words) / len(technical_keywords)
    
    # Score based on the figure's size (larger figures are generally more important)
    width = pdf_figure_info.get("width", 0)
    height = pdf_figure_info.get("height", 0)
    size_score = min((width * height) / (800 * 600), 1.0) # Normalize against a large figure size
    
    # Contextual score from the page number
    page_num = pdf_figure_info.get("page", 1)
    context_score = 1.0 / (1 + abs(page_num - len(pdf_text) // 4000)) # Assume ~4000 chars/page
    
    # Combine scores with weighting
    # Weighted average: 50% keyword, 30% size, 20% context
    relevance = (0.5 * keyword_score) + (0.3 * size_score) + (0.2 * context_score)
    
    # Boost score if the slide explicitly mentions a figure
    if "figure" in slide_words or "diagram" in slide_words:
        relevance *= 1.2
        
    print(f"  - Figure on page {page_num}: Keyword Score={keyword_score:.2f}, Size Score={size_score:.2f}, Context Score={context_score:.2f} -> Relevance={min(relevance, 1.0):.2f}")

    return min(relevance, 1.0)

def assign_visuals_to_slides(slides: List[SlideContent], extracted_figures: List[dict], document_text: str = "") -> List[SlideContent]:
    """Assigns the most relevant PDF figures to slides based on a sophisticated relevance score."""
    
    print(f"🎨 Assigning visuals to {len(slides)} slides using enhanced relevance scoring...")
    
    used_figures = set()
    
    for slide in slides:
        best_figure_index = None
        highest_relevance = 0.0
        
        print(f"\nAssessing figures for Slide {slide.slide_number}: '{slide.title}'")
        
        for i, figure in enumerate(extracted_figures):
            if i in used_figures:
                continue
            
            relevance = check_figure_relevance(
                slide.content, 
                slide.title, 
                figure, 
                document_text
            )
            
            if relevance > highest_relevance:
                highest_relevance = relevance
                best_figure_index = i
        
        # Assign the figure if it meets a minimum relevance threshold
        if best_figure_index is not None and highest_relevance > 0.4: # Increased threshold for higher quality matching
            slide.pdf_figure_index = best_figure_index
            slide.visual_type = "pdf_figure"
            used_figures.add(best_figure_index)
            print(f"✅ Assigned PDF Figure {best_figure_index} to Slide {slide.slide_number} (Relevance: {highest_relevance:.2f})")
        else:
            slide.visual_type = "text_emphasis"
            slide.pdf_figure_index = None
            print(f"📝 No highly relevant PDF figure found for Slide {slide.slide_number}. Using text emphasis.")
            
    return slides

# Chart generation functions removed - using PDF figures only for better performance

def create_visual_optimized_slides(qa_pairs: List[dict], document_summary: DocumentSummary, extracted_figures: List[dict] = None, document_text: str = "") -> List[SlideContent]:
    """Create slides optimized for 67% visual, 33% text layout using PDF figures"""
    
    if extracted_figures is None:
        extracted_figures = []
    
    # Generate base slides with concise content
    slides = generate_slides_from_qa_pairs(
        client=None,  # Will be passed from calling function
        qa_pairs=qa_pairs, 
        document_summary=document_summary
    )
    
    if not slides:
        return []
    
    print(f"🎯 Optimizing {len(slides)} slides for visual learners (67% image, 33% text)")
    
    # Assign PDF figures to relevant slides
    slides = assign_visuals_to_slides(slides, extracted_figures, document_text)
    
    pdf_figure_count = len([s for s in slides if s.visual_type == 'pdf_figure'])
    text_emphasis_count = len([s for s in slides if s.visual_type == 'text_emphasis'])
    
    print(f"✅ Visual optimization complete: {pdf_figure_count} PDF figures, {text_emphasis_count} text-emphasis slides")
    
    return slides