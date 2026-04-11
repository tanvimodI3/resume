from sqlalchemy import Column, Integer, String, Float, Text, JSON
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class ScanResult(Base):
    __tablename__ = "scan_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    filename = Column(String)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    experience = Column(String)
    profiles = Column(JSON)
    match_score = Column(Float)
    missing_skills = Column(JSON)
    strengths = Column(JSON)
    job_description = Column(Text)
