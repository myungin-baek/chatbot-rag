# RAG 기반 AI 채팅봇 시스템 - 세션 요약 및 이전 컨텍스트

## 프로젝트 개요

RAG (Retrieval-Augmented Generation) 기반 AI 채팅봇 시스템 아키텍처 설계 완료.

- **LLM**: 로컬 Ollama (`http://127.0.0.1:11434`)
- **Vector DB**: OpenSearch 2.x+ (k-NN plugin)
- **Frontend**: React SPA + Nginx (HTTP, chatbot.example.com)
- **Backend**: FastAPI (Python 가상 환경)
- **OS**: Ubuntu 24.04 LTS

## 완료된 작업 목록

### 1. 아키텍처 설계 (Phase 1)
- 단일 파일에서 기능별 하위 디렉토리 분리 (`docs/` 폴더, 총 10개 md 파일)
- 전체 시스템 구성도 및 데이터 흐름 다이어그램 작성
- 기술 스택 정의 (React, Nginx, FastAPI, OpenSearch, Ollama 등)

### 2. 데이터 파이프라인 설계
- 지원 형식: TXT, MD, PDF (텍스트 + 이미지 OCR)
- 업로드 API 엔드포인트 설계 (`POST /api/v1/documents/upload`)
- 문서 파싱 로직 (PyMuPDF, markdown2, EasyOCR)
- 청킹 전략: 500 토큰 기준 + 50 토큰 오버랩

### 3. RAG 엔진 설계
- Multi-Vector Search + RRF (Reciprocal Rank Fusion)
- Cross-Encoder Ranker (BAAI/bge-reranker-v2-m3, 2-stage retrieval)
- Hybrid Search (Dense Vector + BM25)
- Query Expansion & Rewriting

### 4. 메모리 아키텍처 설계
- 단기 기억 (STM): Redis 기반, 최근 20개 메시지, 30분 TTL
- 장기 기억 (LTM): PostgreSQL 기반, 사용자 프로필 + 세션 요약본
- 작업 기억 (WM): 현재 응답을 위한 컨텍스트 윈도우

### 5. API 엔드포인트 설계
- 인증: API Key 검증 미들웨어
- 채팅: POST /api/v1/chat (스트리밍 응답)
- 문서 관리: 업로드, 조회, 삭제
- 세션 관리: 조회, 삭제

### 6. 프론트엔드 UI 설계 (AWS Console 스타일)
- React SPA + Vite 빌드
- Nginx Reverse Proxy (HTTP, WebSocket 프록시)
- AWS Console 스타일 디자인 시스템 (색상 팔레트, 타이포그래피 정의)
- 우측 하단 플로팅 채팅 아이콘 + 확장 스타일

### 7. 인프라 구성 및 배포 가이드
- Docker Compose 구성 (OpenSearch, Redis, PostgreSQL, FastAPI)
- Nginx 설정 파일 (HTTP 기반)
- Ubuntu 24.04 LTS 설치 커맨드 (전체 패키지 설치부터 서비스 설정까지)
- Python 가상 환경 생성 가이드

### 8. 인증 및 권한 관리
- 사용자 레벨: 일반 사용자 / 관리자
- 로그인 API (POST /api/v1/auth/login)
- JWT 토큰 기반 인증 (30분 만료)
- 역할 기반 접근 제어 (RBAC)
- 관리자 계정 초기 설정 (ID: admin, PW: sjaksahffk.)

### 9. Docker Compose 기반 단일 서버 구성 (2026-05-04 추가)
- OpenSearch, Redis, PostgreSQL, FastAPI, Nginx 통합 컨테이너
- 볼륨 마운트: /opt/chatbot/data 하위 통일
- Ollama는 호스트 머신에 설치 후 host.docker.internal로 연결

### 10. GitHub Actions CI/CD 파이프라인 (2026-05-04 추가)
- main 브랜치 push 시 자동 테스트 → 빌드 → 배포
- SSH를 통한 서버 배포 (appleboy/ssh-action)
- Secrets 관리: DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY

### 11. FastAPI Request ID 추적 미들웨어 (2026-05-04 추가)
- 각 요청에 고유 UUID 할당 (X-Request-ID)
- contextvars를 사용한 비동기 컨텍스트 관리
- 로깅 시스템 통합 (콘솔 + 파일 로그)

## 최종 프로젝트 구조

