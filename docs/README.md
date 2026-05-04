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

## 구현 로드맵

| Phase | 내용 | 우선순위 |
|-------|------|----------|
| 1 | OpenSearch, 임베딩, 문서 파싱 (TXT/MD/PDF), RAG 엔진 | 높음 |
| 2 | 로컬 LLM 연동, 채팅 API, 세션 관리 | 높음 |
| 3 | Hybrid Search, Cross-Encoder Ranker, Query Rewriting | 보통 |
| 4 | React SPA + Nginx 프론트엔드 (AWS Console 스타일) | 높음 |
| 5 | API Key 인증, 관리자 대시보드 | 보통 |
| 6 | 이미지 OCR, 다중 모델 지원, 지식 그래프 | 낮음 |

## 최신 업데이트 (2026-05-04)

- **Docker Compose 기반 단일 서버 구성**: 모든 서비스를 Docker 컨테이너로 통합
- **GitHub Actions CI/CD 파이프라인**: 자동 빌드 → 테스트 → 배포
- **관리자 계정 초기화 스크립트**: `admin` / `sjaksahffk.`
- **FastAPI Request ID 추적 미들웨어**: 요청별 고유 UUID 할당 및 로깅
