# 08. Python 가상 환경 설정 가이드 (Ubuntu 24.04 LTS)

## 개요

Python 프로젝트는 호스트 시스템에 직접 영향을 주지 않도록 가상 환경(venv)에서 실행합니다.

## 설치 전 준비

```bash
# Ubuntu 24.04 LTS 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.11+ 및 필수 도구 설치
sudo apt install -y python3.11 python3.11-venv python3-pip git curl wget
```

## 가상 환경 생성

### 1. 프로젝트 디렉토리로 이동

```bash
cd /home/code-project/backend
```

### 2. 가상 환경 생성

```bash
# Python 3.11로 가상 환경 생성
python3.11 -m venv .venv
```

### 3. 가상 환경 활성화

```bash
# 활성화
source .venv/bin/activate

# 확인 (prompt가 변경됨)
which python
# /home/code-project/backend/.venv/bin/python
```

### 4. 의존성 설치

```bash
# pip 업그레이드
pip install --upgrade pip

# 프로젝트 의존성 설치
pip install -r requirements.txt
```

## 주요 Python 의존성 (requirements.txt 예시)

```txt
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# Database
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
redis==5.0.7

# RAG & AI
langchain==0.2.14
langchain-community==0.2.13
sentence-transformers==3.1.0
bge-reranker-v2-m3

# Document Processing
pymupdf==1.24.10  # PyMuPDF
markdown2==2.5.0
pdfplumber==0.11.3
easyocr==1.7.1
Pillow==10.4.0

# Utilities
python-dotenv==1.0.1
pydantic==2.9.1
httpx==0.27.2
```

## 가상 환경 비활성화

```bash
# 비활성화
deactivate
```

## 자동 활성화 설정 (선택사항)

프로젝트 루트에 `.env` 파일을 만들어 자동으로 활성화되도록 할 수 있습니다:

```bash
# .env 파일 생성
echo "source /home/code-project/backend/.venv/bin/activate" >> ~/.bashrc
```

## 가상 환경 관리 명령어

| 명령어 | 설명 |
|--------|------|
| `python3.11 -m venv .venv` | 가상 환경 생성 |
| `source .venv/bin/activate` | 활성화 |
| `deactivate` | 비활성화 |
| `pip list` | 설치된 패키지 목록 |
| `pip freeze > requirements.txt` | 의존성 내보내기 |
| `rm -rf .venv` | 가상 환경 삭제 |

## Docker에서 가상 환경 사용 시

Docker 컨테이너 내부에서도 가상 환경을 사용할 수 있습니다:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