```
/home/code-project/
├── docs/                          # 아키텍처 문서 (10개 파일)
│   ├── README.md                  # 문서 개요 및 로드맵
│   ├── 00-session-summary.md      # 세션 요약 (이 파일)
│   ├── 01-system-overview.md      # 전체 시스템 아키텍처
│   ├── 02-data-pipeline.md        # 데이터 파이프라인
│   ├── 03-rag-engine.md           # RAG 엔진
│   ├── 04-memory-architecture.md  # 메모리 아키텍처
│   ├── 05-api-design.md           # API 엔드포인트 설계
│   ├── 06-frontend-ui.md          # 프론트엔드 UI (AWS Console 스타일)
│   ├── 07-infra-deployment.md     # 인프라 구성 및 Ubuntu 24.04 LTS 커맨드
│   ├── 08-python-virtualenv.md    # Python 가상 환경 가이드
│   └── 09-authentication.md       # 인증 및 권한 관리
├── backend/                       # Python FastAPI 백엔드 (미구현)
├── frontend/                      # React SPA (미구현)
└── infra/                         # 인프라 설정 (미구현)
```

## 구현 로드맵 (최종)

| Phase | 내용 | 우선순위 |
|-------|------|----------|
| 1 | OpenSearch, 임베딩, 문서 파싱 (TXT/MD/PDF), RAG 엔진 | 높음 |
| 2 | 로컬 LLM 연동, 채팅 API, 세션 관리 | 높음 |
| 3 | Hybrid Search, Cross-Encoder Ranker, Query Rewriting | 보통 |
| 4 | React SPA + Nginx 프론트엔드 (AWS Console 스타일) | 높음 |
| 5 | API Key 인증, 관리자 대시보드 | 보통 |
| 6 | 이미지 OCR, 다중 모델 지원, 지식 그래프 | 낮음 |

## 최신 업데이트 (2026-05-04)

### 완료된 작업
1. **Docker Compose 기반 단일 서버 구성** - 모든 서비스를 Docker 컨테이너로 통합
2. **GitHub Actions CI/CD 파이프라인** - 자동 빌드 → 테스트 → 배포
3. **관리자 계정 초기화 스크립트** - admin / sjaksahffk.
4. **FastAPI Request ID 추적 미들웨어** - 요청별 고유 UUID 할당 및 로깅

### 생성된 문서
- `docs/10-ci-cd-github-actions.md` - GitHub Actions CI/CD 파이프라인
- `docs/11-docker-compose-single-server.md` - Docker Compose 단일 서버 구성
- `docs/12-admin-account-setup.md` - 관리자 계정 초기화 및 설정
- `docs/13-request-id-tracing.md` - FastAPI Request ID 추적 미들웨어

## 적합도 검토 결과

현재 설계된 아키텍처는 **독립적인 프론트엔드 + 채팅봇 시스템으로서의 역할**을 충분히 수행할 수 있습니다.

### ✅ 커버되는 기능
- RAG 기반 검색 (OpenSearch k-NN + Cross-Encoder)
- 문서 업로드 및 벡터화 (TXT/MD/PDF, OCR 포함)
- 로컬 LLM 연동 (Ollama)
- 메모리 아키텍처 (단기/장기 기억)
- API 엔드포인트 설계 (REST + WebSocket)
- React SPA 프론트엔드 (AWS Console 스타일, 플로팅 채팅 아이콘)
- 관리자 로그인 및 권한 관리 (JWT 기반, 일반/관리자 역할 구분)
- Python 가상 환경 가이드 (Ubuntu 24.04 LTS 호환)

### ⚠️ 보완 필요 항목
1. 실제 코드 구현 (FastAPI 백엔드 + React 프론트엔드)
2. Docker Compose 완성
3. SSL 인증서 (추후 HTTPS 전환 시)
4. 모니터링 및 로깅 시스템
5. 백업 전략

## 다음 세션에서 진행할 작업 제안

1. **Phase 1 구현**: OpenSearch 설치, 임베딩 모델 배포, 문서 파싱 모듈 개발
2. **Phase 2 구현**: FastAPI 백엔드 개발 (채팅 API, 세션 관리)
3. **Phase 4 구현**: React SPA 프론트엔드 개발 (AWS Console 스타일 UI)

---

*최종 업데이트: 2026-05-04 (CI/CD, Docker Compose, Request ID 미들웨어 추가)*
*아키텍처 설계 완료 상태*
