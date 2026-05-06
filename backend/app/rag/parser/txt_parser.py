"""TXT 파일 파서."""

import os
from pathlib import Path

from app.rag.parser.base import BaseDocumentParser, ParsedDocument


class TextFileParser(BaseDocumentParser):
    """일반 텍스트 파일 (.txt) 파서."""

    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding

    def parse(self, file_path: str) -> ParsedDocument:
        """텍스트 파일을 읽고 내용을 반환합니다."""
        path = Path(file_path)
        
        with open(path, "r", encoding=self.encoding) as f:
            content = f.read()

        return ParsedDocument(
            document_id=path.stem,
            file_name=path.name,
            file_type="txt",
            content=content.strip(),
            metadata={
                "file_size": os.path.getsize(file_path),
                "encoding": self.encoding,
            },
        )
