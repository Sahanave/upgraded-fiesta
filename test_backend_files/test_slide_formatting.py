#!/usr/bin/env python3
"""
Test slide content formatting to ensure one point per line
"""

from parsing_info_from_pdfs import format_slide_content

def test_slide_formatting():
    """Test various slide content formatting scenarios"""
    
    test_cases = [
        {
            "name": "Run-on bullet points",
            "input": "• First point • Second point • Third point",
            "expected_lines": 3
        },
        {
            "name": "Mixed bullet formats",
            "input": "- First point\n* Second point\n• Third point",
            "expected_lines": 3
        },
        {
            "name": "Sentences without bullets",
            "input": "This is the first key point. This is the second important concept. Here's the third idea.",
            "expected_lines": 3
        },
        {
            "name": "Already properly formatted",
            "input": "• First point\n• Second point\n• Third point",
            "expected_lines": 3
        },
        {
            "name": "Semicolon separated points",
            "input": "• First important concept; Second key finding; Third major result",
            "expected_lines": 3
        }
    ]
    
    print("🧪 Testing Slide Content Formatting")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        
        formatted = format_slide_content(test_case['input'])
        lines = formatted.split('\n')
        actual_lines = len([line for line in lines if line.strip()])
        
        print(f"Output:\n{formatted}")
        print(f"Expected lines: {test_case['expected_lines']}, Actual: {actual_lines}")
        
        if actual_lines == test_case['expected_lines']:
            print("✅ PASS")
        else:
            print("❌ FAIL")
        
        print("-" * 30)
    
    print("\n🎯 Summary: Slide formatting ensures one point per line with proper bullet symbols")

if __name__ == "__main__":
    test_slide_formatting() 