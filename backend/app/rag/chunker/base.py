"""청커 베이스 클래스."""

from abc import ABC, abstractmethod
from typing import List


class BaseChunker(ABC):
    """모든 청커가 구현해야 할 인터페이스."""

    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """텍스트를 의미 있는 청크로 분할합니다.
        
        Args:
            text: 분할할 원본 텍스트
            
        Returns:
            분할된 청크 리스트
        """
