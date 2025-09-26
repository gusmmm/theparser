#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced year-based statistics functionality.
"""

from main import analyze_subjects_by_year, extract_year_from_subject
import json

def test_year_extraction():
    """Test the year extraction logic."""
    print("=== Testing Year Extraction ===")
    test_cases = [
        ("2401", 2024, "4-digit subject: 2401 -> year 2024, serial 01"),
        ("2512", 2025, "4-digit subject: 2512 -> year 2025, serial 12"), 
        ("901", 2009, "3-digit subject: 901 -> year 2009, serial 01"),
        ("825", 2008, "3-digit subject: 825 -> year 2008, serial 25")
    ]
    
    for subject, expected_year, description in test_cases:
        year = extract_year_from_subject(subject)
        status = "✅" if year == expected_year else "❌"
        print(f"{status} {description} -> extracted: {year}")

def test_analysis():
    """Test the full year-based analysis."""
    print("\n=== Testing Year-Based Analysis ===")
    
    analysis = analyze_subjects_by_year('./pdf/output')
    
    print(f"📊 Summary:")
    print(f"   Total subjects: {analysis['summary']['total_subjects']}")
    print(f"   Years covered: {analysis['summary']['years_covered']}")
    print(f"   Document types: {analysis['summary']['document_types']}")
    
    print(f"\n📅 Year Breakdown:")
    for year in sorted(analysis['by_year'].keys()):
        year_data = analysis['by_year'][year]
        print(f"   Year {year}:")
        print(f"     Subjects: {year_data['total_count']}")
        print(f"     Document types: {year_data['document_types']}")
        print(f"     Processing: P:{year_data['processing_status']['parsed']} M:{year_data['processing_status']['merged']} C:{year_data['processing_status']['cleaned']}")
        
        # Show first few subjects as examples
        if year_data['subjects']:
            print(f"     Sample subjects: {[s['id'] for s in year_data['subjects'][:3]]}")
    
    # Export analysis to JSON for inspection
    with open('./reports/year_analysis_sample.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full analysis exported to: ./reports/year_analysis_sample.json")

if __name__ == "__main__":
    test_year_extraction()
    test_analysis()
    print(f"\n✅ All tests completed! Run 'uv run python main.py --menu' and select option 3 for full statistics.")