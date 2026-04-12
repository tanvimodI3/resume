import os
import json
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def verify_profiles_with_gemini(candidate_skills: List[str], profile_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    load_dotenv()
    
    try:
        from google import genai
        from google.genai import types
        HAS_GEMINI = True
    except ImportError:
        HAS_GEMINI = False

    if not HAS_GEMINI:
        raise ValueError("Google GenAI package is not installed.")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in .env")

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert technical recruiter and profile verification AI.
    Your task is to compare the skills claimed on a candidate's resume against the skills and data extracted from their online profiles (such as LinkedIn, GitHub, LeetCode, etc).
    
    Resume Claimed Skills:
    {json.dumps(candidate_skills, indent=2)}
    
    Extracted Profile Data (from various platforms):
    {json.dumps(profile_data, indent=2)}
    
    Instructions:
    1. Check if the skills claimed on the resume are backed up by the profile data (e.g., repositories, explicitly listed skills on LinkedIn, or LeetCode history).
    2. Give an overall validation score out of 100 indicating how well the profile data corroborates the resume claims.
    3. Provide a brief verification summary detailing strengths (verified skills) and gaps (skills not found on profiles).
    
    Return the result strictly as a valid JSON object matching this schema:
    {{
        "verification_score": <number between 0 and 100>,
        "verified_skills": <list of strings>,
        "unverified_skills": <list of strings>,
        "reasoning": <string, markdown formatted analysis>
    }}
    Do not wrap the JSON in markdown formatting blocks. Just return the JSON object directly.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        result = json.loads(text.strip())
        return result
    except Exception as e:
        logger.error(f"Gemini verification error: {str(e)}")
        raise
