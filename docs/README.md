# RAG 기반 AI 채팅봇 시스템 - 아키텍처 문서

## 프로젝트 개요

RAG (Retrieval-Augmented Generation) 기반 AI 채팅봇 시스템입니다.
로컬 LLM(LMStudio), OpenSearch, Nginx + React SPA로 구성됩니다.

- **LLM**: LMStudio (OpenAI 호환, `http://127.0.0.1:1234/v1`)
- **Vector DB**: OpenSearch 2.x+ (k-NN plugin)
- **Frontend**: React SPA + Nginx (HTTP, chatbot.example.com)
- **Backend**: FastAPI (Python 가상 환경)
- **OS**: Ubuntu 24.04 LTS

## 문서 구조

| 파일 | 설명 |
|------|------|
| [README.md](./README.md) | 문서 개요 |
| [01-system-overview.md](./01-system-overview.md) | 전체 시스템 아키텍처 및 구성 요소 |
| [02-data-pipeline.md](./02-data-pipeline.md) | 문서 업로드, 파싱, 청킹, 벡터화 파이프라인 |
| [03-rag-engine.md](./03-rag-engine.md) | RAG 엔진 (검색, 랭킹, 임베딩) |
| [04-memory-architecture.md](./04-memory-architecture.md) | 단기/장기 기억 메모리 구조 |
| [05-api-design.md](./05-api-design.md) | API 엔드포인트 및 파라미터 설계 |
| [06-frontend-ui.md](./06-frontend-ui.md) | React SPA + Nginx 프론트엔드 UI (AWS Console 스타일) |
| [07-infra-deployment.md](./07-infra-deployment.md) | 인프라 구성, 배포 가이드, Ubuntu 24.04 LTS 커맨드 |
| [08-python-virtualenv.md](./08-python-virtualenv.md) | Python 가상 환경 설정 가이드 |
| [09-authentication.md](./09-authentication.md) | 인증 및 권한 관리 (로그인, JWT, RBAC) |
| [10-ci-cd-github-actions.md](./10-ci-cd-github-actions.md) | GitHub Actions CI/CD 파이프라인 구성 |
| [11-docker-compose-single-server.md](./11-docker-compose-single-server.md) | Docker Compose 기반 단일 서버 구성 |
| [12-admin-account-setup.md](./12-admin-account-setup.md) | 관리자 계정 초기화 및 설정 |
| [13-request-id-tracing.md](./13-request-id-tracing.md) | FastAPI Request ID 추적 미들웨어 |
| [14-implementation-status.md](./14-implementation-status.md) | 구현 현황 및 다음 작업 (2026-05-06) |

## 구현 로드맵

| Phase | 내용 | 우선순위 | 상태 |
|-------|------|----------|------|
| 1 | OpenSearch, 임베딩, 문서 파싱 (TXT/MD/PDF), RAG 엔진 | 높음 | ✅ 완료 |
| 2 | 로컬 LLM 연동, 채팅 API, 세션 관리 | 높음 | ⚠️ 부분 (API 완료, RAG 연동 TODO) |
| 3 | Hybrid Search, Cross-Encoder Ranker, Query Rewriting | 보통 | ✅ 완료 |
| 4 | React SPA + Nginx 프론트엔드 (AWS Console 스타일) | 높음 | ⚠️ 부분 (로그인 UI 완료) |
| 5 | JWT 인증, 관리자 계정 | 보통 | ✅ 완료 |
| 6 | 이미지 OCR, 다중 모델 지원, 지식 그래프 | 낮음 | ⬜ 미着手 |

## 최신 업데이트 (2026-05-06)

- **Phase 2: FastAPI 백엔드 API 전량 구현**
  - 채팅 API (`POST /api/v1/chat/`)
  - 세션 관리 API (`GET/DELETE /api/v1/sessions/`)
  - 문서 관리 API (`GET/POST/DELETE /api/v1/documents/`)
  - SQLAlchemy 모델 (User, Session, Message, Document)
  - DB 테이블 자동 생성 (`init_db()`)
- **Phase 4: 프론트엔드 기반**
  - 로그인 UI (AWS Console 스타일)
  - API 서비스 모듈 (토큰 관리, 모든 API 호출)
- **구현 현황 문서 추가** - `docs/14-implementation-status.md`
