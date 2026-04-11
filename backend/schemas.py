from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ScanResultCreate(BaseModel):
    filename: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    experience: str
    profiles: List[str]
    match_score: float
    missing_skills: List[str]
    strengths: List[str]
    job_description: str

class ScanResultResponse(ScanResultCreate):
    id: int
    user_id: int
    class Config:
        from_attributes = True
