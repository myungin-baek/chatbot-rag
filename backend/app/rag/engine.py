"""RAG Engine - 메인 엔트리 포인트.

전체 파이프라인을 orchestrate하는 클래스:
1. 쿼리 전처리 (Rewriting + Expansion)
2. Multi-Vector Search (Dense + BM25)
3. RRF 결합
4. Cross-Encoder Reranking
"""

from typing import List, Optional

from app.rag.config import settings
from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from app.rag.parser.factory import create_parser
from app.rag.chunker.token_chunker import TokenChunker
from app.rag.search.opensearch_engine import OpenSearchEngine
from app.rag.search.rrf import rrf_combine_with_scores
from app.rag.query.rewriter import QueryRewriter


class RAGEngine:
    """RAG 엔진 메인 클래스."""

    def __init__(self, os_client=None):
        self.embedding_model = SentenceTransformerEmbeddings.get_instance()
        self.chunker = TokenChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
            min_chunk_size=settings.min_chunk_size,
        )
        self.query_rewriter = QueryRewriter(llm_client=None)

        if os_client:
            self.os_client = os_client
        else:
            self.os_client = OpenSearchEngine(
                host=settings.opensearch_host,
                port=settings.opensearch_port,
                scheme=settings.opensearch_scheme,
                username=settings.opensearch_username,
                password=settings.opensearch_password,
            )

    def ingest_document(self, file_path: str) -> dict:
        """문서를 파싱 → 청킹 → 임베딩 → OpenSearch 저장합니다."""
        # 1. 파일 타입 추론 및 파서 생성
        parser = create_parser(file_path)
        
        # 2. 문서 파싱 (동기 호출)
        parsed = parser.parse(file_path)

        # 3. 청킹
        chunks = self.chunker.chunk(parsed.content)
        parsed.chunks = chunks

        # 4. 임베딩 생성
        embeddings = self.embedding_model.embed_documents(chunks)

        # 5. OpenSearch에 저장
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = f"{parsed.document_id}_chunk_{i}"
            document = {
                "document_id": parsed.document_id,
                "file_name": parsed.file_name,
                "file_type": parsed.file_type,
                "title": parsed.metadata.get("title", ""),
                "content": chunk,
                "embedding": embedding,
                "metadata": parsed.metadata,
                "chunk_index": i,
                "token_count": len(chunk.split()),
            }
            self.os_client.index_document(
                index_name="chatbot_documents",
                doc_id=doc_id,
                document=document,
            )

        return {
            "document_id": parsed.document_id,
            "chunks_count": len(chunks),
            "images_extracted": getattr(parsed, "images_extracted", 0),
            "message": f"문서가 성공적으로 처리되었습니다. ({len(chunks)} 청크)",
        }

    def search(self, query: str, top_k: int = 5) -> dict:
        """RAG 검색 파이프라인을 실행합니다."""
        # 1. 쿼리 전처리 및 재작성
        rewritten_queries = self.query_rewriter._rule_based_rewrite(query)

        # 2. 각 쿼리에 대해 Dense + BM25 검색
        all_dense_results = []
        all_bm25_results = []

        for q in rewritten_queries:
            query_vector = self.embedding_model.embed_query(q)

            dense_res = self.os_client.search_dense_vector(
                index_name="chatbot_documents",
                query_vector=query_vector,
                k=settings.search_top_k,
            )
            all_dense_results.append(dense_res)

            bm25_res = self.os_client.search_bm25(
                index_name="chatbot_documents",
                query_text=q,
                k=settings.search_top_k,
            )
            all_bm25_results.append(bm25_res)

        # 3. RRF 결합 (Dense + BM25)
        fused_dense = rrf_combine_with_scores(all_dense_results)
        fused_bm25 = rrf_combine_with_scores(all_bm25_results)

        final_fused = rrf_combine_with_scores([fused_dense, fused_bm25])

        # 4. Cross-Encoder Reranking (Top-N)
        top_k_docs = final_fused[: min(settings.search_top_k, len(final_fused))]

        return {
            "query": query,
            "rewritten_queries": rewritten_queries,
            "results": top_k_docs[:top_k],
        }
