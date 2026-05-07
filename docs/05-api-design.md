# 05. API 엔드포인트 설계

## 인증 구조 (API Key)

```mermaid
graph LR
    Client[Client App] -->|X-API-Key Header| GW[Gateway]
    GW --> Verify[Key 검증]
    Verify -->|Valid| Process[처리]
    Verify -->|Invalid| Reject[401 Unauthorized]
    
    subgraph "API Key 관리"
        DB[(DB/Redis)]
        Admin[관리자 대시보드]
    end
    
    GW --> DB
    Admin --> DB
```

## API 엔드포인트 목록

### 인증

| Method | Endpoint | 설명 | Header |
|--------|----------|------|--------|
| POST | `/api/v1/auth` | API Key 검증 | `X-API-Key: <key>` |

### 채팅

| Method | Endpoint | 설명 | Body |
|--------|----------|------|------|
| POST | `/api/v1/chat` | 채팅 메시지 전송 | `{ "message": "...", "session_id": "..." }` |
| GET | `/api/v1/sessions/{id}` | 세션 조회 | - |
| DELETE | `/api/v1/sessions/{id}` | 세션 삭제 | - |

### 문서 관리

| Method | Endpoint | 설명 | Content-Type |
|--------|----------|------|--------------|
| POST | `/api/v1/documents/upload` | 문서 업로드 (TXT, MD, PDF) | `multipart/form-data` |
| GET | `/api/v1/documents` | 문서 목록 조회 | - |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 | - |

### 파라미터 설정

| Method | Endpoint | 설명 | Body |
|--------|----------|------|------|
| PUT | `/api/v1/settings` | 파라미터 설정 | `{ "model", "temperature", ... }` |
| GET | `/api/v1/settings` | 현재 설정 조회 | - |

## 상세 API 스펙

### POST /api/v1/chat

**요청**:
```json
{
    "message": "안녕하세요, PDF 문서에 대해 질문이 있습니다.",
    "session_id": "sess_abc123",
    "rag_config": {
        "top_k": 5,
        "rerank_enabled": true
    }
}
```

**응답 (스트리밍)**:
```json
{
    "session_id": "sess_abc123",
    "message_id": "msg_xyz789",
    "content": "안녕하세요! PDF 문서에 대해 궁금한 점이 있으신가요?",
    "sources": [
        {
            "document_id": "doc_001",
            "page": 5,
            "text": "관련 내용..."
        }
    ],
    "timestamp": "2026-05-04T01:00:02Z"
}
```

### POST /api/v1/documents/upload

**요청**:
```
POST /api/v1/documents/upload
Header: X-API-Key: <your-api-key>
Content-Type: multipart/form-data

{
    "file": <binary file>,           # .txt, .md 또는 .pdf 파일
    "metadata": {                     # 선택사항
        "title": "문서 제목",
        "category": "카테고리명",
        "tags": ["태그1", "태그2"]
    }
}
```

**응답 (200 OK)**:
```json
{
    "document_id": "doc_abc123",
    "status": "processing",           # processing | completed | failed
    "chunks_count": 15,
    "images_extracted": 3,            # PDF인 경우 추출된 이미지 수
    "message": "문서가 성공적으로 업로드되었습니다."
}
```

### 파라미터 설정 API 구조

```json
{
    "model": "llama3",
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.9,
    "system_prompt": "당신은 친절한 AI 어시스턴트입니다.",
    "rag_config": {
        "top_k": 5,
        "rerank_enabled": true,
        "hybrid_search": true
    }
}
```

## WebSocket 엔드포인트

### ws://host/ws/chat (구버전)

**연결**:
```javascript
const ws = new WebSocket('ws://chatbot.example.com/ws/chat');
ws.send(JSON.stringify({
    type: 'connect',
    session_id: 'sess_abc123',
    api_key: '<your-api-key>'
}));
```

**메시지 타입**:
| 타입 | 방향 | 설명 |
|------|------|------|
| `message` | Client → Server | 채팅 메시지 전송 |
| `chunk` | Server → Client | 스트리밍 응답 청크 |
| `done` | Server → Client | 응답 완료 |
| `error` | Server → Client | 에러 발생 |

### ws://host/ws/stream (실제 구현, 2026-05-06)

**엔드포인트**: `POST /api/v1/chat/` (REST), `ws://host/api/v1/chat/ws/stream` (WebSocket)

**WebSocket 연결**:
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`wss://${location.host}/api/v1/chat/ws/stream`);

ws.onopen = () => {
    // 인증 메시지 전송
    ws.send(JSON.stringify({ type: 'connect', token }));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
        case 'content':   // 콘텐츠 토큰
            appendToken(msg.data);
            break;
        case 'sources':   // 출처 정보
            showSources(msg.data);
            break;
        case 'done':      // 스트리밍 완료
            setIsLoading(false);
            break;
        case 'error':     // 오류
            showError(msg.data);
            break;
    }
};
```

**메시지 타입**:
| 타입 | 방향 | 설명 |
|------|------|------|
| `connect` | Client → Server | 인증 토큰 전송 |
| `message` | Client → Server | 채팅 메시지 (`{content, session_id}`) |
| `content` | Server → Client | 콘텐츠 토큰 (스트리밍) |
| `sources` | Server → Client | 출처 정보 (마지막에 한 번) |
| `done` | Server → Client | 스트리밍 완료 |
| `error` | Server → Client | 에러 발생 |

## 인증 구조 (JWT 기반, 2026-05-06 업데이트)

> **참고**: 초기 설계에서는 API Key를 사용했으나, 실제 구현에서는 JWT 토큰 기반 인증을 사용합니다.

### 로그인
```bash
POST /api/v1/auth/login
{ "username": "admin", "password": "sjaksahffk." }

# 응답
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### 토큰 사용
모든 API 요청에 `Authorization: Bearer <token>` 헤더 추가.
