#!/usr/bin/env python3
"""
Test script for the AI module to ensure the Puter.ai API is working correctly.
"""

import json
import sys
import os

# Add the current directory to the path so we can import ai.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai import generate_quiz_question

def test_ai_functionality():
    """Test the AI functionality with different scenarios."""
    
    print("🧪 Testing AI Quiz Question Generation")
    print("=" * 50)
    
    # Test 1: General knowledge question
    print("\n📝 Test 1: General knowledge question")
    print("-" * 30)
    question1 = generate_quiz_question()
    print(f"Generated question: {json.dumps(question1, indent=2)}")
    
    # Validate structure
    validate_question_structure(question1, "General knowledge")
    
    # Test 2: Subject-specific question
    print("\n📝 Test 2: Subject-specific question (Science)")
    print("-" * 30)
    question2 = generate_quiz_question("science")
    print(f"Generated question: {json.dumps(question2, indent=2)}")
    
    # Validate structure
    validate_question_structure(question2, "Science")
    
    # Test 3: Another subject-specific question
    print("\n📝 Test 3: Subject-specific question (History)")
    print("-" * 30)
    question3 = generate_quiz_question("history")
    print(f"Generated question: {json.dumps(question3, indent=2)}")
    
    # Validate structure
    validate_question_structure(question3, "History")
    
    print("\n" + "=" * 50)
    print("✅ AI testing completed!")

def validate_question_structure(question_data, test_type):
    """Validate the structure of the generated question."""
    
    # Check if it's a dict
    if not isinstance(question_data, dict):
        print(f"❌ FAIL: {test_type} - Question data is not a dictionary")
        return
    
    # Check required keys
    required_keys = ["question", "options", "answer"]
    missing_keys = [key for key in required_keys if key not in question_data]
    
    if missing_keys:
        print(f"❌ FAIL: {test_type} - Missing keys: {missing_keys}")
        return
    
    # Check question
    question = question_data["question"]
    if not isinstance(question, str):
        print(f"❌ FAIL: {test_type} - Question is not a string")
        return
    
    if len(question.strip()) == 0:
        print(f"❌ FAIL: {test_type} - Question is empty")
        return
    
    print(f"✅ PASS: {test_type} - Question: '{question}'")
    
    # Check options
    options = question_data["options"]
    if not isinstance(options, list):
        print(f"❌ FAIL: {test_type} - Options is not a list")
        return
    
    if len(options) < 2:
        print(f"❌ FAIL: {test_type} - Not enough options (minimum 2)")
        return
    
    print(f"✅ PASS: {test_type} - Options count: {len(options)}")
    
    # Check answer index
    answer_index = question_data["answer"]
    if not isinstance(answer_index, int):
        print(f"❌ FAIL: {test_type} - Answer index is not an integer")
        return
    
    if answer_index < 0 or answer_index >= len(options):
        print(f"❌ FAIL: {test_type} - Answer index out of range")
        return
    
    print(f"✅ PASS: {test_type} - Answer index: {answer_index} -> '{options[answer_index]}'")
    
    # Additional checks
    if len(question.split()) > 10:
        print(f"⚠️  WARNING: {test_type} - Question has more than 10 words")
    
    print(f"✅ SUCCESS: {test_type} - All validations passed")

def test_api_connectivity():
    """Test basic API connectivity."""
    print("🌐 Testing API Connectivity")
    print("-" * 30)
    
    try:
        # Try a simple request to check connectivity
        import requests
        response = requests.get("https://api.puter.com/v2/ai/chat", timeout=10)
        print(f"✅ API endpoint accessible. Status code: {response.status_code}")
        print("   Note: A 405 (Method Not Allowed) is expected for GET requests")
    except requests.exceptions.RequestException as e:
        print(f"❌ API connectivity issue: {e}")

if __name__ == "__main__":
    print("QuizNation AI Module Test Suite")
    print("=" * 50)
    
    # Test API connectivity
    test_api_connectivity()
    
    # Test AI functionality
    try:
        test_ai_functionality()
    except Exception as e:
        print(f"❌ ERROR: Failed to test AI functionality: {e}")
        sys.exit(1)