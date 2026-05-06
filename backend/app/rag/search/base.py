"""검색 엔진 베이스 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchResult:
    """검색 결과 항목."""

    document_id: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0
    token_count: int = 0


class BaseSearchEngine(ABC):
    """모든 검색 엔진이 구현해야 할 인터페이스."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """쿼리에 대한 검색 결과를 반환합니다.
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            정렬된 검색 결과 리스트 (점수 내림차순)
        """
