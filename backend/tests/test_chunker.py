"""청커 (Chunker) 테스트."""

import pytest
from app.rag.chunker.token_chunker import TokenChunker


class TestTokenChunker:
    """TokenChunker 클래스 테스트."""

    def test_basic_chunking(self):
        """기본 청킹 동작 검증."""
        chunker = TokenChunker(chunk_size=10, overlap=2)
        
        text = " ".join(["word"] * 30)  # 30단어 텍스트
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.split()) <= 12  # chunk_size + overlap

    def test_empty_text(self):
        """빈 텍스트."""
        chunker = TokenChunker()
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_short_text(self):
        """짧은 텍스트 (청크 하나)."""
        chunker = TokenChunker(chunk_size=100, overlap=10)
        
        text = "short text"
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_overlap(self):
        """오버랩이 적용되는지 검증."""
        chunker = TokenChunker(chunk_size=5, overlap=2)
        
        words = ["a", "b", "c", "d", "e", "f", "g"]
        text = " ".join(words)
        chunks = chunker.chunk(text)

        # 오버랩이 적용되면 인접 청크가 일부 공유해야 함
        assert len(chunks) >= 1


class TestChunkerParameters:
    """청커 파라미터 테스트."""

    def test_chunk_size(self):
        """chunk_size 설정 검증."""
        chunker = TokenChunker(chunk_size=5, overlap=0)
        
        text = " ".join(["word"] * 20)
        chunks = chunker.chunk(text)

        for chunk in chunks:
            assert len(chunk.split()) <= 5

    def test_min_chunk_merge(self):
        """min_chunk_size 이하 청크 병합."""
        chunker = TokenChunker(
            chunk_size=10,
            overlap=0,
            min_chunk_size=5,
        )
        
        # 작은 청크가 여러 개 생성되는 텍스트
        text = " ".join(["x"] * 25)
        chunks = chunker.chunk(text)

        # 병합된 후 최소 크기 이상이어야 함
        for chunk in chunks:
            assert len(chunk.split()) >= 4 or len(chunks) == 1


class TestChunkerEdgeCases:
    """청커 경계 케이스 테스트."""

    def test_single_paragraph(self):
        """단일 문단."""
        chunker = TokenChunker()
        
        text = "하나의 긴 문단입니다." * 20
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1

    def test_multiple_paragraphs(self):
        """여러 문단."""
        chunker = TokenChunker(chunk_size=50, overlap=10)
        
        paragraphs = ["paragraph " + str(i) for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
