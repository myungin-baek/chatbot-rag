/**
 * 채팅 페이지 - AWS Console 스타일 UI (WebSocket 스트리밍 지원)
 */

import { useState, useRef, useEffect } from 'react';
import { listSessions, getSession, deleteSession, createChatWebSocket, logout, uploadDocument, listDocuments, deleteDocument } from '../services/api';
import type { SessionInfo as SessionInfoType, DocumentInfo } from '../services/api';
import type { Message } from '../types/chat';
import './ChatPage.css';

function ChatPage() {
  const [sessions, setSessions] = useState<SessionInfoType[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [showDocsPanel, setShowDocsPanel] = useState(false);
  const [userInfo, setUserInfo] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 스트리밍 상태 관리
  const streamingContentRef = useRef<string>('');
  const currentWebSocketRef = useRef<WebSocket | null>(null);

  // 사용자 정보 로드
  useEffect(() => {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        // JWT 토큰에서 사용자 정보 디코딩 (base64url 지원)
        const base64UrlDecode = (str: string): string => {
          let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
          while (base64.length % 4 !== 0) base64 += '=';
          return decodeURIComponent(escape(atob(base64)));
        };
        
        const payload = JSON.parse(base64UrlDecode(token.split('.')[1]));
        setUserInfo({
          username: payload.sub || 'user',
          role: payload.role || 'user',
        });
      } else {
        // 토큰이 없으면 기본값
        setUserInfo({ username: 'user', role: 'user' });
      }
    } catch (err) {
      console.error('사용자 정보 파싱 실패:', err);
      setUserInfo({ username: 'user', role: 'user' });
    }
  }, []);

  // 세션 목록 로드
  useEffect(() => {
    loadSessions();
    loadDocuments();
  }, []);

  // 새 메시지 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContentRef.current]);

  // WebSocket 정리 (언마운트 시)
  useEffect(() => {
    return () => {
      if (currentWebSocketRef.current) {
        currentWebSocketRef.current.close();
      }
    };
  }, []);

  async function loadSessions() {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch (err) {
      console.error('세션 목록 로드 실패:', err);
    }
  }

  async function selectSession(sessionId: string) {
    setIsLoading(true);
    try {
      const data = await getSession(sessionId);
      setCurrentSessionId(sessionId);
      setMessages(data.messages as Message[]);
    } catch (err) {
      console.error('세션 로드 실패:', err);
    } finally {
      setIsLoading(false);
    }
  }

  // WebSocket 스트리밍으로 메시지 전송
  async function handleSendWithStreaming() {
    if (!inputMessage.trim() || isLoading) return;

    const userMsg: Message = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);
    streamingContentRef.current = '';

    // 로딩 메시지 표시
    const loadingMsgId = `streaming-${Date.now()}`;
    const loadingMsg: Message = {
      message_id: loadingMsgId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, loadingMsg]);

    try {
      let receivedSessionId: string | null = null;
      let finalSources: any[] = [];

      // WebSocket 스트리밍 콜백들
      const onContent = (token: string) => {
        streamingContentRef.current += token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.message_id === loadingMsgId ? { ...msg, content: streamingContentRef.current } : msg
          )
        );
      };

      const onSources = (sources: any[]) => {
        finalSources = sources;
      };

      const onError = (error: string) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.message_id === loadingMsgId ? { ...msg, content: `[오류] ${error}` } : msg
          )
        );
        setIsLoading(false);
      };

      const onDone = () => {
        // 스트리밍 메시지 업데이트 (출처 포함)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.message_id === loadingMsgId
              ? { ...msg, sources: finalSources }
              : msg
          )
        );

        setIsLoading(false);
        loadSessions(); // 세션 목록 갱신
      };

      const ws = createChatWebSocket(onContent, onSources, onError, onDone);

      currentWebSocketRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.session_id) {
            receivedSessionId = msg.session_id;
            setCurrentSessionId(msg.session_id);
          }

          switch (msg.type) {
            case 'content':
              streamingContentRef.current += msg.data || '';
              setMessages((prev) =>
                prev.map((m) =>
                  m.message_id === loadingMsgId ? { ...m, content: streamingContentRef.current } : m
                )
              );
              break;
            case 'sources':
              finalSources = msg.data || [];
              setMessages((prev) =>
                prev.map((m) =>
                  m.message_id === loadingMsgId ? { ...m, sources: msg.data || [] } : m
                )
              );
              break;
            case 'done':
              setIsLoading(false);
              loadSessions();
              if (receivedSessionId) {
                setCurrentSessionId(receivedSessionId);
              }
              break;
            case 'error':
              setMessages((prev) =>
                prev.map((m) =>
                  m.message_id === loadingMsgId ? { ...m, content: `[오류] ${msg.data || '알 수 없는 오류'}` } : m
                )
              );
              setIsLoading(false);
              break;
          }
        } catch (err) {
          console.error('WebSocket 메시지 파싱 실패:', err);
        }
      };

    } catch (err) {
      const errorMsg: Message = {
        message_id: `error-${Date.now()}`,
        role: 'system',
        content: err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      setIsLoading(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await deleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      loadSessions();
    } catch (err) {
      console.error('세션 삭제 실패:', err);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadStatus(null);
    setIsLoading(true);

    try {
      await uploadDocument(file);
      setUploadStatus({ type: 'success', message: `"${file.name}" 파일이 성공적으로 업로드되었습니다.` });
      loadDocuments(); // 문서 목록 새로고침
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '업로드에 실패했습니다.';
      setUploadStatus({ type: 'error', message: `업로드 오류: ${errorMsg}` });
    } finally {
      setIsLoading(false);
      // 파일 입력 초기화 (같은 파일을 다시 선택할 수 있도록)
      event.target.value = '';
    }
  }

  async function loadDocuments() {
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      console.error('문서 목록 로드 실패:', err);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    if (!confirm('이 문서를 삭제하시겠습니까?')) return;
    
    try {
      await deleteDocument(documentId);
      loadDocuments(); // 문서 목록 새로고침
    } catch (err) {
      console.error('문서 삭제 실패:', err);
      alert('문서 삭제에 실패했습니다.');
    }
  }

  function handleLogout() {
    logout();
    window.location.href = '/login';
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendWithStreaming();
    }
  }

  return (
    <div className="chat-page">
      {/* 사이드바 */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        {/* 헤더 - 사용자 정보 + 로그아웃 */}
        <div className="sidebar-header">
          <h2>💬 채팅 세션</h2>
          <button onClick={() => setIsSidebarOpen(false)} title="사이드바 닫기">✕</button>
        </div>

        {/* 사용자 정보 영역 */}
        {userInfo && (
          <div className="user-info-bar">
            <span className="user-avatar">{(userInfo.username || 'U')[0].toUpperCase()}</span>
            <div className="user-details">
              <span className="user-name">{userInfo.username}</span>
              <span className="user-role">{userInfo.role === 'admin' ? '관리자' : '사용자'}</span>
            </div>
          </div>
        )}

        {/* 업로드 버튼 */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
        <button className="upload-btn" onClick={() => fileInputRef.current?.click()} disabled={isLoading}>
          📄 문서 업로드
        </button>

        {/* 업로드 상태 메시지 */}
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.type}`}>
            {uploadStatus.message}
          </div>
        )}

        <button className="new-session-btn" onClick={() => { setCurrentSessionId(null); setMessages([]); }}>
          + 새 세션
        </button>

        {/* 로그아웃 버튼 */}
        <button className="logout-btn" onClick={handleLogout}>
          🚪 로그아웃
        </button>

        {/* 문서 목록 토글 버튼 */}
        <button
          className="docs-toggle-btn"
          onClick={() => setShowDocsPanel(!showDocsPanel)}
        >
          {showDocsPanel ? '▲' : '▼'} 소스 문서 ({documents.length})
        </button>

        {/* 문서 목록 패널 */}
        {showDocsPanel && (
          <div className="docs-panel">
            {documents.length === 0 ? (
              <p className="empty-docs">업로드된 문서가 없습니다.</p>
            ) : (
              <ul className="doc-list">
                {documents.map((doc) => (
                  <li key={doc.document_id} className="doc-item">
                    <div className="doc-info">
                      <span className="doc-name">{doc.file_name}</span>
                      <span className="doc-meta">
                        {doc.chunks_count || 0} 청크 · {((doc.file_size || 0) / (1024 * 1024)).toFixed(1)}MB
                      </span>
                    </div>
                    <button
                      className="delete-doc-btn"
                      onClick={() => handleDeleteDocument(doc.document_id)}
                      title="삭제"
                    >
                      🗑
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.session_id} className={`session-item ${currentSessionId === s.session_id ? 'active' : ''}`}>
              <div className="session-info" onClick={() => selectSession(s.session_id)}>
                <span className="session-title">{s.title}</span>
                <span className="session-meta">{s.message_count} 메시지</span>
              </div>
              <button
                className="delete-session-btn"
                onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.session_id); }}
                title="삭제"
              >
                🗑
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 사이드바 토글 버튼 */}
      {!isSidebarOpen && (
        <button className="sidebar-toggle" onClick={() => setIsSidebarOpen(true)}>☰</button>
      )}

      {/* 메인 채팅 영역 */}
      <main className="chat-main">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <h1>RAG AI Chatbot</h1>
            <p>문서를 업로드하고 질문하세요.</p>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.map((msg) => (
                <div key={msg.message_id} className={`message ${msg.role}`}>
                  <div className="message-bubble">
                    <p>{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <details className="sources-collapse">
                        <summary>출처 ({msg.sources.length})</summary>
                        {msg.sources.map((src, i) => (
                          <div key={i} className="source-item">
                            <strong>[{src.file_name || src.document_id}]</strong>
                            <p>{src.content_preview}</p>
                          </div>
                        ))}
                      </details>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message assistant">
                  <div className="message-bubble loading">
                    <span className="typing-indicator">...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 입력 영역 */}
            <div className="input-area">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="메시지를 입력하세요..."
                rows={1}
                disabled={isLoading}
              />
              <button onClick={handleSendWithStreaming} disabled={!inputMessage.trim() || isLoading}>
                전송
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default ChatPage;
