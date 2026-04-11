from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import shutil
import os
from typing import List
from datetime import timedelta

import db
from services import models, schemas, auth, parser_service, github_fetcher, leetcode_fetcher

app = FastAPI(title="AI Resume ATS API")

# Setup CORS for Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"], # For development
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



@app.post("/auth/token", response_model=schemas.Token)
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
        try:
            result_dict = parser_service.parse_resume(temp_path, job_description)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))
        
        # Save to DB
        scan_result = models.ScanResult(
            user_id=current_user.id,
            filename=file.filename,
            name=result_dict["name"],
            email=result_dict.get("email"),
            phone=result_dict.get("phone"),
            experience=result_dict["experience"],
            profiles=result_dict["profiles"],
            match_score=result_dict["match_score"],
            missing_skills=result_dict["missing_skills"],
            strengths=result_dict["strengths"],
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

@app.get("/github")
async def github_details(session: Session = Depends(db.get_db), current_user: models.User = Depends(auth.get_current_user)):
    scan_result = session.query(models.ScanResult).filter(
        models.ScanResult.user_id == current_user.id
    ).order_by(models.ScanResult.id.desc()).first()
    
    if not scan_result or not scan_result.github_url:
        return {"error": "No GitHub URL found"}
    
    result = await github_fetcher.fetch_github_profile(scan_result.github_url)
    return result

@app.get("/leetcode")
async def leetcode_details(session: Session = Depends(db.get_db), current_user: models.User = Depends(auth.get_current_user)):
    scan_result = session.query(models.ScanResult).filter(
        models.ScanResult.user_id == current_user.id
    ).order_by(models.ScanResult.id.desc()).first()
    
    if not scan_result or not scan_result.leetcode_url:
        return {"error": "No LeetCode URL found"}
    
    result = await leetcode_fetcher.fetch_leetcode_profile(scan_result.leetcode_url)
    return result

@app.get("/api/history", response_model=List[schemas.ScanResultResponse])
def get_user_history(current_user: models.User = Depends(auth.get_current_user), session: Session = Depends(db.get_db)):
    results = session.query(models.ScanResult).filter(models.ScanResult.user_id == current_user.id).order_by(models.ScanResult.id.desc()).all()
    return results
