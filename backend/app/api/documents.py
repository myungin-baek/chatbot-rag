"""문서 관리 API - 업로드/조회/삭제."""

import logging
import os
import uuid
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.document import Document
from app.auth.security import get_current_user
from app.rag.engine import RAGEngine

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

logger = logging.getLogger(__name__)

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class DocumentInfo(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    chunks_count: Optional[int] = None
    status: str
    created_at: str


class UploadResponse(BaseModel):
    document_id: str
    file_name: str
    status: str
    chunks_count: Optional[int] = None
    message: str


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자의 모든 문서 목록 조회."""
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.user_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        DocumentInfo(
            document_id=str(doc.document_id),
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            chunks_count=doc.chunks_count,
            status=doc.status,
            created_at=doc.created_at.isoformat(),
        )
        for doc in documents
    ]


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """문서 업로드 (TXT, MD, PDF)."""
    # 1. 파일 확장자 검증
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 2. 파일 크기 검증
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # 3. 임시 파일로 저장
    file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_content)
            file_path = tmp.name

        # 4. RAG 엔진으로 문서 처리
        rag_engine = RAGEngine.get_instance()
        result = rag_engine.ingest_document(file_path)

        # 5. DB에 문서 정보 저장
        doc = Document(
            user_id=current_user.user_id,
            file_name=file.filename,
            file_type=ext.lstrip("."),
            file_size=len(file_content),
            chunks_count=result.get("chunks_count", 0),
            status="completed",
            metadata_json={
                "title": title or "",
                "category": category or "",
                "tags": tags.split(",") if tags else [],
            },
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        return UploadResponse(
            document_id=str(doc.document_id),
            file_name=doc.file_name,
            status=doc.status,
            chunks_count=doc.chunks_count,
            message="문서가 성공적으로 업로드되었습니다.",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 처리 중 오류가 발생했습니다: {str(e)}",
        )
    finally:
        # 임시 파일 정리
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """문서 삭제 (OpenSearch 벡터도 함께 삭제)."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 문서 ID 형식입니다.",
        )

    doc = db.query(Document).filter(
        Document.document_id == doc_uuid,
        Document.user_id == current_user.user_id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다.",
        )

    # OpenSearch에서 해당 문서의 벡터 삭제
    try:
        rag_engine = RAGEngine.get_instance()
        rag_engine.delete_document_vectors(str(doc_uuid))
    except Exception as e:
        logger.warning(f"Failed to delete vectors from OpenSearch: {e}")

    db.delete(doc)
    db.commit()

    return {"message": "문서가 삭제되었습니다."}
