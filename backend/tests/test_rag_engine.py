"""RAG 엔진 통합 테스트."""

import os
import tempfile
import pytest
from app.rag.config import settings


class TestRAGConfig:
    """RAG 설정 테스트."""

    def test_default_settings(self):
        """기본 설정값 검증."""
        assert settings.chunk_size == 500
        assert settings.chunk_overlap == 50
        assert settings.min_chunk_size == 100
        assert settings.search_top_k == 100
        assert settings.rerank_top_n == 5
        assert settings.rrf_k == 60

    def test_embedding_dim(self):
        """임베딩 차원 설정."""
        assert settings.embedding_dim == 768


class TestEmbeddingModel:
    """임베딩 모델 테스트 (실제 모델 로딩)."""

    @pytest.mark.skip(reason="모델 다운로드 시간 소요")
    def test_embed_query(self):
        """쿼리 임베딩 검증."""
        from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
        
        model = SentenceTransformerEmbeddings.get_instance()
        embedding = model.embed_query("테스트 쿼리")

        assert isinstance(embedding, list)
        assert len(embedding) == settings.embedding_dim
        # 정규화 확인 (L2 norm ≈ 1)
        import math
        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.1

    @pytest.mark.skip(reason="모델 다운로드 시간 소요")
    def test_embed_documents(self):
        """배치 임베딩 검증."""
        from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
        
        model = SentenceTransformerEmbeddings.get_instance()
        
        texts = ["첫 번째 문서", "두 번째 문서", "세 번째 문서"]
        embeddings = model.embed_documents(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert isinstance(emb, list)
            assert len(emb) == settings.embedding_dim


class TestQueryRewriter:
    """쿼리 재작성기 테스트."""

    def test_rewrite_basic(self):
        """기본 쿼리 재작성 (LLM 없이)."""
        from app.rag.query.rewriter import QueryRewriter
        
        rewriter = QueryRewriter()
        
        rewritten = rewriter._rule_based_rewrite("RAG란 무엇인가요?")

        assert len(rewritten) >= 1


class TestChunkerIntegration:
    """청커 통합 테스트."""

    def test_chunk_long_text(self):
        """긴 텍스트 청킹."""
        from app.rag.chunker.token_chunker import TokenChunker
        
        chunker = TokenChunker(chunk_size=50, overlap=10)
        
        text = "한국어 테스트 문장. " * 100
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) > 0


class TestRRFIntegration:
    """RRF 통합 테스트."""

    def test_rrf_with_realistic_data(self):
        """실제 데이터 기반 RRF 검증."""
        from app.rag.search.rrf import rrf_combine
        
        # Dense 검색 결과 (의미적 유사성)
        dense = [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}]
        
        # BM25 검색 결과 (키워드 매칭)
        bm25 = [{"id": "doc2"}, {"id": "doc4"}, {"id": "doc5"}]

        fused = rrf_combine([dense, bm25])

        # doc2가 두 검색에서 모두 등장하므로 1등이어야 함
        assert fused[0][0] == "doc2"
        assert len(fused) == 5


class TestParserIntegration:
    """파서 통합 테스트."""

    def test_full_pipeline_txt(self):
        """TXT 파일 전체 파이프라인 (파싱 + 청킹)."""
        from app.rag.parser.txt_parser import TextFileParser
        from app.rag.chunker.token_chunker import TokenChunker
        
        parser = TextFileParser()
        chunker = TokenChunker(chunk_size=50, overlap=10)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("테스트 문서입니다. " * 20)
            temp_path = f.name

        try:
            parsed = parser.parse(temp_path)
            chunks = chunker.chunk(parsed.content)

            assert len(chunks) >= 1
            for chunk in chunks:
                assert len(chunk) > 0
        finally:
            os.unlink(temp_path)


class TestCrossEncoderReranker:
    """Cross-Encoder 랭커 테스트."""

    @pytest.mark.skip(reason="모델 다운로드 시간 소요")
    def test_rerank(self):
        """Cross-Encoder 재랭킹 검증."""
        from app.rag.reranker.cross_encoder_reranker import CrossEncoderReranker
        
        reranker = CrossEncoderReranker()
        
        documents = [
            {"document_id": "doc1", "content": "Python 프로그래밍 언어"},
            {"document_id": "doc2", "content": "자바스크립트 웹 개발"},
            {"document_id": "doc3", "content": "파이썬으로 데이터 분석하기"},
        ]

        ranked = reranker.rerank("Python 데이터 분석", documents, top_n=2)

        assert len(ranked) == 2
        # Python 관련 문서가 상위권에 있어야 함
        assert any("doc1" in str(d) or "doc3" in str(d) for d in ranked)


class TestRAGEngine:
    """RAG 엔진 테스트."""

    def test_engine_initialization(self):
        """엔진 초기화 검증."""
        from app.rag.engine import RAGEngine
        
        engine = RAGEngine()
        
        assert engine.embedding_model is not None
        assert engine.chunker is not None
        assert engine.os_client is not None
