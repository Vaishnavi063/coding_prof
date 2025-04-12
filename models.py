from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    leetcode_url = Column(String, index=True)
    codechef_url = Column(String, index=True)
    codeforces_url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LeetCodeStats(Base):
    __tablename__ = "leetcode_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    total_problems_solved = Column(Integer)
    easy_solved = Column(Integer)
    medium_solved = Column(Integer)
    hard_solved = Column(Integer)
    contests_participated = Column(Integer)
    contest_rating = Column(Float)
    global_rank = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class CodeChefStats(Base):
    __tablename__ = "codechef_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    total_problems_solved = Column(Integer)
    contest_rating = Column(Float)
    highest_rating = Column(Float)
    global_rank = Column(Integer)
    country_rank = Column(Integer)
    contests_participated = Column(Integer)
    problem_categories = Column(JSON)  # Store problem categories and counts
    recorded_at = Column(DateTime, default=datetime.utcnow)

class CodeForcesStats(Base):
    __tablename__ = "codeforces_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    total_problems_solved = Column(Integer)
    contest_rating = Column(Float)
    highest_rating = Column(Float)
    rank = Column(String)  # e.g., newbie, pupil, expert
    contests_participated = Column(Integer)
    problem_tags = Column(JSON)  # Store problem tags and counts
    recorded_at = Column(DateTime, default=datetime.utcnow)

class LinkedInStats(Base):
    __tablename__ = "linkedin_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    connections = Column(Integer)
    endorsements = Column(Integer)
    skills = Column(String)  # JSON string of skills
    recorded_at = Column(DateTime, default=datetime.utcnow)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./profile_tracker.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 