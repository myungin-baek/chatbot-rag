"""문서 파서 팩토리."""

from pathlib import Path

from app.rag.parser.txt_parser import TextFileParser
from app.rag.parser.md_parser import MarkdownFileParser
from app.rag.parser.pdf_parser import PDFFileParser


# 파일 타입별 파서 매핑
PARSER_MAP = {
    "txt": TextFileParser,
    "md": MarkdownFileParser,
    "pdf": PDFFileParser,
}


def get_parser(file_type: str):
    """파일 타입에 맞는 파서를 반환합니다."""
    parser_class = PARSER_MAP.get(file_type.lower())
    if parser_class is None:
        raise ValueError(f"지원하지 않는 파일 형식: {file_type}")
    return parser_class()


def create_parser(file_path: str):
    """파일 경로에서 타입을 추론하여 파서를 생성합니다."""
    ext = Path(file_path).suffix.lstrip(".").lower()
    return get_parser(ext)
