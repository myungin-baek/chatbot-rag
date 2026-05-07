"""채팅 API - RAG 기반 채팅 엔드포인트."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
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


# ===== WebSocket 스트리밍 =====

@router.websocket("/ws/stream")
async def chat_stream(websocket: WebSocket):
    """WebSocket 스트리밍 채팅 엔드포인트.
    
    메시지 형식 (클라이언트 → 서버):
    - {"type": "connect", "token": "..."} : 연결 인증
    - {"type": "message", "content": "...", "session_id": "..."} : 메시지 전송
    
    응답 형식 (서버 → 클라이언트):
    - {"type": "content", "data": "..."} : 콘텐츠 토큰
    - {"type": "sources", "data": [...]} : 출처 정보
    - {"type": "done", "data": null} : 스트리밍 완료
    - {"type": "error", "data": "..."} : 오류
    """
    await websocket.accept()
    
    token = None
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "connect":
                # 인증 토큰 검증
                token = data.get("token", "")
                if not token:
                    await websocket.send_json({"type": "error", "data": "인증 토큰이 필요합니다."})
                    break
                
                # JWT 검증 (간단하게)
                from app.auth.security import decode_token
                try:
                    decoded = decode_token(token)
                    user_id = decoded.get("sub")
                    if not user_id:
                        await websocket.send_json({"type": "error", "data": "인증에 실패했습니다."})
                        break
                except Exception as e:
                    await websocket.send_json({"type": "error", "data": f"인증 오류: {str(e)}"})
                    break
                
            elif data.get("type") == "message":
                message_content = data.get("content", "")
                session_id = data.get("session_id")
                
                if not message_content.strip():
                    continue
                
                # 세션 확인 또는 생성 (DB 연결)
                db = SessionLocal()
                try:
                    user = decode_user_from_token(token, db)
                    
                    # 1. 세션 확인 또는 생성
                    session_obj = None
                    if session_id:
                        try:
                            session_uuid = uuid.UUID(session_id)
                            session_obj = db.query(Session).filter(
                                Session.session_id == session_uuid,
                                Session.user_id == user.user_id,
                            ).first()
                        except ValueError:
                            pass
                    
                    if not session_obj:
                        session_obj = Session(
                            user_id=user.user_id,
                            title=message_content[:50] + ("..." if len(message_content) > 50 else ""),
                        )
                        db.add(session_obj)
                        db.commit()
                        db.refresh(session_obj)
                    
                    # 2. 사용자 메시지 저장
                    user_message = Message(
                        session_id=session_obj.session_id,
                        role="user",
                        content=message_content,
                    )
                    db.add(user_message)
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Session setup error: {e}")
                    await websocket.send_json({"type": "error", "data": f"세션 설정 오류: {str(e)}"})
                    continue
                
                # 3. RAG 스트리밍 응답
                try:
                    rag_engine = RAGEngine.get_instance()
                    
                    async for event_type, data in rag_engine.generate_response_stream(message_content):
                        await websocket.send_json({
                            "type": event_type,
                            "data": data,
                            "session_id": str(session_obj.session_id),
                        })
                    
                    # 4. 어시스턴트 응답 저장 (스트리밍 완료 후)
                    try:
                        assistant_message = Message(
                            session_id=session_obj.session_id,
                            role="assistant",
                            content="",  # 스트리밍 중에는 내용 알 수 없음
                        )
                        db.add(assistant_message)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Failed to save assistant message: {e}")
                        
                except Exception as e:
                    logger.error(f"RAG streaming error: {e}")
                    await websocket.send_json({"type": "error", "data": f"RAG 오류: {str(e)}"})
                
                finally:
                    db.close()
                    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
        finally:
            await websocket.close()


def decode_user_from_token(token: str, db) -> User:
    """JWT 토큰에서 사용자 정보 추출."""
    from app.auth.security import decode_token
    decoded = decode_token(token)
    user_id = decoded.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="인증에 실패했습니다.")
    
    user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    
    return user
