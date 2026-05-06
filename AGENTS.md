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
- The `openai` package is required for LLM client (not installed by default in requirements.txt)
- Cross-Encoder reranker requires `torch` import (was missing, now fixed)
- Database URL uses `asyncpg` driver in Docker (`postgresql+asyncpg://...`), standard `psycopg2` locally
- [`RAGEngine`](backend/app/rag/engine.py:27) is a **singleton** — always use `RAGEngine.get_instance()` (not `__init__`)
- Query rewriter only uses rule-based rewriting (`_rule_based_rewrite`); LLM rewrite not wired up yet
- Admin accounts auto-initialized on startup via [`init_all_users()`](backend/app/auth/initial_data.py) in main.py startup event
- Nginx serves frontend from `../frontend/chatbot-frontend/dist` (not the default Vite build output dir)
