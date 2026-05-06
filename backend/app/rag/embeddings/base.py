"""임베딩 모델 베이스 클래스."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingModel(ABC):
    """모든 임베딩 모델이 구현해야 할 인터페이스."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서를 임베딩합니다.
        
        Args:
            texts: 임베딩할 문서 목록
            
        Returns:
            각 문서의 임베딩 벡터 리스트
        """

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """쿼리 텍스트를 임베딩합니다.
        
        Args:
            text: 쿼리 텍스트
            
        Returns:
            임베딩 벡터
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """임베딩 차원."""
