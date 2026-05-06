"""OpenSearch 인덱스 설정 및 스키마 정의."""

from app.rag.config import settings


# 인덱스 이름 접두사 기반 생성
def get_index_name(base: str) -> str:
    return f"{settings.opensearch_index_prefix}_{base}"


# 주요 인덱스명
INDEX_DOCUMENTS = get_index_name("documents")       # 문서 메타데이터 + 텍스트 청크
INDEX_EMBEDDINGS = get_index_name("embeddings")     # 임베딩 벡터
INDEX_SESSIONS = get_index_name("sessions")          # 세션 기록


# OpenSearch 인덱스 매핑 (Dense Vector + BM25 Hybrid)
DOCUMENTS_MAPPING = {
    "mappings": {
        "properties": {
            "document_id": {"type": "keyword"},
            "file_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "file_type": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "ko_analyzer"},
            "content": {"type": "text", "analyzer": "ko_analyzer"},
            "embedding": {
                "type": "knn_vector",
                "dimension": settings.embedding_dim,
                "method": {
                    "name": "hnsw",
                    "space_type": "l2",
                    "engine": "faiss",
                    "parameters": {"ef_construction": 128, "m": 16}
                }
            },
            "metadata": {
                "properties": {
                    "category": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "source_url": {"type": "text"}
                }
            },
            "chunk_index": {"type": "integer"},
            "token_count": {"type": "integer"},
            "created_at": {"type": "date", "format": "epoch_millis"},
            "updated_at": {"type": "date", "format": "epoch_millis"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                # 한국어 분할용 커스텀 분석기 (KoNLPy/Komoran 연동 시 활성화)
                "ko_analyzer": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["nori_number", "lowercase", "ko_stop"]
                }
            },
            # Nori 토크나이저 필터 (OpenSearch 분석 플러그인 필요)
            "token_filter": {
                "ko_stop": {"type": "stop", "stops": [".", ",", "!", "?", "의", "에", "는", "이", "가"]}
            }
        }
    }
}


# 세션 인덱스 매핑
SESSIONS_MAPPING = {
    "mappings": {
        "properties": {
            "session_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "messages": {
                "type": "nested",
                "properties": {
                    "role": {"type": "keyword"},
                    "content": {"type": "text"},
                    "timestamp": {"type": "date", "format": "epoch_millis"}
                }
            },
            "created_at": {"type": "date", "format": "epoch_millis"},
            "updated_at": {"type": "date", "format": "epoch_millis"}
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    }
}


# 인덱스 생성 스키마 목록
INDEX_SCHEMAS = {
    INDEX_DOCUMENTS: DOCUMENTS_MAPPING,
    INDEX_SESSIONS: SESSIONS_MAPPING,
}
