#!/usr/bin/env python3

import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

def test_gemini():
    # Get API key from environment 
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment")
        return False
    
    try:
        print("Testing Gemini API...")
        print(f"API Key: {api_key[:10]}..." if api_key else "None")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create model
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest',
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # Simple test
        response = model.generate_content("Say hello in a cheerful way!")
        
        print(f"SUCCESS: {response.text}")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gemini() 