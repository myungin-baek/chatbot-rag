"""세션 관리 API - 세션 조회/삭제."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.session import Session
from app.models.message import Message
from app.auth.security import get_current_user

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionDetail(BaseModel):
    session_id: str
    title: str
    messages: List[dict]
    created_at: str
    updated_at: str


@router.get("/", response_model=List[SessionInfo])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자의 모든 세션 목록 조회."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == current_user.user_id)
        .order_by(Session.updated_at.desc())
        .all()
    )

    result = []
    for session in sessions:
        message_count = (
            db.query(Message)
            .filter(Message.session_id == session.session_id)
            .count()
        )
        result.append(
            SessionInfo(
                session_id=str(session.session_id),
                title=session.title,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                message_count=message_count,
            )
        )

    return result


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """세션 상세 조회 (메시지 포함)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 세션 ID 형식입니다.",
        )

    session = db.query(Session).filter(
        Session.session_id == session_uuid,
        Session.user_id == current_user.user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다.",
        )

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_uuid)
        .order_by(Message.created_at.asc())
        .all()
    )

    messages_data = [
        {
            "message_id": str(m.message_id),
            "role": m.role,
            "content": m.content,
            "sources": m.sources or [],
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]

    return SessionDetail(
        session_id=str(session.session_id),
        title=session.title,
        messages=messages_data,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """세션 삭제 (메시지 포함)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 세션 ID 형식입니다.",
        )

    session = db.query(Session).filter(
        Session.session_id == session_uuid,
        Session.user_id == current_user.user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다.",
        )

    # 메시지 먼저 삭제
    db.query(Message).filter(Message.session_id == session_uuid).delete()
    # 세션 삭제
    db.delete(session)
    db.commit()

    return {"message": "세션이 삭제되었습니다."}
