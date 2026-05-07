"""RAG Engine - 메인 엔트리 포인트.

전체 파이프라인을 orchestrate하는 클래스:
1. 쿼리 전처리 (Rewriting + Expansion)
2. Multi-Vector Search (Dense + BM25)
3. RRF 결합
4. Cross-Encoder Reranking
5. LLM 응답 생성 (일반/스트리밍)
"""

import logging
from typing import AsyncGenerator, List, Optional

from app.rag.config import settings
from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from app.rag.parser.factory import create_parser
from app.rag.chunker.token_chunker import TokenChunker
from app.rag.search.opensearch_engine import OpenSearchEngine
from app.rag.search.rrf import rrf_combine_with_scores
from app.rag.query.rewriter import QueryRewriter
from app.rag.llm.llm_client import LLMClient
from app.rag.reranker.cross_encoder_reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG 엔진 메인 클래스."""

    _instance = None

    def __init__(self, os_client=None):
        self.embedding_model = SentenceTransformerEmbeddings.get_instance()
        self.chunker = TokenChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
            min_chunk_size=settings.min_chunk_size,
        )
        self.query_rewriter = QueryRewriter(llm_client=None)
        self.llm = LLMClient.get_instance()
        self.reranker = CrossEncoderReranker(model_name=settings.cross_encoder_model_name)

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

    @classmethod
    def get_instance(cls, os_client=None) -> "RAGEngine":
        """싱글톤 인스턴스 반환."""
        if cls._instance is None:
            cls._instance = cls(os_client=os_client)
        return cls._instance

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
        """RAG 검색 파이프라인을 실행합니다.
        
        1. 쿼리 전처리 및 재작성
        2. Dense + BM25 검색
        3. RRF 결합
        4. Cross-Encoder Reranking
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 딕셔너리 (query, rewritten_queries, results)
        """
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
        candidates = final_fused[: min(settings.search_top_k, len(final_fused))]
        
        try:
            ranked_docs = self.reranker.rerank(
                query=query,
                documents=candidates,
                top_n=settings.rerank_top_n,
            )
        except Exception as e:
            logger.warning(f"Cross-Encoder reranker failed, using RRF results: {e}")
            ranked_docs = candidates[:settings.rerank_top_n]

        return {
            "query": query,
            "rewritten_queries": rewritten_queries,
            "results": ranked_docs[:top_k],
        }

    def generate_response(self, query: str, conversation_history: Optional[List[dict]] = None) -> dict:
        """RAG 기반 응답을 전체 파이프라인으로 생성합니다.
        
        1. OpenSearch에서 관련 문서 검색
        2. LLM에 컨텍스트 + 쿼리 전달
        3. 응답 + 출처 반환
        
        Args:
            query: 사용자 질문
            conversation_history: 대화 히스토리 (role, content 포함)
            
        Returns:
            딕셔너리 (content, sources, metadata)
        """
        # 1. 관련 문서 검색
        search_result = self.search(query, top_k=settings.rerank_top_n)
        results = search_result.get("results", [])

        # 2. LLM 응답 생성
        try:
            content = self.llm.generate_with_context(
                query=query,
                context_documents=results,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            content = f"[LLM 오류] 응답 생성에 실패했습니다: {str(e)}"

        # 3. 출처 정보 추출
        sources = []
        for doc in results:
            sources.append({
                "document_id": doc.get("document_id", ""),
                "file_name": doc.get("file_name", ""),
                "content_preview": doc.get("content", "")[:200] + "...",
                "score": doc.get("rerank_score", doc.get("rrf_score", 0)),
            })

        return {
            "content": content,
            "sources": sources,
            "metadata": {
                "rewritten_queries": search_result.get("rewritten_queries", []),
                "search_count": len(results),
            },
        }

    async def generate_response_stream(
        self, query: str, conversation_history: Optional[List[dict]] = None
    ) -> AsyncGenerator[tuple, None]:
        """RAG 기반 스트리밍 응답을 생성합니다.

        1. OpenSearch에서 관련 문서 검색 (동기)
        2. LLM에 컨텍스트 + 쿼리 전달 (스트리밍)
        3. 토큰 단위 스트림 반환

        Yields:
            (event_type, data) 튜플
            - ("content", token_string): 콘텐츠 토큰
            - ("sources", sources_list): 출처 정보 (마지막에 한 번)
            - ("done", None): 스트리밍 완료
        """
        # 1. 관련 문서 검색 (동기 작업)
        search_result = self.search(query, top_k=settings.rerank_top_n)
        results = search_result.get("results", [])

        # 출처 정보 추출
        sources = []
        for doc in results:
            sources.append({
                "document_id": doc.get("document_id", ""),
                "file_name": doc.get("file_name", ""),
                "content_preview": doc.get("content", "")[:200] + "...",
                "score": doc.get("rerank_score", doc.get("rrf_score", 0)),
            })

        # 2. LLM 스트리밍 응답 생성
        try:
            async for token in self.llm.generate_with_context_stream(
                query=query,
                context_documents=results,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            ):
                yield ("content", token)

            # 3. 출처 정보 전송
            yield ("sources", sources)

        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield ("error", f"[LLM 오류] 응답 생성에 실패했습니다: {str(e)}")

        finally:
            # 4. 완료 신호
            yield ("done", None)

    def delete_document_vectors(self, document_id: str) -> dict:
        """OpenSearch에서 특정 문서의 모든 벡터를 삭제합니다.
        
        Args:
            document_id: 삭제할 문서 ID
            
        Returns:
            삭제 결과 딕셔너리
        """
        query = {
            "term": {"document_id": document_id},
        }
        return self.os_client.delete_documents_by_filter(
            index_name="chatbot_documents",
            query=query,
        )
