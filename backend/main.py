import os
import sys
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

import uvicorn





from backend import db
from backend.services import models, schemas, auth, parser_service, github_fetcher, leetcode_fetcher
from backend.oauth import oauth
from services.linkedin_extraction import get_full_candidate_profile
from langchain_cohere import CohereEmbeddings
from backend.services import interviewer_service
from backend.services import profile_service

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
# INTERNAL HELPER
# ─────────────────────────────────────────────────────────

def _run_full_pipeline(resume_text: str, job_description: str) -> dict:
    try:
        logger.info("[1/8] Extracting candidate info...")
        info = parser_service.extract_info_with_cohere(resume_text)

        logger.info("[2/8] Extracting skills...")
        raw_skills = parser_service.extract_skills_with_cohere(resume_text)

        logger.info("[3/8] Normalizing skills...")
        normalized_skills = parser_service.normalize_skills_with_cohere(raw_skills)

        logger.info("[4/8] Chunking resume text...")
        chunks = parser_service.chunk_text(resume_text)

        logger.info("[5/8] Generating embeddings...")
        embedding_model = CohereEmbeddings(
            model="embed-english-v3.0",
            cohere_api_key=os.getenv("COHERE_API_KEY")
        )
        vectorstore = parser_service.build_vectorstore(chunks, embedding_model)

        logger.info("[6/8] Computing embedding score...")
        k = min(5, len(chunks)) if len(chunks) > 0 else 1
        embedding_score = parser_service.compute_embedding_score(vectorstore, job_description, k=k)

        logger.info("[7/8] Running LLM evaluation...")
        llm_eval = parser_service.evaluate_with_cohere(resume_text, job_description)
        llm_score = float(llm_eval.get("match_percentage", 0))

        logger.info("[8/8] Computing final score...")
        final_score = parser_service.compute_final_score(embedding_score, llm_score)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=db.engine)


# ─────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
async def root():
    return {
        "name": "ATS Resume-Job Matcher API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    return HealthCheckResponse(status="healthy", timestamp=datetime.utcnow())


# ── Auth ─────────────────────────────────────────────────

@app.post("/auth/signup", response_model=schemas.UserResponse, tags=["Auth"])
def signup(user: schemas.UserCreate, session: Session = Depends(db.get_db)):
    hashed_pwd = auth.get_password_hash(user.password)
    db_user = models.User(name=user.name, email=user.email, password=hashed_pwd)
    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")


@app.post("/auth/token", response_model=schemas.Token, tags=["Auth"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(db.get_db)):
    user = session.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/google", tags=["Auth"])
async def google_login(request: Request):
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback", tags=["Auth"])
async def google_callback(request: Request, session: Session = Depends(db.get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo", {})
    email = user_info.get("email")
    name = user_info.get("name")

    if not email or not name:
        raise HTTPException(status_code=400, detail="Google OAuth did not return required user information")

    user = session.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(name=name, email=email, password="oauth")
        session.add(user)
        session.commit()
        session.refresh(user)

    return RedirectResponse(os.getenv("FRONTEND_URL", "http://localhost:3000") + "/login")


# ── Resume Parse ─────────────────────────────────────────

@app.post("/api/parse", response_model=schemas.ScanResultResponse, tags=["Matching"])
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db)
):
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            result_dict = parser_service.parse_resume(temp_path, job_description)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))

        scan_result = models.ScanResult(
            user_id=current_user.id,
            filename=file.filename,
            name=result_dict.get("name", "Unknown"),
            email=result_dict.get("email"),
            phone=result_dict.get("phone"),
            experience=result_dict.get("experience", "Unknown"),
            profiles=result_dict.get("profiles", []),
            skills=result_dict.get("skills", []),
            match_score=result_dict.get("match_score", 0),
            missing_skills=result_dict.get("missing_skills", []),
            strengths=result_dict.get("strengths", []),
            job_description=job_description,
            github_url=result_dict.get("github_url"),
            leetcode_url=result_dict.get("leetcode_url")
        )
        session.add(scan_result)
        session.commit()
        session.refresh(scan_result)
        return scan_result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ── Profile Verification ─────────────────────────────────

