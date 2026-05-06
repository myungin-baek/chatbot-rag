"""문서 파서 베이스 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class ParsedDocument:
    """파싱된 문서 결과."""

    document_id: str
    file_name: str
    file_type: str  # txt, md, pdf
    content: str  # 전체 텍스트 내용
    chunks: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    images_extracted: int = 0


class BaseDocumentParser(ABC):
    """모든 문서 파서가 구현해야 할 인터페이스."""

    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        """문서를 파싱하여 텍스트 청크로 분할합니다.
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파싱된 문서 결과
        """
