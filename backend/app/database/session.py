"""PostgreSQL 세션 관리."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:secret@localhost:5432/chatbot",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """DB 테이블 자동 생성."""
    # 모든 Base 모델을 import하여 metadata에 등록
    from app.database.base import Base
    from app.models.user import User  # noqa: F401
    from app.models.session import Session  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.document import Document  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """DB 세션 생성자"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
