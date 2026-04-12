from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import shutil
import os
from typing import List
from fastapi import Request
from fastapi.responses import RedirectResponse
from oauth import oauth

import db
from services import models, schemas, auth, parser_service
from services import interviewer_service

app = FastAPI(title="AI Resume ATS API")

# Setup CORS for Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB tables
models.Base.metadata.create_all(bind=db.engine)

@app.post("/auth/signup", response_model=schemas.UserResponse)
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

from starlette.middleware.sessions import SessionMiddleware
import os

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET")
)

@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(db.get_db)):
    user = session.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/parse", response_model=schemas.ScanResultResponse)
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db)
):
    # Save uploaded file temporarily
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run AI Parser
        result_dict = parser_service.parse_resume(temp_path, job_description)
        
        # Save to DB
        scan_result = models.ScanResult(
            user_id=current_user.id,
            filename=file.filename,
            name=result_dict["name"],
            email=result_dict.get("email"),
            phone=result_dict.get("phone"),
            experience=result_dict["experience"],
            profiles=result_dict["profiles"],
            skills=result_dict.get("skills", []),
            match_score=result_dict["match_score"],
            missing_skills=result_dict["missing_skills"],
            strengths=result_dict["strengths"],
            job_description=job_description
        )
        session.add(scan_result)
        session.commit()
        session.refresh(scan_result)
        return scan_result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/history", response_model=List[schemas.ScanResultResponse])
def get_user_history(current_user: models.User = Depends(auth.get_current_user), session: Session = Depends(db.get_db)):
    results = session.query(models.ScanResult).filter(models.ScanResult.user_id == current_user.id).order_by(models.ScanResult.id.desc()).all()
    return results

@app.get("/api/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ─────────────────────────────────────────────────────────
# AI INTERVIEWER ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.post("/api/interview/start")
async def interview_start(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Upload resume PDF → parse with Gemini → generate 5 personalized questions.
    Returns: { resume_data: {...}, questions: ["Q1", ..., "Q5"] }
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Only accept PDF for the interviewer
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for AI Interviewer")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
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
    """
    Submit one answer → get AI score + structured feedback.
    Body: { question: str, answer: str }
    Returns: { score, feedback, strengths, improvements, suggestions }
    """
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
    """
    Submit all Q&A pairs → get final evaluation report.
    Body: { qa_pairs: [{ question, answer, score }, ...] }
    Returns: { overall_score, technical_skills, communication, problem_solving,
               summary, strengths, areas_for_improvement }
    """
    qa_pairs = data.get("qa_pairs", [])

    if not qa_pairs or len(qa_pairs) == 0:
        raise HTTPException(status_code=400, detail="qa_pairs is required and must not be empty")

    try:
        report = interviewer_service.generate_final_report(qa_pairs)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
