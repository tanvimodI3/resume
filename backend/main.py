from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import shutil
import os
from typing import List

from . import models, schemas, auth, database, parser_service

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
models.Base.metadata.create_all(bind=database.engine)

@app.post("/auth/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    hashed_pwd = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_pwd)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already registered")

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: auth.OAuth2PasswordBearer = Depends(), db: Session = Depends(database.get_db)):
    # Standard OAuth2 behavior expects username and password
    # But since we might use simple JSON from frontend, let's create a custom route
    pass # Wait, OAuth2PasswordRequestForm is better

from fastapi.security import OAuth2PasswordRequestForm

@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/parse", response_model=schemas.ScanResultResponse)
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
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
            match_score=result_dict["match_score"],
            missing_skills=result_dict["missing_skills"],
            strengths=result_dict["strengths"],
            job_description=job_description
        )
        db.add(scan_result)
        db.commit()
        db.refresh(scan_result)
        return scan_result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/history", response_model=List[schemas.ScanResultResponse])
def get_user_history(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    results = db.query(models.ScanResult).filter(models.ScanResult.user_id == current_user.id).order_by(models.ScanResult.id.desc()).all()
    return results
