# LLM 연동 및 E2E 테스트 설계서

## 1. LMStudio 서버 설정

### 1.1 LMStudio 실행 방법

```bash
# LMStudio 다운로드 (Linux)
wget https://github.com/lmstudio-ai/lmstudio/releases/download/v0.3.10/lmstudio-linux-x64.tar.gz
tar -xzf lmstudio-linux-x64.tar.gz
cd lmstudio-linux-x64
./lmstudio

# 또는 CLI 모드 (headless 서버용)
pip install lmstudio-cli
lmserve --model <model_name> --host 127.0.0.1 --port 1234
```

### 1.2 추천 모델

| 모델 | 용도 | 크기 | 메모리 요구량 |
|------|------|------|--------------|
| `llama-3.1-8b-instruct` | 일반 채팅 | ~5GB VRAM | 8GB+ RAM |
| `qwen2.5-7b-instruct` | 다국어 지원 | ~5GB VRAM | 8GB+ RAM |
| `mistral-7b-instruct` | 경량 모델 | ~4GB VRAM | 6GB+ RAM |

### 1.3 API 엔드포인트 검증

```bash
# LMStudio 서버 상태 확인
curl http://127.0.0.1:1234/v1/models

# 간단한 테스트 요청
curl -X POST http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lmstudio-community/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "안녕하세요"}],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

## 2. RAG 파이프라인 E2E 테스트

### 2.1 문서 인제스트 테스트 시나리오

#### 2.1.1 PDF 파일 업로드
- **테스트 파일**: `test_document.pdf` (50~100 페이지)
- **검증 항목**:
  - [ ] 파일 확장자 `.pdf` 인식
  - [ ] PyPDF2/Pymupdf 파싱 성공
  - [ ] 청크 생성 (chunk_size=500, overlap=50)
  - [ ] 임베딩 벡터 생성 (768차원)
  - [ ] OpenSearch `chatbot_documents` 인덱스 저장

```bash
# PDF 업로드 API 호출
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@test_document.pdf" \
  -F "title=테스트 문서" \
  -F "category=test"
```

#### 2.1.2 TXT 파일 업로드
- **테스트 파일**: `test_document.txt` (한글 포함)
- **검증 항목**: UTF-8 인코딩, 한글 텍스트 파싱

#### 2.1.3 Markdown 파일 업로드
- **테스트 파일**: `test_document.md`
- **검증 항목**: 마크다운 포맷 유지

### 2.2 OpenSearch 검증

```bash
# 인덱스 확인
curl http://localhost:9200/_cat/indices?v

# 문서 수 확인
curl -X GET "http://localhost:9200/chatbot_documents/_count" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}}'

# 샘플 문서 조회
curl -X GET "http://localhost:9200/chatbot_documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 1,
    "_source": ["content", "file_name", "chunk_index"]
  }'
```

### 2.3 검색 파이프라인 테스트

```bash
# RAG 응답 생성 (REST API)
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "테스트 문서에 대해 질문하세요",
    "session_id": null
  }'
```

## 3. WebSocket 스트리밍 테스트

### 3.1 Python 스크립트 테스트

```python
import asyncio
import json
import websockets
import base64

async def test_streaming():
    # JWT 토큰 가져오기 (로그인 API에서)
    token = "<YOUR_TOKEN>"
    
    uri = "ws://localhost:8000/api/v1/chat/ws/stream"
    async with websockets.connect(uri) as ws:
        # 1. 인증
        await ws.send(json.dumps({
            "type": "connect",
            "token": token
        }))
        
        # 응답 대기
        auth_response = json.loads(await ws.recv())
        print(f"Auth response: {auth_response}")
        
        # 2. 메시지 전송
        await ws.send(json.dumps({
            "type": "message",
            "content": "테스트 질문입니다.",
            "session_id": None
        }))
        
        # 스트리밍 응답 수신
        while True:
            msg = json.loads(await ws.recv())
            print(f"Event type: {msg['type']}, Data: {str(msg.get('data', ''))[:100]}")
            
            if msg["type"] == "done":
                break
            elif msg["type"] == "error":
                print(f"Error: {msg['data']}")
                break

asyncio.run(test_streaming())
```

### 3.2 curl 테스트 (WebSocket)

```bash
# wscat 사용
wscat -c ws://localhost:8000/api/v1/chat/ws/stream
> {"type": "connect", "token": "<TOKEN>"}
< {"type": "content", "data": "..."}
< {"type": "sources", "data": [...]}
< {"type": "done", "data": null}
```

## 4. 전체 E2E 테스트 체크리스트

### 4.1 인프라 상태 확인
- [ ] OpenSearch: `http://localhost:9200` (healthy)
- [ ] PostgreSQL: `postgresql://postgres:password@localhost:5432/rag_chatbot`
- [ ] Redis: `redis://localhost:6379`
- [ ] LMStudio: `http://127.0.0.1:1234/v1/models` (응답)
- [ ] Backend: `http://localhost:8000/docs` (Swagger UI)

### 4.2 인증 테스트
- [ ] 로그인 API (`POST /api/v1/auth/login`) - 성공
- [ ] JWT 토큰 발급 확인
- [ ] 보호된 엔드포인트 접근 (토큰 포함 시 성공, 미포함 시 401)

### 4.3 문서 인제스트 테스트
- [ ] PDF 업로드 → OpenSearch 저장
- [ ] TXT 업로드 → OpenSearch 저장
- [ ] MD 업로드 → OpenSearch 저장
- [ ] 지원하지 않는 형식 (`.docx`) → 400 에러 반환

### 4.4 RAG 검색 테스트
- [ ] 관련 문서 검색 결과 반환
- [ ] RRF 결합 점수 정상 동작
- [ ] Cross-Encoder reranking 동작

### 4.5 채팅 API 테스트
- [ ] REST 응답 생성 (`POST /api/v1/chat/`)
- [ ] WebSocket 스트리밍 (`ws://.../ws/stream`)
- [ ] 세션 유지 (session_id 전달 시 이어서 대화)

### 4.6 프론트엔드 통합 테스트
- [ ] 로그인 페이지 접근 → 성공
- [ ] 채팅 페이지 렌더링
- [ ] 문서 업로드 버튼 클릭 → 파일 선택 다이얼로그
- [ ] 파일 업로드 후 상태 메시지 표시
- [ ] 로그아웃 버튼 클릭 → 세션 종료

## 5. 문제 해결 가이드

### 5.1 LMStudio 연결 실패
```bash
# 포트 확인
ss -tlnp | grep 1234

# 서비스 재시작
systemctl restart lmstudio
```

### 5.2 OpenSearch 연결 실패
```bash
# 인덱스 생성 (없을 경우)
curl -X PUT "http://localhost:9200/chatbot_documents" \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "embedding": {"type": "dense_vector", "dims": 768, "index": true, "similarity": "cosine"},
        "content": {"type": "text"},
        "document_id": {"type": "keyword"},
        "file_name": {"type": "keyword"}
      }
    }
  }'
```

### 5.3 임베딩 모델 로딩 실패
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 모델 다운로드 필요
- 첫 실행 시 자동으로 HuggingFace에서 다운로드됨 (대략 400MB)
