"""문서 파서 테스트."""

import os
import tempfile
import pytest
from app.rag.parser.txt_parser import TextFileParser
from app.rag.parser.md_parser import MarkdownFileParser
from app.rag.parser.factory import get_parser, create_parser


class TestTextFileParser:
    """TXT 파일 파서 테스트."""

    def test_parse_txt_file(self):
        """텍스트 파일 파싱 검증."""
        parser = TextFileParser()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!\nThis is a test file.")
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            
            assert result.document_id == os.path.splitext(os.path.basename(temp_path))[0]
            assert result.file_type == "txt"
            assert "Hello, World!" in result.content
            assert len(result.chunks) == 0  # 파서 단계에서는 청킹 안 함
        finally:
            os.unlink(temp_path)

    def test_parse_empty_file(self):
        """빈 파일 파싱."""
        parser = TextFileParser()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            assert result.content == ""
        finally:
            os.unlink(temp_path)


class TestMarkdownFileParser:
    """MD 파일 파서 테스트."""

    def test_parse_md_file(self):
        """마크다운 파일 파싱 검증."""
        parser = MarkdownFileParser()
        
        md_content = """# Test Document

This is a **test** markdown file.

## Section 1
Content here.

- Item 1
- Item 2
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(md_content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            
            assert result.file_type == "md"
            assert result.metadata.get("title") == "Test Document"
            assert len(result.content) > 0
        finally:
            os.unlink(temp_path)


class TestParserFactory:
    """파서 팩토리 테스트."""

    def test_get_parser_txt(self):
        """TXT 파서 생성."""
        parser = get_parser("txt")
        assert parser is not None

    def test_get_parser_md(self):
        """MD 파서 생성."""
        parser = get_parser("md")
        assert parser is not None

    def test_get_parser_pdf(self):
        """PDF 파서 생성."""
        parser = get_parser("pdf")
        assert parser is not None

    def test_get_parser_invalid(self):
        """지원하지 않는 파일 형식."""
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            get_parser("unknown")

    def test_create_parser_from_path(self):
        """파일 경로에서 파서 생성."""
        parser = create_parser("/path/to/file.txt")
        assert isinstance(parser, TextFileParser)


class TestParserEdgeCases:
    """파서 경계 케이스 테스트."""

    def test_large_file(self):
        """대용량 파일 처리."""
        parser = TextFileParser()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("단어 " * 10000)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            assert len(result.content) > 0
        finally:
            os.unlink(temp_path)

    def test_special_characters(self):
        """특수 문자 포함 파일."""
        parser = TextFileParser()
        
        content = "한글 테스트! @#$%^&*()\n\n日本語もテスト。"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            assert "한글 테스트!" in result.content
        finally:
            os.unlink(temp_path)
