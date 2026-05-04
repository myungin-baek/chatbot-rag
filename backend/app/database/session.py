"""PostgreSQL 세션 관리."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:secret@localhost:5432/chatbot",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """DB 세션 생성자"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
