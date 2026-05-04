# 11. Docker Compose 기반 단일 서버 구성

## 개요

기존 아키텍처에서는 각 서비스를 별도 서버로 구성했으나, Docker Compose를 활용해 단일 서버에서 모든 컨테이너를 구동하는 방식으로 변경합니다.

## 서버 요구사항

### 메모리 분석 요약

각 컨테이너 서비스별 실제 메모리 요구사항:

| 서비스 | 최소 RAM | 권장 RAM | 비고 |
|--------|----------|----------|------|
| OpenSearch (k-NN) | 2 GB | 4 GB | JVM 힙 + k-NN 인덱스 |
| Redis | 0.5 GB | 1 GB | 세션/캐시 저장소 |
| PostgreSQL | 1 GB | 2 GB | 장기 메모리 + 사용자 데이터 |
| FastAPI Backend | 0.5 GB | 1 GB | Python + 의존성들 |
| Nginx | 0.1 GB | 0.1 GB | 매우 가벼움 |
| Ollama (Host) | 4 GB | 8 GB+ | LLM 모델에 따라 가변적 |
| **컨테이너 합계** | ~4.6 GB | ~8.2 GB | |
| OS + Docker 데몬 | ~2 GB | ~3 GB | |
| **총 필요 RAM** | **~7 GB** | **~11 GB** | |

### 최종 사양

| 항목 | 최소 사양 | 권장 사양 (현재 구성) |
|------|-----------|---------------------|
| CPU | 4 코어 | **8 코어** |
| RAM | 12 GB | **16 GB 이상** |
| Storage | 100 GB SSD | 200 GB NVMe |
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |

### 메모리 최적화 옵션 (저사양 서버용)

RAM이 부족한 경우 다음 설정으로 조정 가능합니다:

```yaml
# docker-compose.yml - 메모리 제한 설정
services:
  opensearch:
    environment:
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
  
  postgresql:
    deploy:
      resources:
        limits:
          memory: 1G
  
  redis:
    command: ["redis-server", "--maxmemory", "256mb"]
```

## 서비스 구성

```mermaid
graph TB
    subgraph "Single Server (Ubuntu 24.04)"
        Nginx[Nginx<br/>Port: 80]
        
        subgraph "Docker Containers"
            API[FastAPI Backend<br/>Port: 8000]
            Redis[(Redis Cache)]
            PG[(PostgreSQL DB)]
            OS[(OpenSearch k-NN)]
        end
        
        Ollama[Ollama (Host)<br/>Port: 11434]
    end
    
    User[사용자] -->|HTTP/WS| Nginx
    Nginx --> API
    API --> Redis
    API --> PG
    API --> OS
    API -->|host.docker.internal| Ollama
```

## 프로젝트 디렉토리 구조 (최종)

```
/home/code-project/
├── docs/                          # 아키텍처 문서
│   ├── README.md                  # 문서 개요
│   ├── 00-session-summary.md      # 세션 요약
│   ├── 01-system-overview.md      # 전체 시스템 아키텍처
│   ├── 02-data-pipeline.md        # 데이터 파이프라인
│   ├── 03-rag-engine.md           # RAG 엔진
│   ├── 04-memory-architecture.md  # 메모리 아키텍처
│   ├── 05-api-design.md           # API 엔드포인트 설계
│   ├── 06-frontend-ui.md          # 프론트엔드 UI
│   ├── 07-infra-deployment.md     # 인프라 구성 (기존)
│   ├── 08-python-virtualenv.md    # Python 가상 환경 가이드
│   ├── 09-authentication.md       # 인증 및 권한 관리
│   ├── 10-ci-cd-github-actions.md # GitHub Actions CI/CD
│   └── 11-docker-compose-single-server.md # Docker Compose 구성 (이 파일)
├── backend/                       # Python FastAPI 백엔드
│   ├── app/
│   │   ├── main.py                # FastAPI 진입점
│   │   ├── api/                   # API 라우터
│   │   ├── rag/                   # RAG 엔진 모듈
│   │   ├── memory/                # 메모리 관리 모듈
│   │   ├── documents/             # 문서 처리 모듈
│   │   └── middleware/            # 미들웨어 (Request ID 등)
│   ├── tests/                     # 테스트 파일
│   ├── requirements.txt           # Python 의존성
│   └── Dockerfile                 # 백엔드 Docker 이미지 빌드
├── frontend/                      # React SPA
│   ├── chatbot-frontend/
│   │   ├── public/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── nginx.conf                 # Nginx 설정 파일
├── infra/                         # 인프라 설정
│   ├── docker-compose.yml         # 컨테이너 오케스트레이션 (메인)
│   └── .env                       # 환경변수 파일
└── .github/workflows/             # GitHub Actions 워크플로우
    └── deploy.yml                 # CI/CD 파이프라인
```

