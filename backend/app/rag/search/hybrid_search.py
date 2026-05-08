"""Hybrid Search (Dense Vector + BM25) 구현."""

from typing import List, Optional

from app.rag.search.base import BaseSearchEngine, SearchResult
from app.rag.search.opensearch_engine import OpenSearchEngine
from app.rag.search.rrf import rrf_combine_with_scores


class HybridSearch(BaseSearchEngine):
    """Dense Vector + BM25 하이브리드 검색 엔진.
    
    1. Dense Vector (k-NN)로 Top-K 문서 검색
    2. BM25 키워드 검색으로 Top-K 문서 검색
    3. RRF 알고리즘으로 두 결과 결합 및 재순위화
    """

    def __init__(self, engine: OpenSearchEngine):
        self.engine = engine

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """하이브리드 검색을 수행합니다."""
        from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
        
        # 임베딩 모델에서 쿼리 벡터 생성
        embedding_model = SentenceTransformerEmbeddings.get_instance()
        query_vector = embedding_model.embed_query(query)
        
        dense_results = self.engine.search_dense_vector(
            index_name="chatbot_documents",
            query_vector=query_vector,
            k=top_k * 10,
        )
        
        bm25_results = self.engine.search_bm25(
            index_name="chatbot_documents",
            query_text=query,
            k=top_k * 10,
        )

        # RRF 결합
        fused = rrf_combine_with_scores([dense_results, bm25_results])
        
        return [SearchResult(**item) for item in fused[:top_k]]
