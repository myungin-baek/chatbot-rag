"""랭커 베이스 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class RankedResult:
    """랭킹된 결과."""

    document_id: str
    content: str
    score: float
    rank: int


class BaseReranker(ABC):
    """모든 랭커가 구현해야 할 인터페이스."""

    @abstractmethod
    def rerank(self, query: str, documents: List[RankedResult], top_n: int = 5) -> List[RankedResult]:
        """문서들을 재랭킹합니다.
        
        Args:
            query: 검색 쿼리
            documents: 랭킹할 문서 리스트
            top_n: 반환할 결과 수
            
        Returns:
            재랭킹된 문서 리스트 (점수 내림차순)
        """
