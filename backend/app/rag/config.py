"""RAG 엔진 설정."""

from pydantic_settings import BaseSettings


class RAGSettings(BaseSettings):
    """RAG 엔진 설정값."""

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_scheme: str = "http"
    opensearch_index_prefix: str = "chatbot"
    opensearch_username: str = "admin"
    opensearch_password: str = ""

    # 임베딩 모델 (LMStudio BGE-M3)
    embedding_model_name: str = "text-embedding-bge-m3"
    embedding_dim: int = 1024

    # 청킹 설정
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 100

    # 검색 설정
    search_top_k: int = 100  # Stage 1 (Dense/BM25) 결과 수
    rerank_top_n: int = 5   # Stage 2 (Cross-Encoder) 결과 수
    rrf_k: int = 60         # RRF 상수

    # Cross-Encoder Ranker
    cross_encoder_model_name: str = "BAAI/bge-reranker-v2-m3"

    # 쿼리 재작성 (LLM 기반)
    query_rewrite_enabled: bool = True
    num_rewritten_queries: int = 3

    # LLM (LMStudio OpenAI 호환)
    llm_base_url: str = "http://127.0.0.1:1234/v1"
    llm_model: str = "qwen/qwen3.6-27b"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    
    # 임베딩 모델 (LMStudio)
    embedding_api_url: str = "http://127.0.0.1:1234/v1"
    embedding_model_name: str = "text-embedding-bge-m3"

    model_config = {"env_file": ".env", "env_prefix": "RAG_"}


settings = RAGSettings()
