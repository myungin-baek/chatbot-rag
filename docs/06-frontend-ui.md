# 06. 프론트엔드 UI (React SPA + Nginx)

## AWS Console 스타일 디자인 시스템

### 색상 팔레트

| 용도 | 색상 | Hex 코드 |
|------|------|----------|
| 메인 배경 | 회색 | `#F4F5F7` |
| 사이드바 | 흰색 | `#FFFFFF` |
| 헤더 | AWS 블루 | `#16325C` |
| 액션 버튼 | AWS 오렌지 | `#FF8E00` |
| 2차 버튼 | AWS 블루 | `#417D90` |
| 텍스트 (기본) | 다크 그레이 | `#232F3E` |
| 텍스트 (보조) | 그레이 | `#6D757D` |
| 경계선 | 라이트 그레이 | `#D9DBDF` |
| 성공 | 그린 | `#1D8102` |
| 경고 | 옐로우 | `#C4A000` |
| 에러 | 레드 | `#D13212` |

### 타이포그래피

- **폰트**: Amazon Ember (또는 Inter 대체)
- **헤더**: 16px Bold
- **본문**: 14px Regular
- **소문자**: 12px Regular

## React SPA 구조

```
chatbot-frontend/
├── public/
│   ├── index.html              # 진입점
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── Layout.tsx          # AWS Console 스타일 레이아웃
│   │   ├── Sidebar.tsx         # 좌측 사이드바 (메뉴)
│   │   ├── Header.tsx          # 상단 헤더
│   │   ├── ChatWindow.tsx      # 채팅창 컴포넌트
│   │   ├── MessageBubble.tsx   # 메시지 버블 (user/assistant)
│   │   ├── TypingIndicator.tsx # 입력 중 표시기
│   │   ├── SourceReference.tsx # 참조 소스 표시
│   │   └── FloatingChatIcon.tsx# 우측 하단 플로팅 아이콘
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket 커넥션 관리
│   │   └── useChatSession.ts   # 세션 상태 관리
│   ├── services/
│   │   ├── api.ts              # REST API 호출
│   │   └── websocket.ts        # WebSocket 통신
│   ├── App.tsx                 # 메인 앱 컴포넌트
│   └── index.tsx               # 진입점
├── package.json
└── vite.config.ts
```

## 채팅 위젯 UI 구성

### 플로팅 아이콘 (기본 상태)

- **위치**: 우측 하단 고정 (bottom: 24px, right: 24px)
- **크기**: 56x56px 원형 버튼
- **아이콘**: AI 로고 또는 채팅 아이콘
- **배경색**: AWS 블루 (`#16325C`)
- **호버 효과**: 약간 확대 + 그림자

### 채팅창 (확장 상태)

- **크기**: 400x600px (최대)
- **위치**: 우측 하단에서 위로 확장
- **레이아웃**: AWS Console 스타일
  - 상단: 헤더 (채팅봇 이름 + 닫기 버튼)
  - 중앙: 메시지 목록 (스크롤 가능)
  - 하단: 입력 필드 + 전송 버튼

### 메시지 버블

| 역할 | 정렬 | 배경색 | 텍스트 색상 |
|------|------|--------|-------------|
| 사용자 | 우측 | AWS 블루 (`#417D90`) | 흰색 |
| AI | 좌측 | 흰색 (`#FFFFFF`) | 다크 그레이 (`#232F3E`) |

### 소스 참조 표시

- 응답 하단에 작은 카드 형태로 출처 문서 표시
- 클릭 시 원문 확인 모달 열기
- 문서명, 페이지 번호, 관련 구문 표시

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

## 통신 프로토콜

| 타입 | 프로토콜 | 설명 |
|------|----------|------|
| REST API | HTTP | 문서 업로드, 세션 관리, 초기 채팅 요청 |
| 실시간 응답 | WebSocket (ws://) | LLM 스트리밍 응답 수신 |
| 파일 전송 | HTTP multipart | TXT/MD/PDF 파일 업로드 |

## 주요 컴포넌트 상세

### FloatingChatIcon.tsx

```tsx
// 우측 하단 플로팅 버튼
interface FloatingChatIconProps {
    onClick: () => void;
}

const FloatingChatIcon = ({ onClick }: FloatingChatIconProps) => (
    <button
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-[#16325C] text-white shadow-lg hover:shadow-xl transition-all"
        onClick={onClick}
    >
        {/* AI 아이콘 */}
    </button>
);
```

### ChatWindow.tsx

```tsx
// 채팅창 컴포넌트 (AWS Console 스타일)
interface ChatWindowProps {
    isOpen: boolean;
    onClose: () => void;
}

const ChatWindow = ({ isOpen, onClose }: ChatWindowProps) => (
    <div className={`fixed bottom-24 right-6 w-[400px] h-[600px] bg-white rounded-lg shadow-xl border border-[#D9DBDF] ${isOpen ? 'block' : 'hidden'}`}>
        {/* 헤더 */}
        <div className="bg-[#16325C] text-white p-4 rounded-t-lg flex justify-between">
            <span>AI Chatbot</span>
            <button onClick={onClose}>✕</button>
        </div>
        
        {/* 메시지 목록 */}
        <div className="flex-1 overflow-y-auto p-4">
            {/* MessageBubble 컴포넌트들 */}
        </div>
        
        {/* 입력 필드 */}
        <div className="p-4 border-t border-[#D9DBDF]">
            <input type="text" placeholder="메시지를 입력하세요..." />
        </div>
    </div>
);
```
