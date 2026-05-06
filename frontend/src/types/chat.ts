/**
 * 채팅 메시지 인터페이스
 */

export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: any[];
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}
