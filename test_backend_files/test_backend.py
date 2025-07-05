#!/usr/bin/env python3
"""
Simple Backend Functionality Tester
Tests core functions: PDF processing, summary generation, Q&A generation, slide generation
"""

import sys
import os
from pathlib import Path
import time
# Import backend functions
from parsing_info_from_pdfs import extract_text_from_pdf, generate_summary, generate_qa_pairs_from_document, generate_slides_from_qa_pairs, create_vector_store, upload_single_pdf
from main import openai_client


def test_document_summary(client, pdf_path):
    """Test document summary generation"""
    print("\n2️⃣ Testing Document Summary Generation...")
    
    try:
        start_time = time.time()
        summary = generate_summary(client, pdf_path)
        duration = time.time() - start_time
        
        print(f"✅ Summary generated in {duration:.1f}s")
        print(f"   📋 Title: {summary.title}")
        print(f"   📄 Abstract: {summary.abstract[:150]}...")
        print(f"   🔑 Key Points ({len(summary.key_points)}):")
        for i, point in enumerate(summary.key_points[:3], 1):
            print(f"      {i}. {point}")
        print(f"   📚 Topics: {', '.join(summary.main_topics[:5])}")
        print(f"   📊 Difficulty: {summary.difficulty_level}")
        print(f"   ⏰ Read Time: {summary.estimated_read_time}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        return None

def test_qa_generation(client, summary, vector_store_id):
    """Test Q&A pairs generation"""
    print("\n3️⃣ Testing Q&A Generation...")
    
    try:
        start_time = time.time()
        qa_pairs = generate_qa_pairs_from_document(client, summary, vector_store_id)
        duration = time.time() - start_time
        
        print(f"✅ Generated {len(qa_pairs)} Q&A pairs in {duration:.1f}s")
        
        # Show first few Q&A pairs
        for i, qa in enumerate(qa_pairs[:3], 1):
            print(f"\n   Q{i}: {qa['question']}")
            print(f"   A{i}: {qa['answer'][:100]}...")
        
        if len(qa_pairs) > 3:
            print(f"\n   ... and {len(qa_pairs) - 3} more Q&A pairs")
            
        return qa_pairs
        
    except Exception as e:
        print(f"❌ Q&A generation failed: {e}")
        return None

def test_slide_generation(client, qa_pairs, summary):
    """Test slide generation from Q&A pairs"""
    print("\n4️⃣ Testing Slide Generation...")
    
    try:
        start_time = time.time()
        slides = generate_slides_from_qa_pairs(client, qa_pairs, summary)
        duration = time.time() - start_time
        
        print(f"✅ Generated {len(slides)} slides in {duration:.1f}s")
        
        # Show each slide
        for slide in slides:
            print(f"\n   📊 Slide {slide.slide_number}: {slide.title}")
            print(f"      Content: {slide.content[:100]}...")
            print(f"      Image Desc: {slide.image_description[:60]}...")
            print(f"      Speaker Notes: {slide.speaker_notes[:60]}...")
        
        return slides
        
    except Exception as e:
        print(f"❌ Slide generation failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Backend Functionality Tester")
    print("=" * 60)

    store_name = f"document_store_{int(time.time())}"

    vector_store_details = create_vector_store(openai_client, store_name)
    
    # Get PDF path from command line or use default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Usage: python test_backend.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_backend.py /path/to/your/document.pdf")
        print("  python test_backend.py ~/Downloads/research_paper.pdf")
        return
    
    print(f"🎯 Testing with PDF: {pdf_path}")
    filename = os.path.basename(pdf_path)
    upload_single_pdf(openai_client, filename, vector_store_details["id"])

    
    
    # Test 1: Document Summary
    summary = test_document_summary(openai_client, pdf_path)
    if not summary:
        print("❌ Cannot proceed without document summary")
        return
    
    # Test 3: Q&A Generation
    qa_pairs = test_qa_generation(openai_client, summary, vector_store_details["id"])
    if not qa_pairs:
        print("❌ Cannot proceed without Q&A pairs")
        return
    
    # Test 4: Slide Generation
    slides = test_slide_generation(openai_client, qa_pairs, summary)
    if not slides:
        print("❌ Slide generation failed")
        return
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Document Summary: SUCCESS")
    print(f"✅ Q&A Generation: SUCCESS ({len(qa_pairs)} pairs)")
    print(f"✅ Slide Generation: SUCCESS ({len(slides)} slides)")
    print("\n🎉 All backend functions working correctly!")


if __name__ == "__main__":
    main() 