"""Markdown 파일 파서."""

import re
from pathlib import Path

try:
    import markdown2
except ImportError:
    markdown2 = None

from app.rag.parser.base import ParsedDocument


class MarkdownFileParser:
    """마크다운 파일 (.md) 파서.
    
    마크다운 → HTML 변환 후 순수 텍스트 추출.
    헤더 구조를 메타데이터로 유지합니다.
    """

    def __init__(self):
        self._markdown2_available = markdown2 is not None

    def parse(self, file_path: str) -> ParsedDocument:
        """마크다운 파일을 파싱합니다."""
        path = Path(file_path)
        
        with open(path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # 제목 추출 (첫 번째 H1)
        title_match = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem

        if self._markdown2_available:
            html = markdown2.markdown(raw_content)
            content = self._extract_text_from_html(html)
        else:
            # fallback: 단순 정규식 추출
            content = self._simple_md_to_text(raw_content)

        return ParsedDocument(
            document_id=path.stem,
            file_name=path.name,
            file_type="md",
            content=content.strip(),
            metadata={"title": title},
        )

    def _extract_text_from_html(self, html: str) -> str:
        """HTML에서 순수 텍스트 추출 (BeautifulSoup 없이 단순화)."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text

    def _simple_md_to_text(self, md_content: str) -> str:
        """마크다운을 단순 텍스트로 변환 (fallback)."""
        lines = []
        for line in md_content.split("\n"):
            # 헤더/리스트/인용구 등 마크다운 기호 제거
            cleaned = re.sub(r"^(#{1,6}|[-*])\s+", "", line)
            lines.append(cleaned)
        return "\n".join(lines).strip()
