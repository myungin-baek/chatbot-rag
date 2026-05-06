"""FastAPI 진입점."""

from fastapi import FastAPI, Request, Response
from app.middleware.request_id import RequestIDMiddleware, LoggingMiddleware
from app.database.session import engine, SessionLocal
from app.auth.initial_data import init_all_users
from app.api import auth, chat, sessions, documents

app = FastAPI(title="Chatbot RAG API")

# 미들웨어 등록 (순서 중요 - 위에서 아래로 실행)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
async def startup():
    """앱 시작 시 관리자 계정 초기화"""
    db = SessionLocal()
    try:
        init_all_users(db)
    finally:
        db.close()


# 라우터 등록
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(documents.router)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "ok"}