## Docker Compose 구성 (`infra/docker-compose.yml`)

```yaml
version: '3.8'

services:
  # ─── OpenSearch (Vector DB) ──────────────
  opensearch:
    image: opensearchproject/opensearch:2.15.0
    container_name: chatbot-opensearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    networks:
      - chatbot-net
    restart: unless-stopped

  # ─── Redis (Session/Cache) ──────────────
  redis:
    image: redis:7-alpine
    container_name: chatbot-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - chatbot-net
    restart: unless-stopped

  # ─── PostgreSQL (Long-term Memory + Users) ──
  postgresql:
    image: postgres:15-alpine
    container_name: chatbot-postgresql
    environment:
      POSTGRES_DB: chatbot
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data
    networks:
      - chatbot-net
    restart: unless-stopped

  # ─── FastAPI Backend ──────────────────────
  api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: chatbot-api
    ports:
      - "8000:8000"
    environment:
      - OPENSEARCH_URL=http://opensearch:9200
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql+asyncpg://admin:secret@postgresql:5432/chatbot
      - OLLAMA_URL=http://host.docker.internal:11434
    depends_on:
      - opensearch
      - redis
      - postgresql
    networks:
      - chatbot-net
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

  # ─── Nginx (Frontend + Reverse Proxy) ─────
  nginx:
    image: nginx:alpine
    container_name: chatbot-nginx
    ports:
      - "80:80"
    volumes:
      - ../frontend/chatbot-frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - api
    networks:
      - chatbot-net
    restart: unless-stopped

volumes:
  opensearch-data:
  redis-data:
  pg-data:

networks:
  chatbot-net:
    driver: bridge
```

## Nginx 설정 (`infra/nginx.conf`)

```nginx
server {
    listen 80;
    server_name chatbot.example.com;

    # 정적 파일 서빙 (React SPA)
    root /usr/share/nginx/html;
    index index.html;

    # React Router 지원 (SPA 라우팅)
    location / {
        try_files $uri $uri/ /index.html;
        
        # 캐시 제어
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 프록시 (REST)
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # WebSocket 프록시 (실시간 스트리밍)
    location /ws/ {
        proxy_pass http://api:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # WebSocket 타임아웃 (긴 연결 유지)
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 보안 헤더
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

## 환경변수 파일 (`infra/.env`)

```bash
# OpenSearch
OPENSEARCH_URL=http://opensearch:9200

# Redis
REDIS_URL=redis://redis:6379

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://admin:secret@postgresql:5432/chatbot

# Ollama (호스트 머신)
OLLAMA_URL=http://host.docker.internal:11434

# JWT Secret
JWT_SECRET=your-secret-key-change-in-production

# Admin Account
ADMIN_USERNAME=admin
ADMIN_PASSWORD=sjaksahffk.
```

## 서버 설정 커맨드

### Ubuntu 24.04 LTS 초기 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y curl wget git unzip jq htop net-tools docker.io docker-compose-plugin

# Docker 그룹에 사용자 추가 (선택사항)
sudo usermod -aG docker $USER

# Docker 서비스 시작
sudo systemctl enable --now docker
```

### Ollama 설치 (호스트 머신)

```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# 모델 다운로드
ollama pull llama3
```

## 배포 명령어

```bash
# 프로젝트 디렉토리로 이동
cd /home/code-project/infra

# 컨테이너 빌드 및 시작
docker compose up -d --build

# 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f api

# 서비스 재시작
docker compose restart

# 서비스 중지
docker compose down
```

## 데이터 백업 전략

```bash
# OpenSearch 백업
curl -X PUT "localhost:9200/_snapshot/my_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backup/opensearch"
  }
}'

# PostgreSQL 백업
docker exec chatbot-postgresql pg_dump -U admin chatbot > backup_$(date +%Y%m%d).sql

# Redis 백업 (RDB)
docker cp chatbot-redis:/data/dump.rdb ./redis-backup.rdb
```

---

*문서 생성일: 2026-05-04*
