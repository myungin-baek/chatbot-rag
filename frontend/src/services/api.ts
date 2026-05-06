/**
 * API 서비스 모듈
 * 백엔드 REST API 호출
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 인증 토큰 관리
function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function setToken(token: string): void {
  localStorage.setItem('access_token', token);
}

function clearToken(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
}

// 기본 헤더
async function getHeaders(contentType: string = 'application/json'): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': contentType,
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// API 응답 처리
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// ===== 인증 API =====

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: string;
  expires_in: number;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: await getHeaders(),
    body: JSON.stringify(data),
  });
  const result = await handleResponse<LoginResponse>(response);
  setToken(result.access_token);
  return result;
}

export function logout(): void {
  clearToken();
}

// ===== 채팅 API =====

export interface ChatRequest {
  message: string;
  session_id?: string | null;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  content: string;
  sources: any[];
  timestamp: string;
}

export async function sendMessage(data: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: await getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<ChatResponse>(response);
}

// ===== 세션 API =====

export interface SessionInfo {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail {
  session_id: string;
  title: string;
  messages: Array<{
    message_id: string;
    role: string;
    content: string;
    sources: any[];
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export async function listSessions(): Promise<SessionInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/`, {
    headers: await getHeaders(),
  });
  return handleResponse<SessionInfo[]>(response);
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
    headers: await getHeaders(),
  });
  return handleResponse<SessionDetail>(response);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: await getHeaders(),
  });
  return handleResponse(response);
}

// ===== 문서 API =====

export interface DocumentInfo {
  document_id: string;
  file_name: string;
  file_type: string;
  file_size: number | null;
  chunks_count: number | null;
  status: string;
  created_at: string;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/`, {
    headers: await getHeaders(),
  });
  return handleResponse<DocumentInfo[]>(response);
}

export async function uploadDocument(file: File): Promise<{ document_id: string; file_name: string; status: string; chunks_count: number | null; message: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
    },
    body: formData,
  });
  return handleResponse(response);
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
    method: 'DELETE',
    headers: await getHeaders(),
  });
  return handleResponse(response);
}
