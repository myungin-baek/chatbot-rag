"""채팅 API - RAG 기반 채팅 엔드포인트."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.session import Session
from app.models.message import Message
from app.auth.security import get_current_user
from app.rag.engine import RAGEngine

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    rag_config: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    content: str
    sources: list = []
    timestamp: str


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """채팅 메시지 전송 및 RAG 기반 응답 생성."""
    # 1. 세션 확인 또는 생성
    session = None
    if request.session_id:
        try:
            session_uuid = uuid.UUID(request.session_id)
            session = db.query(Session).filter(
                Session.session_id == session_uuid,
                Session.user_id == current_user.user_id,
            ).first()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="잘못된 세션 ID 형식입니다.",
            )

    if not session:
        # 새 세션 생성
        session = Session(
            user_id=current_user.user_id,
            title=request.message[:50] + ("..." if len(request.message) > 50 else ""),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. 사용자 메시지 저장
    user_message = Message(
        session_id=session.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # 3. RAG 엔진으로 응답 생성
    try:
        rag_engine = RAGEngine.get_instance()
        rag_response = rag_engine.generate_response(request.message)
    except Exception as e:
        logger.error(f"RAG engine error: {e}")
        rag_response = {
            "content": f"[오류] RAG 엔진 처리 중 오류가 발생했습니다: {str(e)}",
            "sources": [],
        }

    # 4. 어시스턴트 응답 저장
    assistant_message = Message(
        session_id=session.session_id,
        role="assistant",
        content=rag_response["content"],
        sources=rag_response.get("sources", []),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        session_id=str(session.session_id),
        message_id=str(assistant_message.message_id),
        content=rag_response["content"],
        sources=rag_response.get("sources", []),
        timestamp=assistant_message.created_at.isoformat(),
    )
