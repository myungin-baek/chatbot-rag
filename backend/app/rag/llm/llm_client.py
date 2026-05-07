"""LLM 모듈 - LMStudio (OpenAI 호환) 연동."""

from typing import List, Optional
from openai import OpenAI

from app.rag.config import settings


class LLMClient:
    """LLM 클라이언트 (LMStudio OpenAI 호환 API).
    
    LMStudio는 OpenAI 호환 API를 제공하므로 openai 패키지를直接使用합니다.
    기본 URL: http://127.0.0.1:1234/v1
    """
    
    _instance = None
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.client = OpenAI(
            base_url=self.base_url,
            api_key="lm-studio",  # LMStudio는 API key 불필요
        )
    
    @classmethod
    def get_instance(cls) -> "LLMClient":
        """싱글톤 인스턴스 반환."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """일반 텍스트 생성."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[LLM 오류] {str(e)}"
    
    def generate_with_context(
        self,
        query: str,
        context_documents: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """RAG 기반 응답 생성 (검색된 문서를 컨텍스트로 사용).
        
        Args:
            query: 사용자 질문
            context_documents: RAG 검색 결과 문서 리스트
            system_prompt: 시스템 프롬프트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
            
        Returns:
            LLM 응답 텍스트
        """
        # 컨텍스트 문서 조합
        context_text = ""
        for i, doc in enumerate(context_documents, 1):
            content = doc.get("content", "")
            source = doc.get("file_name", doc.get("document_id", f"문서{i}"))
            context_text += f"[출처 {i} ({source})]: {content}\\n\\n"
        
        # 시스템 프롬프트
        if not system_prompt:
            system_prompt = """너는 지식이 풍부하고 도움이 되는 AI 어시스턴트입니다.
주어진 문서 컨텍스트를 바탕으로 사용자의 질문에 정확하고 간결하게 답변하세요.
컨텍스트에 없는 정보는 '알 수 없습니다'라고 답변하세요.
답변 마지막에 사용된 출처를 명시하세요."""
        
        # 사용자 프롬프트
        prompt = f"""다음 문서 컨텍스트를 참고하여 질문에 답변하세요:

<컨텍스트>
{context_text}
</컨텍스트>

<질문>
{query}
</질문>

답변:"""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    def is_available(self) -> bool:
        """LLM 서버 연결 확인."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=1,
            )
            return response is not None
        except Exception:
            return False


    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """스트리밍 텍스트 생성 (async generator)."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"[LLM 오류] {str(e)}"

    async def generate_with_context_stream(
        self,
        query: str,
        context_documents: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """RAG 기반 스트리밍 응답 생성."""
        # 컨텍스트 문서 조합
        context_text = ""
        for i, doc in enumerate(context_documents, 1):
            content = doc.get("content", "")
            source = doc.get("file_name", doc.get("document_id", f"문서{i}"))
            context_text += f"[출처 {i} ({source})]: {content}\n\n"
        
        # 시스템 프롬프트
        if not system_prompt:
            system_prompt = """너는 지식이 풍부하고 도움이 되는 AI 어시스턴트입니다.
주어진 문서 컨텍스트를 바탕으로 사용자의 질문에 정확하고 간결하게 답변하세요.
컨텍스트에 없는 정보는 '알 수 없습니다'라고 답변하세요.
답변 마지막에 사용된 출처를 명시하세요."""
        
        # 사용자 프롬프트
        prompt = f"""다음 문서 컨텍스트를 참고하여 질문에 답변하세요:

<컨텍스트>
{context_text}
</컨텍스트>

<질문>
{query}
</질문>

답변:"""
        
        async for token in self.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield token


# 설정값에 LLM 관련 옵션 추가 (config.py에 없는 경우 기본값 제공)
def _get_llm_base_url() -> str:
    import os
    return os.getenv("LMSTUDIO_URL", "http://127.0.0.1:1234/v1")


def _get_llm_model() -> str:
    import os
    return os.getenv("LLM_MODEL", "lmstudio-community")
