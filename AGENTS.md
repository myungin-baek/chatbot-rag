# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

RAG-based AI chatbot system. Backend: FastAPI + Python 3.10+. Frontend: React 19 + TypeScript + Vite. Infra: Docker Compose (OpenSearch, Redis, PostgreSQL, Nginx).

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
cd backend && python -m pytest                          # Run all tests
cd backend && python -m pytest tests/test_rrf.py        # Run single test file
cd backend && python -m pytest -k "test_name"           # Run specific test
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run build

# Docker (all services)
cd infra && docker-compose up -d
```

## Key Patterns

- RAG config values in [`backend/app/rag/config.py`](backend/app/rag/config.py:1) — env vars use `RAG_` prefix via pydantic-settings (`RAG_OPENSEARCH_HOST`, etc.)
- All API routes under [`backend/app/api/`](backend/app/api/) with auth dependency; prefix is `/api/v1/`
- JWT authentication required for all endpoints except `/health` and login
- OpenSearch index name: `chatbot_documents` (defined in [`opensearch_config.py`](backend/app/rag/opensearch_config.py))
- LLM: LMStudio at `http://127.0.0.1:1234/v1` (OpenAI-compatible)

## Gotchas

- `.env` file must be in `infra/` directory (Docker uses `infra/.env`)
- OpenSearch 2.15+ requires `OPENSEARCH_INITIAL_ADMIN_PASSWORD` env var — set to a strong password with uppercase, lowercase, digit, special char
- Database URL uses standard `postgresql://` driver in Docker (not `asyncpg`) — [`session.py`](backend/app/database/session.py:12) uses sync SQLAlchemy
- [`RAGEngine`](backend/app/rag/engine.py:27) is a **singleton** — always use `RAGEngine.get_instance()` (not `__init__`)
- Query rewriter only uses rule-based rewriting (`_rule_based_rewrite`); LLM rewrite not wired up yet
- Admin accounts auto-initialized on startup via [`init_all_users()`](backend/app/auth/initial_data.py) in main.py startup event
- Nginx serves frontend from `../frontend/dist` (Vite default build output, NOT `chatbot-frontend/dist`)
- [`hybrid_search.py`](backend/app/rag/search/hybrid_search.py:28) has a **temporary implementation** — query vector is `[0.0] * 768`; actual embedding-based search not wired up yet
- [`SentenceTransformerEmbeddings.get_instance()`](backend/app/rag/embeddings/sentence_transformers.py:27) accepts `model_name` parameter (unlike RAGEngine which doesn't)
- Middleware order in [`main.py`](backend/app/main.py:14): RequestIDMiddleware must be added before LoggingMiddleware
- Frontend stores JWT token in localStorage key `'access_token'` ([`api.ts`](frontend/src/services/api.ts:9))
- Supported file types for ingestion: `txt`, `md`, `pdf` only (see [`parser/factory.py`](backend/app/rag/parser/factory.py:11))
- Password hashing uses direct `bcrypt` library (not passlib) — see [`security.py`](backend/app/auth/security.py)
- [`get_current_user()`](backend/app/auth/security.py:61) returns a **User model instance** from DB, not a dict
- Session `created_at` and `updated_at` have default values in [`session.py`](backend/app/models/session.py:19-20)
