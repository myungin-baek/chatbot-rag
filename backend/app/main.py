"""FastAPI 진입점."""

import logging
from fastapi import FastAPI, Request, Response
from app.middleware.request_id import RequestIDMiddleware, LoggingMiddleware
from app.database.session import engine, SessionLocal
from app.auth.initial_data import init_all_users
from app.api import auth, chat, sessions, documents

logger = logging.getLogger(__name__)

app = FastAPI(title="Chatbot RAG API")

# 미들웨어 등록 (순서 중요 - 위에서 아래로 실행)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
async def startup():
    """앱 시작 시 DB 테이블 생성, 관리자 계정 초기화 및 OpenSearch 인덱스 생성"""
    from app.database.base import Base
    
    # 0. DB 테이블 자동 생성
    Base.metadata.create_all(bind=engine)

    # 1. 관리자 계정 초기화
    db = SessionLocal()
    try:
        init_all_users(db)
    finally:
        db.close()

    # 2. OpenSearch 인덱스 자동 생성
    try:
        from app.rag.engine import RAGEngine
        rag_engine = RAGEngine.get_instance()
        index_name = "chatbot_documents"
        
        if not rag_engine.os_client.client.indices.exists(index=index_name):
            rag_engine.os_client.create_index(
                index_name=index_name,
                mapping={
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "file_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "file_type": {"type": "keyword"},
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 768,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "faiss",
                                "parameters": {"ef_construction": 128, "m": 16},
                            },
                        },
                        "metadata": {"type": "object"},
                        "chunk_index": {"type": "integer"},
                        "token_count": {"type": "integer"},
                    }
                },
            )
            logger.info(f"Created OpenSearch index: {index_name}")
        else:
            logger.info(f"OpenSearch index already exists: {index_name}")
    except Exception as e:
        logger.warning(f"Failed to create OpenSearch index (will be created on first ingest): {e}")


# 라우터 등록
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(documents.router)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "ok"}
