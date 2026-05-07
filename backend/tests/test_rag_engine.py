"""RAG Engine 통합 테스트 (모의 객체 사용)."""

import pytest
from unittest.mock import MagicMock, patch
from app.rag.engine import RAGEngine


class TestRAGEngineSingleton:
    """RAGEngine 싱글톤 패턴 테스트."""

    def test_singleton_instance(self):
        """싱글톤 인스턴스 반환 검증."""
        engine1 = RAGEngine.get_instance()
        engine2 = RAGEngine.get_instance()
        assert engine1 is engine2


class TestQueryRewriting:
    """쿼리 재작성 테스트 (모의 LLM)."""

    @pytest.fixture
    def mock_engine(self):
        """모의 RAG 엔진."""
        with patch('app.rag.engine.SentenceTransformerEmbeddings'), \
             patch('app.rag.engine.TokenChunker'), \
             patch('app.rag.engine.LLMClient'), \
             patch('app.rag.engine.CrossEncoderReranker'):
            engine = RAGEngine.get_instance()
            return engine

    def test_rule_based_rewrite(self, mock_engine):
        """규칙 기반 쿼리 재작성."""
        query = "Python에서 리스트 컴프리헨션 사용법"
        rewritten = mock_engine.query_rewriter._rule_based_rewrite(query)
        
        # 최소한 원본 쿼리는 포함되어야 함
        assert len(rewritten) >= 1

    def test_query_rewrite_empty(self, mock_engine):
        """빈 쿼리 처리."""
        rewritten = mock_engine.query_rewriter._rule_based_rewrite("")
        assert len(rewritten) == 0


class TestChunker:
    """문서 청킹 테스트."""

    @pytest.fixture
    def chunker(self):
        from app.rag.chunker.token_chunker import TokenChunker
        return TokenChunker(chunk_size=100, overlap=20, min_chunk_size=50)

    def test_basic_chunking(self, chunker):
        """기본 청킹 동작."""
        text = " ".join([f"word{i}" for i in range(500)])
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 1
        # 각 청크는 최소 크기를 가져야 함
        for chunk in chunks:
            assert len(chunk.split()) >= 50

    def test_small_text(self, chunker):
        """작은 텍스트 (청킹되지 않음)."""
        text = "short text"
        chunks = chunker.chunk(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_exact_chunk_size(self, chunker):
        """정확한 청크 크기 테스트."""
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = chunker.chunk(text)
        
        # 100 단어는 100 토큰이므로 하나의 청크여야 함
        assert len(chunks) == 1


class TestDocumentParser:
    """문서 파서 테스트."""

    def test_txt_parser(self, tmp_path):
        """TXT 파일 파싱."""
        from app.rag.parser.txt_parser import TXTParser
        
        # 임시 파일 생성
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello World\nThis is a test document.")
        
        parser = TXTParser()
        result = parser.parse(str(file_path))
        
        assert result.file_name == "test.txt"
        assert result.file_type == "txt"
        assert len(result.content) > 0

    def test_md_parser(self, tmp_path):
        """MD 파일 파싱."""
        from app.rag.parser.md_parser import MarkdownParser
        
        file_path = tmp_path / "test.md"
        file_path.write_text("# Title\n\nThis is a **markdown** document.")
        
        parser = MarkdownParser()
        result = parser.parse(str(file_path))
        
        assert result.file_name == "test.md"
        assert result.file_type == "md"

    def test_pdf_parser_not_found(self, tmp_path):
        """PDF 파서 - 파일 없음."""
        from app.rag.parser.pdf_parser import PDFParser
        
        file_path = tmp_path / "nonexistent.pdf"
        
        parser = PDFParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(str(file_path))

    def test_create_parser_factory(self, tmp_path):
        """파서 팩토리."""
        from app.rag.parser.factory import create_parser
        
        # TXT
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Test content")
        parser_txt = create_parser(str(txt_file))
        assert type(parser_txt).__name__ == "TXTParser"
        
        # MD
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")
        parser_md = create_parser(str(md_file))
        assert type(parser_md).__name__ == "MarkdownParser"


class TestLLMClient:
    """LLM 클라이언트 테스트 (모의)."""

    def test_llm_client_creation(self):
        """LLM 클라이언트 생성."""
        from app.rag.llm.llm_client import LLMClient
        
        with patch('app.rag.llm.llm_client.OpenAI'):
            client = LLMClient()
            assert client.base_url == "http://127.0.0.1:1234/v1"

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        """스트리밍 생성."""
        from app.rag.llm.llm_client import LLMClient
        
        with patch('app.rag.llm.llm_client.OpenAI') as mock_openai:
            # 모의 스트림 응답 설정
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]
            mock_openai.return_value.chat.completions.create.return_value = [mock_chunk]
            
            client = LLMClient()
            tokens = []
            async for token in client.generate_stream("test"):
                tokens.append(token)
            
            assert len(tokens) == 1
            assert tokens[0] == "Hello"


class TestHybridSearch:
    """하이브리드 검색 테스트."""

    def test_rrf_with_scores(self):
        """RRF with scores 검증."""
        from app.rag.search.rrf import rrf_combine_with_scores
        
        results = [
            [{"id": "doc1", "score": 0.9}, {"id": "doc2", "score": 0.8}],
            [{"id": "doc2", "score": 0.85}, {"id": "doc3", "score": 0.7}],
        ]
        
        fused = rrf_combine_with_scores(results)
        
        assert len(fused) == 3
        # doc2가 두 결과에 모두 나타나므로 가장 높은 RRF 점수
        assert fused[0]["id"] == "doc2"


class TestConfig:
    """설정 테스트."""

    def test_default_config(self):
        """기본 설정값 검증."""
        from app.rag.config import settings
        
        assert settings.opensearch_host == "localhost"
        assert settings.opensearch_port == 9200
        assert settings.chunk_size == 500
        assert settings.chunk_overlap == 50
        assert settings.llm_temperature == 0.7
