"""
FastAPI wrapper for the ATS Resume-Job Matcher
Imports and uses all logic from app.py
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
import uvicorn
#app= FastAPI() #fast api object 

#@app.post("/query")
# Ensure the repository root is on sys.path so backend/api.py can import app.py.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ─────────────────────────────────────────────────────────
# IMPORT ALL LOGIC FROM app.py
# ─────────────────────────────────────────────────────────
from app import (
    extract_text_from_file,
    extract_text_from_upload,
    extract_info_with_cohere,
    extract_skills_with_cohere,
    normalize_skills_with_cohere,
    chunk_text,
    build_vectorstore,
    compute_embedding_score,
    evaluate_with_cohere,
    compute_final_score,
    run_pipeline
)
from auth import hash_password, verify_password
from db import create_user, get_connection, get_user_by_email
from oauth import oauth
from langchain_cohere import CohereEmbeddings

# ─────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────

class NormalizedSkill(BaseModel):
    skill: str
    category: str


class CandidateInfoResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    experience: Optional[str] = None
    profiles: List[str] = []


class SkillExtractionResponse(BaseModel):
    raw_skills: List[str]
    normalized_skills: List[NormalizedSkill]
    total_skills: int


class LLMEvaluation(BaseModel):
    match_percentage: int = Field(..., ge=0, le=100)
    missing_skills: List[str] = []
    strengths: List[str] = []


class MatchScore(BaseModel):
    embedding_score: float = Field(..., ge=0, le=100)
    llm_score: float = Field(..., ge=0, le=100)
    final_score: float = Field(..., ge=0, le=100)


class ResumeMatchResponse(BaseModel):
    candidate_info: CandidateInfoResponse
    skills: SkillExtractionResponse
    scores: MatchScore
    llm_evaluation: LLMEvaluation
    processed_at: datetime


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime


class TextExtractionResponse(BaseModel):
    filename: str
    text: str
    character_count: int
    word_count: int


# ─────────────────────────────────────────────────────────
# INTERNAL HELPER FOR PIPELINE LOGIC
# ─────────────────────────────────────────────────────────

def _run_full_pipeline(resume_text: str, job_description: str) -> dict:
    """
    Runs the full matching pipeline and returns structured data.
    Uses all logic from app.py
    """
    try:
        # Step 1 — Extract candidate info
        logger.info("[1/8] Extracting candidate info (Cohere)...")
        info = extract_info_with_cohere(resume_text)

        # Step 2 — Extract skills
        logger.info("[2/8] Extracting skills (Cohere)...")
        raw_skills = extract_skills_with_cohere(resume_text)

        # Step 3 — Normalize skills
        logger.info("[3/8] Normalizing skills (Cohere)...")
        normalized_skills = normalize_skills_with_cohere(raw_skills)

        # Step 4 — Chunk resume text
        logger.info("[4/8] Chunking resume text...")
        chunks = chunk_text(resume_text)

        # Step 5 — Embed + store in ChromaDB
        logger.info("[5/8] Generating embeddings + storing in ChromaDB...")
        embedding_model = CohereEmbeddings(
            model="embed-english-v3.0",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )
        vectorstore = build_vectorstore(chunks, embedding_model)

        # Step 6 — Embedding similarity score
        logger.info("[6/8] Computing embedding similarity score...")
        k = min(5, len(chunks))
        embedding_score = compute_embedding_score(vectorstore, job_description, k=k)

        # Step 7 — Cohere LLM evaluation
        logger.info("[7/8] Running Cohere final evaluation...")
        llm_eval = evaluate_with_cohere(resume_text, job_description)
        llm_score = float(llm_eval.get("match_percentage", 0))

        # Step 8 — Final score
        logger.info("[8/8] Computing final score...")
        final_score = compute_final_score(embedding_score, llm_score)

        return {
            "candidate_info": info,
            "normalized_skills": normalized_skills,
            "raw_skills": raw_skills,
            "embedding_score": embedding_score,
            "llm_score": llm_score,
            "final_score": final_score,
            "llm_eval": llm_eval
        }
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise


# ─────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Resume Job verification",
    description="Cohere-powered Applicant Tracking System and profile verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────



@app.get("/", tags=["Info"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "ATS Resume-Job Matcher API",
        "version": "1.0.0",
        "description": "Cohere-powered resume to job matching system",
        "docs": "/docs",
        "health": "/health"
    }



@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/signup")
async def signup(data: dict):

    name=data["name"]
    email=data["email"]
    password=data["password"]

    if get_user_by_email(email):
        raise HTTPException(400,"User exists")

    hashed=hash_password(password)

    user=create_user(name,email,hashed)

    return {"user":user}



# Login


@app.post("/login")
async def login(data:dict):

    email=data["email"]
    password=data["password"]

    user=get_user_by_email(email)

    if not user:
        raise HTTPException(400,"Invalid email")

    if not verify_password(password,user["password"]):
        raise HTTPException(400,"Wrong password")

    return {"user":user}


# Google OAuth
@app.get("/auth/google")
async def google_login(request:Request):

    redirect_uri="http://localhost:8000/auth/google/callback"

    return await oauth.google.authorize_redirect(request,redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request:Request):

    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo", {})

    email = user.get("email")
    name = user.get("name")

    if not email or not name:
        raise HTTPException(status_code=400, detail="Google OAuth did not return required user information")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE email=%s',
                (email,)
            )
            existing = cursor.fetchone()

            if not existing:
                cursor.execute(
                    'INSERT INTO users (name, email, password) VALUES (%s, %s, %s)',
                    (name, email, "oauth")
                )
                conn.commit()
    finally:
        conn.close()

    return RedirectResponse(os.getenv("FRONTEND_URL") + "/login")

@app.post("/extract-text", response_model=TextExtractionResponse, tags=["Resume Processing"])
async def extract_text_endpoint(file: UploadFile = File(...)):
    """
    Extract text from a resume file (PDF, DOCX, or TXT).
    
    **Parameters:**
    - file: Resume file (PDF, DOCX, or TXT format)
    
    **Returns:**
    - filename: Name of the uploaded file
    - text: Extracted text content
    - character_count: Total characters extracted
    - word_count: Total words extracted
    """
    try:
        if file.filename is None:
            raise ValueError("Filename is required")
        
        logger.info(f"Extracting text from file: {file.filename}")
        contents = await file.read()
        
        # Validate file size (10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
        
        text = extract_text_from_upload(contents, file.filename)
        
        logger.info(f"Successfully extracted {len(text)} characters")
        
        return TextExtractionResponse(
            filename=file.filename,
            text=text,
            character_count=len(text),
            word_count=len(text.split())
        )
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise HTTPException(status_code=500, detail="Error extracting text from file")


@app.post("/extract-skills", response_model=SkillExtractionResponse, tags=["Resume Processing"])
async def extract_skills_endpoint(resume_text: str = Query(..., min_length=10)):
    """
    Extract and normalize skills from resume text.
    
    **Parameters:**
    - resume_text: Raw resume text (query parameter, minimum 10 characters)
    
    **Returns:**
    - raw_skills: List of extracted skills as found in resume
    - normalized_skills: Skills categorized and normalized
    - total_skills: Total count of unique skills
    
    **Example:**
    ```
    GET /extract-skills?resume_text=I have experience with Python, React, and Docker
    ```
    """
    try:
        if not resume_text or len(resume_text.strip()) < 10:
            raise ValueError("Resume text must be at least 10 characters")
        
        logger.info("Extracting skills from resume...")
        raw_skills = extract_skills_with_cohere(resume_text)
        
        logger.info("Normalizing skills...")
        normalized_skills_list = normalize_skills_with_cohere(raw_skills)
        
        normalized_skills = [
            NormalizedSkill(skill=s["skill"], category=s["category"])
            for s in normalized_skills_list
        ]
        
        logger.info(f"Extracted {len(raw_skills)} skills")
        
        return SkillExtractionResponse(
            raw_skills=raw_skills,
            normalized_skills=normalized_skills,
            total_skills=len(raw_skills)
        )
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error extracting skills: {str(e)}")
        raise HTTPException(status_code=500, detail="Error extracting skills")


@app.post("/extract-candidate-info", response_model=CandidateInfoResponse, tags=["Resume Processing"])
async def extract_candidate_info_endpoint(resume_text: str = Query(..., min_length=10)):
    """
    Extract candidate information from resume text.
    
    **Parameters:**
    - resume_text: Raw resume text (query parameter, minimum 10 characters)
    
    **Returns:**
    - name: Candidate's full name
    - email: Email address
    - phone: Phone number
    - experience: Years of experience
    - profiles: List of LinkedIn, GitHub, or portfolio URLs
    
    **Example:**
    ```
    GET /extract-candidate-info?resume_text=John Doe, john@example.com, 5 years experience...
    ```
    """
    try:
        if not resume_text or len(resume_text.strip()) < 10:
            raise ValueError("Resume text must be at least 10 characters")
        
        logger.info("Extracting candidate info...")
        info = extract_info_with_cohere(resume_text)
        
        logger.info(f"Extracted info for: {info.get('name', 'Unknown')}")
        
        return CandidateInfoResponse(
            name=info.get("name"),
            email=info.get("email"),
            phone=info.get("phone"),
            experience=info.get("experience"),
            profiles=info.get("profiles", [])
        )
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error extracting candidate info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error extracting candidate information")


@app.post("/match-resume-to-job", response_model=ResumeMatchResponse, tags=["Matching"])
async def match_resume_to_job_endpoint(
    resume_text: str = Query(..., min_length=10),
    job_description: str = Query(..., min_length=10)
):
    """
    Match a resume against a job description using embedding + LLM scoring.
    
    **Parameters:**
    - resume_text: Raw resume text (query parameter, minimum 10 characters)
    - job_description: Job description text (query parameter, minimum 10 characters)
    
    **Returns:**
    - candidate_info: Extracted candidate information
    - skills: Extracted and normalized skills
    - scores: Embedding score, LLM score, and final combined score
    - llm_evaluation: Missing skills and candidate strengths
    - processed_at: Timestamp of when matching was performed
    
    **Scoring:**
    - Final Score = (0.7 × Embedding Score) + (0.3 × LLM Score)
    
    **Example:**
    ```
    POST /match-resume-to-job?resume_text=...&job_description=...
    ```
    """
    try:
        if not resume_text or len(resume_text.strip()) < 10:
            raise ValueError("Resume text must be at least 10 characters")
        if not job_description or len(job_description.strip()) < 10:
            raise ValueError("Job description must be at least 10 characters")
        
        logger.info("Starting resume-to-job matching...")
        
        result = _run_full_pipeline(resume_text, job_description)
        
        candidate_info = CandidateInfoResponse(
            name=result["candidate_info"].get("name"),
            email=result["candidate_info"].get("email"),
            phone=result["candidate_info"].get("phone"),
            experience=result["candidate_info"].get("experience"),
            profiles=result["candidate_info"].get("profiles", [])
        )
        
        normalized_skills = [
            NormalizedSkill(skill=s["skill"], category=s["category"])
            for s in result["normalized_skills"]
        ]
        
        skills_response = SkillExtractionResponse(
            raw_skills=result["raw_skills"],
            normalized_skills=normalized_skills,
            total_skills=len(result["raw_skills"])
        )
        
        scores = MatchScore(
            embedding_score=result["embedding_score"],
            llm_score=result["llm_score"],
            final_score=result["final_score"]
        )
        
        llm_eval = LLMEvaluation(
            match_percentage=result["llm_eval"].get("match_percentage", 0),
            missing_skills=result["llm_eval"].get("missing_skills", []),
            strengths=result["llm_eval"].get("strengths", [])
        )
        
        logger.info(f"Matching complete. Final score: {result['final_score']}%")
        
        return ResumeMatchResponse(
            candidate_info=candidate_info,
            skills=skills_response,
            scores=scores,
            llm_evaluation=llm_eval,
            processed_at=datetime.utcnow()
        )
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in matching: {str(e)}")
        raise HTTPException(status_code=500, detail="Error performing match")


@app.post("/match-resume-file-to-job", response_model=ResumeMatchResponse, tags=["Matching"])
async def match_resume_file_to_job_endpoint(
    file: UploadFile = File(...),
    job_description: str = Query(..., min_length=10)
):
    """
    Match a resume file against a job description.
    
    **Parameters:**
    - file: Resume file (PDF, DOCX, or TXT format) - form-data
    - job_description: Job description text (query parameter, minimum 10 characters)
    
    **Returns:**
    - candidate_info: Extracted candidate information
    - skills: Extracted and normalized skills
    - scores: Embedding, LLM, and final match scores
    - llm_evaluation: Missing skills and strengths
    - processed_at: Timestamp of processing
    
    **File Size Limit:** 10MB
    
    **Example:**
    ```
    POST /match-resume-file-to-job
    
    Form Data:
    - file: <resume.pdf>
    - job_description: <job description text>
    ```
    """
    try:
        if file.filename is None:
            raise ValueError("Filename is required")
        
        logger.info(f"Processing resume file: {file.filename}")
        contents = await file.read()
        
        MAX_FILE_SIZE = 10 * 1024 * 1024
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")
        
        resume_text = extract_text_from_upload(contents, file.filename)
        
        result = _run_full_pipeline(resume_text, job_description)
        
        candidate_info = CandidateInfoResponse(
            name=result["candidate_info"].get("name"),
            email=result["candidate_info"].get("email"),
            phone=result["candidate_info"].get("phone"),
            experience=result["candidate_info"].get("experience"),
            profiles=result["candidate_info"].get("profiles", [])
        )
        
        normalized_skills = [
            NormalizedSkill(skill=s["skill"], category=s["category"])
            for s in result["normalized_skills"]
        ]
        
        skills_response = SkillExtractionResponse(
            raw_skills=result["raw_skills"],
            normalized_skills=normalized_skills,
            total_skills=len(result["raw_skills"])
        )
        
        scores = MatchScore(
            embedding_score=result["embedding_score"],
            llm_score=result["llm_score"],
            final_score=result["final_score"]
        )
        
        llm_eval = LLMEvaluation(
            match_percentage=result["llm_eval"].get("match_percentage", 0),
            missing_skills=result["llm_eval"].get("missing_skills", []),
            strengths=result["llm_eval"].get("strengths", [])
        )
        
        logger.info(f"File matching complete. Final score: {result['final_score']}%")
        
        return ResumeMatchResponse(
            candidate_info=candidate_info,
            skills=skills_response,
            scores=scores,
            llm_evaluation=llm_eval,
            processed_at=datetime.utcnow()
        )
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in file matching: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing resume file")


@app.post("/batch-match", tags=["Matching"])
async def batch_match_endpoint(
    files: List[UploadFile] = File(...),
    job_description: str = Query(..., min_length=10)
):
    """
    Match multiple resume files against a single job description.
    
    **Parameters:**
    - files: List of resume files (PDF, DOCX, or TXT format)
    - job_description: Job description text (query parameter)
    
    **Returns:**
    - total_submitted: Number of files submitted
    - total_processed: Number successfully processed
    - total_errors: Number failed to process
    - results: Array of match results for each resume
    
    **Example:**
    ```
    POST /batch-match
    
    Form Data:
    - files: [resume1.pdf, resume2.pdf, resume3.pdf]
    - job_description: <job description text>
    ```
    """
    try:
        if not job_description or len(job_description.strip()) < 10:
            raise ValueError("Job description must be at least 10 characters")
        
        if not files or len(files) == 0:
            raise ValueError("At least one resume file is required")
        
        logger.info(f"Starting batch matching for {len(files)} resumes...")
        
        results = []
        for file in files:
            try:
                if file.filename is None:
                    logger.warning("Skipping file with no filename")
                    continue
                
                contents = await file.read()
                MAX_FILE_SIZE = 10 * 1024 * 1024
                if len(contents) > MAX_FILE_SIZE:
                    logger.warning(f"File {file.filename} exceeds size limit, skipping")
                    continue
                
                logger.info(f"Processing {file.filename}...")
                resume_text = extract_text_from_upload(contents, file.filename)
                
                result = _run_full_pipeline(resume_text, job_description)
                
                candidate_info = CandidateInfoResponse(
                    name=result["candidate_info"].get("name"),
                    email=result["candidate_info"].get("email"),
                    phone=result["candidate_info"].get("phone"),
                    experience=result["candidate_info"].get("experience"),
                    profiles=result["candidate_info"].get("profiles", [])
                )
                
                normalized_skills = [
                    NormalizedSkill(skill=s["skill"], category=s["category"])
                    for s in result["normalized_skills"]
                ]
                
                skills_response = SkillExtractionResponse(
                    raw_skills=result["raw_skills"],
                    normalized_skills=normalized_skills,
                    total_skills=len(result["raw_skills"])
                )
                
                scores = MatchScore(
                    embedding_score=result["embedding_score"],
                    llm_score=result["llm_score"],
                    final_score=result["final_score"]
                )
                
                llm_eval = LLMEvaluation(
                    match_percentage=result["llm_eval"].get("match_percentage", 0),
                    missing_skills=result["llm_eval"].get("missing_skills", []),
                    strengths=result["llm_eval"].get("strengths", [])
                )
                
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "match": ResumeMatchResponse(
                        candidate_info=candidate_info,
                        skills=skills_response,
                        scores=scores,
                        llm_evaluation=llm_eval,
                        processed_at=datetime.utcnow()
                    )
                })
                
                logger.info(f"✓ {file.filename}: {result['final_score']}%")
            
            except Exception as e:
                logger.error(f"Error matching {file.filename}: {str(e)}")
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "total_submitted": len(files),
            "total_processed": len([r for r in results if r["status"] == "success"]),
            "total_errors": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in batch_match: {str(e)}")
        raise HTTPException(status_code=500, detail="Error in batch matching")


# ─────────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "status_code": 500
    }


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    #logger.info("Starting ATS Resume Matcher API...")
    logger.info("FastAPI Docs available at: http://localhost:8000/docs")
    logger.info("ReDoc available at: http://localhost:8000/redoc")
    default_port = int(os.getenv("PORT", "8000"))
    for port in (default_port, default_port + 1, default_port + 2):
        try:
            uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
            break
        except OSError as err:
            message = str(err).lower()
            if "address already in use" in message or "only one usage" in message:
                logger.warning(f"Port {port} is already in use. Trying next port...")
                continue
            raise
    else:
        logger.error(
            "Unable to bind to any available port. Stop the service using port 8000 or set PORT to a different port."
        )
        raise RuntimeError(
            "Unable to bind to any available port. Set PORT to a different value or stop the process using port 8000."
        )