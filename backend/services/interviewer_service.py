"""
AI Interviewer Service
Uses Google Gemini (gemini-2.0-flash) via the new google-genai SDK for:
  - Resume parsing (structured extraction)
  - Interview question generation (5 personalized questions)
  - Answer evaluation (score + feedback)
  - Final report generation (overall score + breakdown)

No embeddings, no vector store — pure LLM text generation.
Ported and fixed from: github.com/Manthan0000/ai-interviewer
"""

import os
import re
import json
import logging
import numpy as np
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── PDF extraction (reuse PyMuPDF already installed) ─────────────────────────
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Configure Gemini Client ──────────────────────────────────────────────────
_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if _api_key:
    _client = genai.Client(api_key=_api_key)
    logger.info("Gemini client initialized successfully")
else:
    _client = None
    logger.warning("GOOGLE_API_KEY not found — Gemini calls will fail")

MODEL_NAME = "gemini-2.0-flash"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract text from PDF bytes
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract plain text from raw PDF bytes using PyMuPDF."""
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise


def _generate(prompt: str) -> str:
    """Call Gemini and return the text response with retry logic for transient errors."""
    if _client is None:
        raise RuntimeError("Gemini client not configured — set GOOGLE_API_KEY in .env")
    
    import time
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = _client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "Service Unavailable" in error_str or "overloaded" in error_str.lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Gemini API busy (503). Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            logger.error(f"Gemini generation error: {error_str}")
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Core AI Engine
# ─────────────────────────────────────────────────────────────────────────────

class InterviewEngine:
    """
    Wraps all Gemini calls for the AI Interviewer feature.
    Single instance is reused per request (stateless).
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")

    # ── 1. Parse resume into structured data ─────────────────────────────────

    def parse_resume(self, text_content: str) -> Dict[str, Any]:
        prompt = f"""
Parse this resume text into structured JSON. Return ONLY valid JSON with these exact fields:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "skills": ["skill1", "skill2"],
    "education": [{{"degree": "degree", "institution": "school", "year": "year"}}],
    "experience": [{{"title": "job title", "company": "company", "duration": "duration", "description": "description"}}],
    "projects": [{{"name": "project", "description": "description", "technologies": ["tech1"]}}],
    "certifications": ["cert1"]
}}

Resume Text:
{text_content}

Return ONLY the JSON object, no markdown or explanations.
"""
        try:
            raw = _generate(prompt)
            json_text = re.sub(r"^```json\s*", "", raw)
            json_text = re.sub(r"\s*```$", "", json_text)
            return json.loads(json_text)
        except Exception as e:
            logger.error(f"Resume parse error: {e}")
            return {
                "name": "Candidate",
                "email": "",
                "phone": "",
                "skills": [],
                "education": [],
                "experience": [],
                "projects": [],
                "certifications": [],
            }

    # ── 2. Generate N personalized interview questions ────────────────────────

    def generate_questions(self, resume_data: Dict, num_questions: int = 5) -> List[str]:
        name = resume_data.get("name", "Candidate")
        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience", [])
        projects = resume_data.get("projects", [])
        education = resume_data.get("education", [])

        # Build a short profile summary for the prompt
        profile_lines = [f"Candidate: {name}"]
        if skills:
            profile_lines.append(f"Skills: {', '.join(skills[:10])}")
        for exp in experience[:3]:
            profile_lines.append(
                f"Experience: {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})"
            )
        for proj in projects[:3]:
            profile_lines.append(f"Project: {proj.get('name', '')} — {proj.get('description', '')[:120]}")
        for edu in education[:2]:
            profile_lines.append(
                f"Education: {edu.get('degree', '')} from {edu.get('institution', '')}"
            )
        profile_text = "\n".join(profile_lines)

        # Question distribution
        tech_count = max(2, round(num_questions * 0.5))
        behav_count = max(1, round(num_questions * 0.3))
        sit_count = num_questions - tech_count - behav_count

        prompt = f"""
You are an expert technical interviewer. Based on this candidate's profile, generate exactly {num_questions} personalized interview questions.

{profile_text}

Requirements:
- Questions MUST reference their actual skills, projects, companies
- {tech_count} Technical questions (deep dive into their specific tech stack)
- {behav_count} Behavioral questions (based on their actual experience)
- {sit_count} Situational/Career questions (relevant to their background)
- Make every question specific — NOT generic

Return ONLY the {num_questions} questions, numbered 1-{num_questions}, one per line. No extra text.
"""

        try:
            raw = _generate(prompt)
            questions = self._parse_numbered_list(raw, num_questions)

            # Fallback if not enough questions
            if len(questions) < num_questions:
                fallbacks = [
                    f"Tell me about yourself and your background, {name}.",
                    f"Walk me through a challenging project involving {skills[0] if skills else 'your stack'}.",
                    "Describe a time you had to meet a tight deadline. How did you handle it?",
                    "What's the hardest technical problem you've solved? Walk me through it.",
                    f"Where do you see your career going in the next 3 years?",
                ]
                while len(questions) < num_questions and fallbacks:
                    questions.append(fallbacks.pop(0))

            return questions[:num_questions]

        except Exception as e:
            logger.error(f"Question generation error: {e}")
            return [
                f"Tell me about yourself, {name}.",
                f"Walk me through your experience with {', '.join(skills[:2]) if skills else 'your main skills'}.",
                "Describe a challenging technical problem you solved.",
                "How do you handle competing priorities and tight deadlines?",
                "What are your career goals for the next 3–5 years?",
            ][:num_questions]

    # ── 3. Evaluate a single answer ───────────────────────────────────────────

    def evaluate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        if not answer or not answer.strip():
            return {
                "score": 0,
                "feedback": "No answer was provided.",
                "strengths": [],
                "improvements": ["Provide a complete answer to the question."],
                "suggestions": ["Take time to think before answering."],
            }

        # Step 1: Generate an ideal answer for similarity scoring
        ideal_prompt = f"""
Provide a concise, professional model answer (100–150 words) to this interview question:
"{question}"
Be specific, relevant, and demonstrate clear competence.
"""
        try:
            ideal_answer = _generate(ideal_prompt)
        except Exception:
            ideal_answer = answer  # fallback — compare against itself

        # Step 2: TF-IDF similarity score
        similarity_score = self._calculate_similarity(answer, ideal_answer)

        # Step 3: Gemini qualitative feedback
        feedback_prompt = f"""
Evaluate this interview answer and provide structured feedback.

Question: "{question}"
Candidate's Answer: "{answer}"
Model Answer: "{ideal_answer}"

Respond in this EXACT format (no extra text):
SCORE: [0-100]
STRENGTHS: [2-3 strengths, separated by semicolons]
IMPROVEMENTS: [2-3 improvement areas, separated by semicolons]
SUGGESTIONS: [2-3 actionable suggestions, separated by semicolons]
SUMMARY: [2-sentence overall assessment]
"""
        try:
            feedback_text = _generate(feedback_prompt)
            parsed = self._parse_evaluation_response(feedback_text)

            # Blend Gemini score with TF-IDF similarity
            ai_score = parsed.get("score", similarity_score)
            final_score = round((float(ai_score) * 0.7 + similarity_score * 0.3), 1)
            final_score = max(0, min(100, final_score))

            return {
                "score": final_score,
                "feedback": parsed.get("summary", "Answer evaluated."),
                "strengths": parsed.get("strengths", []),
                "improvements": parsed.get("improvements", []),
                "suggestions": parsed.get("suggestions", []),
            }

        except Exception as e:
            logger.error(f"Answer evaluation error: {e}")
            return {
                "score": similarity_score,
                "feedback": "Your answer has been recorded. Aim for more specific examples.",
                "strengths": ["Attempted to answer the question"],
                "improvements": ["Provide concrete examples", "Structure your answer clearly"],
                "suggestions": ["Use the STAR method (Situation, Task, Action, Result)"],
            }

    # ── 4. Generate full final report ─────────────────────────────────────────

    def generate_final_report(self, qa_pairs: List[Dict]) -> Dict[str, Any]:
        """
        qa_pairs: [{ question, answer, score }, ...]
        """
        scores = [item.get("score", 0) for item in qa_pairs]
        avg_score = round(float(np.mean(scores)), 1) if scores else 0

        # Build transcript
        transcript_lines = []
        for i, item in enumerate(qa_pairs, 1):
            transcript_lines.append(f"Q{i}: {item.get('question', '')}")
            transcript_lines.append(f"A{i}: {item.get('answer', '')} [Score: {item.get('score', 0)}]")
            transcript_lines.append("")
        transcript = "\n".join(transcript_lines)

        prompt = f"""
You are evaluating a completed interview. Based on the full transcript below, provide a comprehensive evaluation.

Average Score: {avg_score}/100

Full Transcript:
{transcript}

Respond in this EXACT format (no extra text):
OVERALL_SCORE: [0-100]
TECHNICAL_SKILLS: [0-100]
COMMUNICATION: [0-100]
PROBLEM_SOLVING: [0-100]
SUMMARY: [2-3 sentence overall assessment of the candidate]
STRENGTHS: [top 3 strengths, separated by semicolons]
AREAS_FOR_IMPROVEMENT: [top 3 improvement areas, separated by semicolons]
"""

        try:
            raw = _generate(prompt)
            result = self._parse_report_response(raw, avg_score)
            return result
        except Exception as e:
            logger.error(f"Final report error: {e}")
            return {
                "overall_score": int(avg_score),
                "technical_skills": int(avg_score),
                "communication": int(avg_score * 0.9),
                "problem_solving": int(avg_score * 0.95),
                "summary": "The candidate completed the interview and demonstrated knowledge across the assessed areas.",
                "strengths": ["Completed all questions", "Demonstrated technical awareness"],
                "areas_for_improvement": ["Provide more specific examples", "Structure answers using STAR method"],
            }

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        try:
            matrix = self.vectorizer.fit_transform([text1, text2])
            score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
            return round(float(score) * 100, 1)
        except Exception:
            return 50.0

    def _parse_numbered_list(self, text: str, max_items: int) -> List[str]:
        questions = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Match numbered lines like "1.", "1)", "1 "
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            cleaned = re.sub(r"^[-•*]\s*", "", cleaned).strip()
            if cleaned and len(cleaned) > 10:
                questions.append(cleaned)
            if len(questions) >= max_items:
                break
        return questions

    def _parse_evaluation_response(self, text: str) -> Dict:
        result = {"score": 70, "strengths": [], "improvements": [], "suggestions": [], "summary": ""}

        score_m = re.search(r"SCORE:\s*(\d+)", text, re.IGNORECASE)
        if score_m:
            result["score"] = int(score_m.group(1))

        for field, key in [("STRENGTHS", "strengths"), ("IMPROVEMENTS", "improvements"), ("SUGGESTIONS", "suggestions")]:
            m = re.search(rf"{field}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.IGNORECASE | re.DOTALL)
            if m:
                raw = m.group(1).strip()
                items = [s.strip() for s in re.split(r"[;•\-\*\n]", raw) if s.strip()]
                result[key] = [i for i in items if len(i) > 3]

        summary_m = re.search(r"SUMMARY:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.IGNORECASE | re.DOTALL)
        if summary_m:
            result["summary"] = summary_m.group(1).strip()

        return result

    def _parse_report_response(self, text: str, fallback_score: float) -> Dict:
        result = {
            "overall_score": int(fallback_score),
            "technical_skills": int(fallback_score),
            "communication": int(fallback_score),
            "problem_solving": int(fallback_score),
            "summary": "",
            "strengths": [],
            "areas_for_improvement": [],
        }

        for field, key in [
            ("OVERALL_SCORE", "overall_score"),
            ("TECHNICAL_SKILLS", "technical_skills"),
            ("COMMUNICATION", "communication"),
            ("PROBLEM_SOLVING", "problem_solving"),
        ]:
            m = re.search(rf"{field}:\s*(\d+)", text, re.IGNORECASE)
            if m:
                result[key] = int(m.group(1))

        summary_m = re.search(r"SUMMARY:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.IGNORECASE | re.DOTALL)
        if summary_m:
            result["summary"] = summary_m.group(1).strip()

        for field, key in [("STRENGTHS", "strengths"), ("AREAS_FOR_IMPROVEMENT", "areas_for_improvement")]:
            m = re.search(rf"{field}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.IGNORECASE | re.DOTALL)
            if m:
                raw = m.group(1).strip()
                result[key] = [s.strip() for s in re.split(r"[;•\-\*\n]", raw) if s.strip() and len(s.strip()) > 3]

        return result


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions (called by main.py endpoints)
# ─────────────────────────────────────────────────────────────────────────────

_engine = None


def _get_engine() -> InterviewEngine:
    global _engine
    if _engine is None:
        _engine = InterviewEngine()
    return _engine


def parse_resume_for_interview(pdf_bytes: bytes, filename: str) -> Dict:
    """Extract PDF text then parse resume into structured data."""
    text = extract_text_from_pdf_bytes(pdf_bytes)
    if not text.strip():
        raise ValueError("Could not extract text from the uploaded PDF.")
    engine = _get_engine()
    resume_data = engine.parse_resume(text)
    return resume_data


def generate_questions(resume_data: Dict, num: int = 5) -> List[str]:
    """Generate N personalized interview questions."""
    return _get_engine().generate_questions(resume_data, num_questions=num)


def evaluate_answer(question: str, answer: str) -> Dict:
    """Evaluate a single answer and return score + feedback."""
    return _get_engine().evaluate_answer(question, answer)


def generate_final_report(qa_pairs: List[Dict]) -> Dict:
    """Generate overall interview report from all Q&A pairs."""
    return _get_engine().generate_final_report(qa_pairs)
