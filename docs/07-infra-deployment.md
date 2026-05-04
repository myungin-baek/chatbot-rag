# 07. 인프라 구성 및 배포

## 인프라 구성 (소규모)

| 서비스 | 호스트 | 메모리 | 비고 |
|--------|--------|--------|------|
| OpenSearch | 별도 서버 | 8GB+ | k-NN 플러그인 포함 |
| API Gateway (FastAPI) | 별도 서버 | 4GB+ | Uvicorn + Gunicorn |
| Reranker Service | 별도 서버 | 8GB+ | bge-reranker-v2-m3 |
| Redis | 별도 서버 | 2GB+ | 세션 저장소 |
| PostgreSQL | 별도 서버 | 4GB+ | 장기 메모리 |
| LMStudio (LLM API) | 127.0.0.1 | - | OpenAI 호환 API |

## 프로젝트 디렉토리 구조

```
/home/code-project/
├── docs/                          # 아키텍처 문서
│   ├── README.md                  # 문서 개요
│   ├── 01-system-overview.md      # 전체 시스템 아키텍처
│   ├── 02-data-pipeline.md        # 데이터 파이프라인
│   ├── 03-rag-engine.md           # RAG 엔진
│   ├── 04-memory-architecture.md  # 메모리 아키텍처
│   ├── 05-api-design.md           # API 엔드포인트 설계
│   ├── 06-frontend-ui.md          # 프론트엔드 UI
│   └── 07-infra-deployment.md     # 인프라 구성
├── backend/                       # Python FastAPI 백엔드
│   ├── app/
│   │   ├── main.py                # FastAPI 진입점
│   │   ├── api/                   # API 라우터
│   │   ├── rag/                   # RAG 엔진 모듈
│   │   ├── memory/                # 메모리 관리 모듈
│   │   └── documents/             # 문서 처리 모듈
│   ├── requirements.txt           # Python 의존성
│   └── .venv/                     # 가상 환경 (gitignore)
├── frontend/                      # React SPA
│   ├── chatbot-frontend/
│   │   ├── public/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── nginx.conf                 # Nginx 설정 파일
└── infra/                         # 인프라 설정
    ├── docker-compose.yml         # 컨테이너 오케스트레이션
    └── ansible/                   # 서버 프로비저닝 (선택사항)
```

## Docker Compose 구성

```yaml
version: '3.8'

services:
  opensearch:
    image: opensearchproject/opensearch:2.15.0
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
    ports:
      - "9200:9200"
    volumes:
      - opensearch-data:/usr/share/opensearch/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgresql:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: chatbot
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data

  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENSEARCH_URL=http://opensearch:9200
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://admin:secret@postgresql:5432/chatbot
      - OLLAMA_URL=http://127.0.0.1:11434
    depends_on:
      - opensearch
      - redis
      - postgresql

volumes:
  opensearch-data:
  pg-data:
```

## Nginx 설정 (HTTP)

```nginx
server {
    listen 80;
    server_name chatbot.example.com;

    # 정적 파일 서빙 (React SPA)
    root /var/www/chatbot/dist;
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
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-API-Key $http_x_api_key;
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # WebSocket 프록시 (실시간 스트리밍)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
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

## 구현 로드맵 (최종)

| Phase | 내용 | 우선순위 |
|-------|------|----------|
| 1 | OpenSearch, 임베딩, 문서 파싱 (TXT/MD/PDF), RAG 엔진 | 높음 |
| 2 | 로컬 LLM 연동, 채팅 API, 세션 관리 | 높음 |
| 3 | Hybrid Search, Cross-Encoder Ranker, Query Rewriting | 보통 |
| 4 | React SPA + Nginx 프론트엔드 (AWS Console 스타일) | 높음 |
| 5 | API Key 인증, 관리자 대시보드 | 보통 |
| 6 | 이미지 OCR, 다중 모델 지원, 지식 그래프 | 낮음 |

## 배포 체크리스트

- [ ] OpenSearch 설치 및 k-NN 플러그인 활성화
- [ ] Redis 설치 및 설정
- [ ] PostgreSQL 설치 및 데이터베이스 생성
- [ ] Python 가상 환경 생성 (`.venv`)
- [ ] FastAPI 백엔드 빌드 및 실행
- [ ] React SPA 빌드 (`npm run build`)
- [ ] Nginx 설정 적용 및 리로드
- [ ] SSL 인증서 적용 (추후 HTTPS 전환 시)

## Ubuntu 24.04 LTS 설치 커맨드

### 시스템 업데이트 및 기본 패키지 설치
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y curl wget git unzip jq htop net-tools nginx redis-server postgresql python3-pip python3-venv
```

### OpenSearch 설치 (k-NN 플러그인 포함)
```bash
# Java 17 설치 (OpenSearch 의존성)
sudo apt install -y openjdk-17-jdk

# OpenSearch 다운로드 및 설치
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.15.0/opensearch-2.15.0-linux-x64.tar.gz
tar -xzf opensearch-2.15.0-linux-x64.tar.gz
sudo mv opensearch-2.15.0 /usr/local/opensearch

# OpenSearch 설정 수정 (/usr/local/opensearch/config/opensearch.yml)
# discovery.type: single-node 설정

# k-NN 플러그인 설치
/usr/local/opensearch/bin/opensearch-plugin install analysis-icu
```

### PostgreSQL 설정
```bash
# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql -c "CREATE DATABASE chatbot;"
sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD 'secret';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot TO admin;"
```

### Redis 설정
```bash
# Redis 서비스 시작
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Python 가상 환경 생성
```bash
# 프로젝트 디렉토리로 이동
cd /home/code-project/backend

# 가상 환경 생성
python3 -m venv .venv

# 가상 환경 활성화
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### Ollama 설치 (로컬 LLM)
```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# 모델 다운로드 (예: llama3)
ollama pull llama3
```

### Nginx 설정
```bash
# Nginx 설정 파일 복사
sudo cp /home/code-project/frontend/nginx.conf /etc/nginx/sites-available/chatbot

# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Nginx 테스트 및 리로드
sudo nginx -t && sudo systemctl reload nginx
```
