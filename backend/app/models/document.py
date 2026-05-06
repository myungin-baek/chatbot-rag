"""Document 모델 - PostgreSQL documents 테이블."""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # txt, md, pdf
    file_size = Column(Integer, nullable=True)
    chunks_count = Column(Integer, nullable=True, default=0)
    status = Column(String(20), nullable=False, default="processing")  # processing, completed, failed
    metadata_json = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Document(document_id={self.document_id}, file_name={self.file_name})>"
