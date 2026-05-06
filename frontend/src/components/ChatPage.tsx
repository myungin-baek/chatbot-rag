/**
 * 채팅 페이지 - AWS Console 스타일 UI
 */

import { useState, useRef, useEffect } from 'react';
import { sendMessage, listSessions, getSession, deleteSession } from '../services/api';
import type { SessionInfo as SessionInfoType } from '../services/api';
import type { Message } from '../types/chat';
import './ChatPage.css';

function ChatPage() {
  const [sessions, setSessions] = useState<SessionInfoType[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 세션 목록 로드
  useEffect(() => {
    loadSessions();
  }, []);

  // 새 메시지 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

  async function handleSend() {
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

    try {
      const response = await sendMessage({
        message: inputMessage,
        session_id: currentSessionId,
      });

      setCurrentSessionId(response.session_id);
      await loadSessions(); // 세션 목록 갱신

      const assistantMsg: Message = {
        message_id: response.message_id,
        role: 'assistant',
        content: response.content,
        sources: response.sources,
        created_at: response.timestamp,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        message_id: `error-${Date.now()}`,
        role: 'system',
        content: err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
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

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-page">
      {/* 사이드바 */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>💬 채팅 세션</h2>
          <button onClick={() => setIsSidebarOpen(false)} title="사이드바 닫기">✕</button>
        </div>

        <button className="new-session-btn" onClick={() => { setCurrentSessionId(null); setMessages([]); }}>
          + 새 세션
        </button>

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
              <button onClick={handleSend} disabled={!inputMessage.trim() || isLoading}>
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
