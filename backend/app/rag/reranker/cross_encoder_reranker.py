"""Cross-Encoder 기반 랭커.

BAAI/bge-reranker-v2-m3 모델 사용 (다국어 지원)
"""

import torch
from typing import List, Optional

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError:
    AutoModelForSequenceClassification = None
    AutoTokenizer = None


class CrossEncoderReranker:
    """Cross-Encoder 랭커.
    
    Stage 1: Dense Vector Search (Fast) → Top-K 문서
    Stage 2: Cross-Encoder Reranker (Slow, Precision-focused) → Top-N 문서
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """모델과 토크나이저를 로드합니다 (지연 초기화)."""
        if AutoModelForSequenceClassification is None or AutoTokenizer is None:
            raise ImportError(
                "transformers가 설치되어 있지 않습니다. "
                "pip install transformers torch"
            )

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        self._model.eval()

    def rerank(
        self,
        query: str,
        documents: List[dict],
        top_n: int = 5,
    ) -> List[dict]:
        """Cross-Encoder로 문서를 재랭킹합니다.
        
        Args:
            query: 검색 쿼리
            documents: 문서 리스트 (document_id, content 포함)
            top_n: 반환할 결과 수
            
        Returns:
            점수 내림차순 정렬된 문서 리스트
        """
        if self._model is None:
            self._load_model()

        # 쿼리-문서 쌍 생성
        pairs = [(query, doc["content"]) for doc in documents]

        # 토큰화
        inputs = self._tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        # 점수 예측
        with torch.no_grad():
            outputs = self._model(**inputs)
            scores = outputs.logits.squeeze().tolist()

        # 문서에 점수 추가 및 정렬
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = round(score, 4)

        ranked = sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_n]
