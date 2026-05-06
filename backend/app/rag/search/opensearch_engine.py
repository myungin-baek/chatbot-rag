"""OpenSearch 기반 검색 엔진."""

from typing import List, Optional

try:
    from opensearchpy import OpenSearch
except ImportError:
    OpenSearch = None


class OpenSearchEngine:
    """OpenSearch 클라이언트 래퍼.
    
    Dense Vector (k-NN) + BM25 Hybrid 검색 지원
    """

    def __init__(self, host: str, port: int, scheme: str, username: str, password: str):
        if OpenSearch is None:
            raise ImportError("opensearch-py가 설치되어 있지 않습니다. pip install opensearch-py")

        self.client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=(username, password),
            scheme=scheme,
        )
        self._index_prefix = "chatbot"

    def health_check(self) -> dict:
        """OpenSearch 헬스체크."""
        return self.client.cluster.health()

    def create_index(self, index_name: str, mapping: dict) -> bool:
        """인덱스를 생성합니다 (이미 존재하면 건너뜀)."""
        if not self.client.indices.exists(index=index_name):
            body = {
                "mappings": mapping.get("mappings", {}),
                "settings": mapping.get("settings", {}),
            }
            self.client.indices.create(index=index_name, body=body)
            return True
        return False

    def index_document(self, index_name: str, doc_id: str, document: dict) -> bool:
        """문서를 인덱스에 추가합니다."""
        self.client.index(index=index_name, id=doc_id, body=document)
        return True

    def search_dense_vector(
        self,
        index_name: str,
        query_vector: List[float],
        k: int = 10,
        filter_condition: Optional[dict] = None,
    ) -> dict:
        """Dense Vector (k-NN) 검색."""
        body = {
            "size": k,
            "_source": True,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": k,
                    }
                }
            },
        }

        if filter_condition:
            body["query"] = {
                "bool": {
                    "must": [{"knn": {"embedding": {"vector": query_vector, "k": k}}}],
                    "filter": [filter_condition],
                }
            }

        return self.client.search(index=index_name, body=body)

    def search_bm25(self, index_name: str, query_text: str, k: int = 10) -> dict:
        """BM25 키워드 검색."""
        body = {
            "size": k,
            "_source": True,
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["content", "title"],
                    "fuzziness": "AUTO",
                }
            },
        }
        return self.client.search(index=index_name, body=body)

    def search_hybrid(
        self,
        index_name: str,
        query_text: str,
        query_vector: List[float],
        k: int = 10,
    ) -> dict:
        """Hybrid 검색 (Dense Vector + BM25 결합)."""
        body = {
            "size": k,
            "_source": True,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content": query_text}},
                        {"knn": {"embedding": {"vector": query_vector, "k": k}}},
                    ],
                    "boosting": {
                        "positive": [{"match": {"content": query_text}}],
                        "negative": [{"knn": {"embedding": {"vector": query_vector, "k": k * 2}}}],
                        "negative_boost": 0.5,
                    },
                }
            },
        }
        return self.client.search(index=index_name, body=body)

    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """문서를 인덱스에서 삭제합니다."""
        self.client.delete(index=index_name, id=doc_id)
        return True

    def index_exists(self, index_name: str) -> bool:
        """인덱스가 존재하는지 확인합니다."""
        return self.client.indices.exists(index=index_name)

    def delete_index(self, index_name: str) -> bool:
        """인덱스를 삭제합니다."""
        if self.client.indices.exists(index=index_name):
            self.client.indices.delete(index=index_name)
            return True
        return False

    def delete_documents_by_filter(self, index_name: str, query: dict) -> dict:
        """조건에 맞는 문서를 일괄 삭제합니다."""
        body = {
            "query": query,
        }
        return self.client.delete_by_query(index=index_name, body=body)
