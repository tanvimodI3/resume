from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScanResult(Base):
    __tablename__ = "candidate_details"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    experience = Column(String)
    profiles = Column(JSON)
    skills = Column(JSON)
    match_score = Column(Float)
    missing_skills = Column(JSON)
    strengths = Column(JSON)
    job_description = Column(Text)
    github_url = Column(String, nullable=True)
    leetcode_url = Column(String, nullable=True)
