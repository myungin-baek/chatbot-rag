"""쿼리 재작성 및 확장 모듈.

LLM을 활용한 Query Rewriting + Query Expansion
한국어 특화: 형태소 분석기 (KoNLPy/Komoran) 연동 지원
"""

from typing import List, Optional


class QueryRewriter:
    """쿼리 재작성기.
    
    1. LLM 기반 쿼리 재작성 (Query Rewriting)
    2. 관련 질문 생성 (Query Expansion)
    3. 한국어 형태소 분석 연동
    """

    def __init__(self, llm_client: Optional[object] = None):
        self.llm_client = llm_client
        self._konlpy_available = False

    async def rewrite(self, query: str, num_variants: int = 3) -> List[str]:
        """쿼리를 재작성하여 여러 변형 생성합니다.
        
        Args:
            query: 원본 쿼리
            num_variants: 생성할 변형 수
            
        Returns:
            재작성된 쿼리 리스트 (원본 포함)
        """
        variants = [query]

        if self.llm_client:
            # LLM 기반 재작성
            rewritten = await self._llm_rewrite(query, num_variants)
            variants.extend(rewritten)
        else:
            # 기본 규칙 기반 재작성 (LLM 미사용 시)
            variants.extend(self._rule_based_rewrite(query))

        return list(set(variants))[:num_variants + 1]

    async def _llm_rewrite(self, query: str, num_variants: int) -> List[str]:
        """LLM을 사용하여 쿼리를 재작성합니다."""
        prompt = f"""다음 질문과 의미적으로 동일한 다른 표현들을 {num_variants}개 생성하세요.
각 변형은 약간 다른 어조나 관점에서 작성되어야 합니다.

원본 질문: {query}

생성된 질문만 줄바꿈으로 구분하여 출력하세요."""

        response = await self.llm_client.generate(prompt)
        return [q.strip() for q in response.split("\n") if q.strip()]

    def _rule_based_rewrite(self, query: str) -> List[str]:
        """규칙 기반 쿼리 재작성 (LLM 미사용 시 fallback)."""
        variants = []

        # 접미사 추가
        suffixes = ["에 대해", "관련해서", "알려줘"]
        for suffix in suffixes:
            if not query.endswith(suffix):
                variants.append(f"{query} {suffix}")

        return variants

    def expand_query(self, query: str) -> List[str]:
        """쿼리를 확장하여 관련 질문들을 생성합니다.
        
        한국어 특화 형태소 분석을 활용합니다.
        """
        expanded = [query]

        # KoNLPy/Komoran 연동 (선택사항)
        if self._konlpy_available:
            expanded.extend(self._morphological_expand(query))

        return expanded

    def _morphological_expand(self, query: str) -> List[str]:
        """형태소 분석을 통한 쿼리 확장."""
        try:
            from konlpy.tag import Kkma
            kkma = Kkma()
            morphs = kkma.morphs(query)
            
            # 어간 추출 및 관련어 생성
            expanded = []
            for morph in morphs[:3]:  # 상위 3개 형태소만 사용
                expanded.append(f"{query} {morph}")
            return expanded
        except ImportError:
            return []