@app.get("/github", tags=["Profile Verification"])
async def github_details(
    session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    scan_result = session.query(models.ScanResult).filter(
        models.ScanResult.user_id == current_user.id
    ).order_by(models.ScanResult.id.desc()).first()

    if not scan_result or not scan_result.github_url:
        return {"error": "No GitHub URL found"}

    result = await github_fetcher.fetch_github_profile(scan_result.github_url)
    return result


@app.get("/leetcode", tags=["Profile Verification"])
async def leetcode_details(
    session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    scan_result = session.query(models.ScanResult).filter(
        models.ScanResult.user_id == current_user.id
    ).order_by(models.ScanResult.id.desc()).first()

    if not scan_result or not scan_result.leetcode_url:
        return {"error": "No LeetCode URL found"}

    result = await leetcode_fetcher.fetch_leetcode_profile(scan_result.leetcode_url)
    return result


# ── History & Me ─────────────────────────────────────────

@app.get("/api/history", response_model=List[schemas.ScanResultResponse], tags=["Matching"])
def get_user_history(current_user: models.User = Depends(auth.get_current_user), session: Session = Depends(db.get_db)):
    results = session.query(models.ScanResult).filter(
        models.ScanResult.user_id == current_user.id
    ).order_by(models.ScanResult.id.desc()).all()
    return results


@app.get("/api/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ── AI Interviewer ────────────────────────────────────────

@app.post("/api/interview/start")
async def interview_start(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    try:
        resume_data = interviewer_service.parse_resume_for_interview(contents, file.filename)
        questions = interviewer_service.generate_questions(resume_data, num=5)
        return {"resume_data": resume_data, "questions": questions}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@app.post("/api/interview/evaluate")
async def interview_evaluate(
    data: dict,
    current_user: models.User = Depends(auth.get_current_user),
):
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    try:
        result = interviewer_service.evaluate_answer(question, answer)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/api/interview/report")
async def interview_report(
    data: dict,
    current_user: models.User = Depends(auth.get_current_user),
):
    qa_pairs = data.get("qa_pairs", [])
    if not qa_pairs:
        raise HTTPException(status_code=400, detail="qa_pairs is required and must not be empty")

    try:
        report = interviewer_service.generate_final_report(qa_pairs)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ── Core API Tools ────────────────────────────────────────

@app.post("/extract-text", response_model=TextExtractionResponse, tags=["Resume Processing"])
async def extract_text_endpoint(file: UploadFile = File(...)):
    try:
        if file.filename is None:
            raise ValueError("Filename is required")
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise ValueError("File size exceeds 10MB limit")
        text = parser_service.extract_text_from_upload(contents, file.filename)
        return TextExtractionResponse(
            filename=file.filename,
            text=text,
            character_count=len(text),
            word_count=len(text.split())
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error extracting text from file")


@app.post("/extract-skills", response_model=SkillExtractionResponse, tags=["Resume Processing"])
async def extract_skills_endpoint(resume_text: str = Query(..., min_length=10)):
    try:
        raw_skills = parser_service.extract_skills_with_cohere(resume_text)
        normalized_skills_list = parser_service.normalize_skills_with_cohere(raw_skills)
        normalized_skills = [NormalizedSkill(skill=s["skill"], category=s["category"]) for s in normalized_skills_list]
        return SkillExtractionResponse(raw_skills=raw_skills, normalized_skills=normalized_skills, total_skills=len(raw_skills))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error extracting skills")


@app.post("/extract-candidate-info", response_model=CandidateInfoResponse, tags=["Resume Processing"])
async def extract_candidate_info_endpoint(resume_text: str = Query(..., min_length=10)):
    try:
        info = parser_service.extract_info_with_cohere(resume_text)
        return CandidateInfoResponse(
            name=info.get("name"),
            email=info.get("email"),
            phone=info.get("phone"),
            experience=info.get("experience"),
            profiles=info.get("profiles", [])
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error extracting candidate information")


@app.post("/match-resume-to-job", response_model=ResumeMatchResponse, tags=["Matching"])
async def match_resume_to_job_endpoint(
    resume_text: str = Query(..., min_length=10),
    job_description: str = Query(..., min_length=10)
):
    try:
        result = _run_full_pipeline(resume_text, job_description)
        candidate_info = CandidateInfoResponse(**{k: result["candidate_info"].get(k) for k in ["name", "email", "phone", "experience"]}, profiles=result["candidate_info"].get("profiles", []))
        normalized_skills = [NormalizedSkill(skill=s["skill"], category=s["category"]) for s in result["normalized_skills"]]
        skills_response = SkillExtractionResponse(raw_skills=result["raw_skills"], normalized_skills=normalized_skills, total_skills=len(result["raw_skills"]))
        scores = MatchScore(embedding_score=result["embedding_score"], llm_score=result["llm_score"], final_score=result["final_score"])
        llm_eval = LLMEvaluation(match_percentage=result["llm_eval"].get("match_percentage", 0), missing_skills=result["llm_eval"].get("missing_skills", []), strengths=result["llm_eval"].get("strengths", []))
        return ResumeMatchResponse(candidate_info=candidate_info, skills=skills_response, scores=scores, llm_evaluation=llm_eval, processed_at=datetime.utcnow())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error performing match")


@app.post("/match-resume-file-to-job", response_model=ResumeMatchResponse, tags=["Matching"])
async def match_resume_file_to_job_endpoint(
    file: UploadFile = File(...),
    job_description: str = Query(..., min_length=10)
):
    try:
        if file.filename is None:
            raise ValueError("Filename is required")
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise ValueError("File size exceeds 10MB limit")
        resume_text = parser_service.extract_text_from_upload(contents, file.filename)
        result = _run_full_pipeline(resume_text, job_description)
        candidate_info = CandidateInfoResponse(**{k: result["candidate_info"].get(k) for k in ["name", "email", "phone", "experience"]}, profiles=result["candidate_info"].get("profiles", []))
        normalized_skills = [NormalizedSkill(skill=s["skill"], category=s["category"]) for s in result["normalized_skills"]]
        skills_response = SkillExtractionResponse(raw_skills=result["raw_skills"], normalized_skills=normalized_skills, total_skills=len(result["raw_skills"]))
        scores = MatchScore(embedding_score=result["embedding_score"], llm_score=result["llm_score"], final_score=result["final_score"])
        llm_eval = LLMEvaluation(match_percentage=result["llm_eval"].get("match_percentage", 0), missing_skills=result["llm_eval"].get("missing_skills", []), strengths=result["llm_eval"].get("strengths", []))
        return ResumeMatchResponse(candidate_info=candidate_info, skills=skills_response, scores=scores, llm_evaluation=llm_eval, processed_at=datetime.utcnow())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing resume file")


@app.post("/batch-match", tags=["Matching"])
async def batch_match_endpoint(
    files: List[UploadFile] = File(...),
    job_description: str = Query(..., min_length=10)
):
    try:
        results = []
        for file in files:
            try:
                if file.filename is None:
                    continue
                contents = await file.read()
                if len(contents) > 10 * 1024 * 1024:
                    continue
                resume_text = parser_service.extract_text_from_upload(contents, file.filename)
                result = _run_full_pipeline(resume_text, job_description)
                candidate_info = CandidateInfoResponse(**{k: result["candidate_info"].get(k) for k in ["name", "email", "phone", "experience"]}, profiles=result["candidate_info"].get("profiles", []))
                normalized_skills = [NormalizedSkill(skill=s["skill"], category=s["category"]) for s in result["normalized_skills"]]
                skills_response = SkillExtractionResponse(raw_skills=result["raw_skills"], normalized_skills=normalized_skills, total_skills=len(result["raw_skills"]))
                scores = MatchScore(embedding_score=result["embedding_score"], llm_score=result["llm_score"], final_score=result["final_score"])
                llm_eval = LLMEvaluation(match_percentage=result["llm_eval"].get("match_percentage", 0), missing_skills=result["llm_eval"].get("missing_skills", []), strengths=result["llm_eval"].get("strengths", []))
                results.append({"filename": file.filename, "status": "success", "match": ResumeMatchResponse(candidate_info=candidate_info, skills=skills_response, scores=scores, llm_evaluation=llm_eval, processed_at=datetime.utcnow())})
            except Exception as e:
                results.append({"filename": file.filename, "status": "error", "error": str(e)})
        return {
            "total_submitted": len(files),
            "total_processed": len([r for r in results if r["status"] == "success"]),
            "total_errors": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error in batch matching")
    
@app.get("/candidate/linkedin")
def fetch_candidate(linkedin_url: str):
    data = get_full_candidate_profile(linkedin_url)
    return data


# ─────────────────────────────────────────────────────────
# PROFILE VERIFICATION ENDPOINTS
# ─────────────────────────────────────────────────────────

from typing import Any, Dict

class ProfileVerificationScoreRequest(BaseModel):
    resume_skills: List[str]
    profile_data: List[Dict[str, Any]]

class ProfileAnalysisRequest(BaseModel):
    profiles: List[str] = Field(..., min_length=1, description="List of profile URLs to analyze")


@app.post("/api/analyze-profiles", tags=["Profile Verification"])
async def analyze_profiles_endpoint(data: ProfileAnalysisRequest):
    """
    Analyze a list of profile URLs (GitHub, LeetCode, etc.).
    Returns detailed analysis for GitHub and LeetCode profiles,
    and classified links for other platforms.
    """
    try:
        if not data.profiles or len(data.profiles) == 0:
            raise ValueError("At least one profile URL is required")

        # Filter out empty strings
        urls = [u.strip() for u in data.profiles if u and u.strip()]
        if not urls:
            raise ValueError("No valid URLs provided")

        logger.info(f"Analyzing {len(urls)} profile URLs...")
        results = profile_service.classify_and_analyze_profiles(urls)

        return {
            "total_submitted": len(urls),
            "total_analyzed": len([r for r in results if r.get('status') == 'success']),
            "results": results
        }
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing profiles: {str(e)}")
        raise HTTPException(status_code=500, detail="Error analyzing profiles")


@app.post("/api/verify-profiles", tags=["Profile Verification"])
async def verify_profiles_endpoint(data: ProfileVerificationScoreRequest):
    try:
        from backend.services.verification_service import verify_profiles_with_gemini
        result = verify_profiles_with_gemini(data.resume_skills, data.profile_data)
        return result
    except Exception as e:
        logger.error(f"Error in verify-profiles: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating verification score")


# ── Exception Handlers ────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"error": "Internal server error", "status_code": 500})


if __name__ == "__main__":
    default_port = int(os.getenv("PORT", "8000"))
    for port in (default_port, default_port + 1, default_port + 2):
        try:
            uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
            break
        except OSError as err:
            if "address already in use" in str(err).lower() or "only one usage" in str(err).lower():
                continue
            raise
    else:
        logger.error("Unable to bind to any available port.")
        raise RuntimeError("Unable to bind to any available port.")
