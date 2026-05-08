"""Sentence-Transformers 기반 임베딩 모델."""

from typing import List, Optional

import torch
from sentence_transformers import SentenceTransformer as ST
from openai import OpenAI

from app.rag.embeddings.base import BaseEmbeddingModel
from app.rag.config import settings


class SentenceTransformerEmbeddings(BaseEmbeddingModel):
    """Sentence-Transformers를 사용한 임베딩 모델.
    
    한국어 다국어 파이프라인 지원 (paraphrase-multilingual-MiniLM-L12-v2)
    LMStudio API 또는 로컬 모델 사용 가능
    """

    _instance: Optional["SentenceTransformerEmbeddings"] = None
    _model: Optional[object] = None

    def __init__(self, model_name=None):
        self.model_name = model_name or settings.embedding_model_name
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._batch_size = 32 if self._device == "cuda" else 8
        
        # LMStudio API 사용 여부 확인 (API URL이 설정되어 있으면 API 모드)
        api_url = getattr(settings, 'embedding_api_url', None)
        if api_url:
            self._use_api = True
            self._api_client = OpenAI(
                base_url=api_url,
                api_key="lm-studio",
            )
            self._api_model = settings.embedding_model_name
        else:
            self._use_api = False

    @classmethod
    def get_instance(cls, model_name=None):
        """싱글톤 인스턴스 반환."""
        if cls._instance is None or model_name is not None:
            cls._instance = cls(model_name)
        return cls._instance

    def _get_model(self):
        """모델 로딩 (지연 초기화)."""
        if self._model is None and not self._use_api:
            self._model = ST(
                self.model_name,
                device=self._device,
            )
        return self._model

    @property
    def dimension(self):
        """임베딩 차원."""
        if self._use_api:
            # API 모드는 고정 차원 (BGE-M3는 1024)
            return 1024
        model = self._get_model()
        return model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서를 배치 임베딩합니다."""
        if self._use_api:
            # LMStudio API를 사용한 배치 임베딩
            response = self._api_client.embeddings.create(
                model=self._api_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        
        model = self._get_model()
        
        embeddings = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_emb = model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_emb.tolist())

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """쿼리 텍스트를 임베딩합니다."""
        if self._use_api:
            response = self._api_client.embeddings.create(
                model=self._api_model,
                input=[text],
            )
            return response.data[0].embedding
        
        model = self._get_model()
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
