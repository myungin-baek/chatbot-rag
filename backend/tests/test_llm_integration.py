"""LLM 연동 E2E 테스트 - LMStudio 서버와 실제 통신."""

import pytest
from openai import OpenAI


class TestLMStudioIntegration:
    """LMStudio API 연결 테스트."""

    @pytest.fixture
    def llm_client(self):
        from app.rag.llm.llm_client import LLMClient
        return LLMClient.get_instance()

    @pytest.fixture
    def openai_client(self):
        return OpenAI(
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
        )

    def test_models_list(self, openai_client):
        """LMStudio에서 사용 가능한 모델 목록 조회."""
        response = openai_client.models.list()
        models = [m.id for m in response.data]
        
        assert len(models) > 0, "LMStudio에 로드된 모델이 없습니다."
        print(f"사용 가능한 모델: {models}")

    def test_chat_completion(self, llm_client):
        """LLM 응답 생성 테스트."""
        result = llm_client.generate(
            prompt="안녕하세요. 간단한 자기소개를 해주세요.",
            system_prompt="너는 한국어로 답변하는 AI 어시스턴트입니다.",
            max_tokens=100,
        )
        
        assert result is not None
        assert len(result) > 0
        print(f"응답: {result}")

    def test_chat_completion_stream(self, llm_client):
        """LLM 스트리밍 응답 테스트."""
        tokens = []
        for token in llm_client.generate_stream(
            prompt="1부터 5까지 숫자를 나열해주세요.",
            max_tokens=100,
        ):
            tokens.append(token)
        
        full_response = "".join(tokens)
        assert len(full_response) > 0
        print(f"스트리밍 응답: {full_response}")

    def test_rag_generation(self, llm_client):
        """RAG 기반 응답 생성 테스트 (컨텍스트 없음)."""
        result = llm_client.generate_with_context(
            query="안녕하세요. RAG 시스템에 대해 설명해주세요.",
            context_documents=[],
            max_tokens=200,
        )
        
        assert result is not None
        print(f"RAG 응답: {result}")


class TestEmbeddingIntegration:
    """임베딩 API 연결 테스트."""

    @pytest.fixture
    def embedding_model(self):
        from app.rag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
        return SentenceTransformerEmbeddings.get_instance()

    def test_embed_query(self, embedding_model):
        """쿼리 임베딩 테스트."""
        text = "안녕하세요"
        vector = embedding_model.embed_query(text)
        
        assert len(vector) == 1024, f"예상 차원: 1024, 실제: {len(vector)}"
        # 벡터 정규화 확인 (L2 norm ≈ 1.0)
        import math
        norm = math.sqrt(sum(v * v for v in vector))
        assert abs(norm - 1.0) < 0.01, f"L2 norm이 1.0에 가까워야 합니다: {norm}"
        print(f"임베딩 차원: {len(vector)}, L2 norm: {norm:.4f}")

    def test_embed_documents(self, embedding_model):
        """배치 임베딩 테스트."""
        texts = [
            "안녕하세요",
            "오늘 날씨가 좋네요.",
            "RAG 시스템은 검색 증강 생성입니다.",
        ]
        vectors = embedding_model.embed_documents(texts)
        
        assert len(vectors) == 3
        for i, v in enumerate(vectors):
            assert len(v) == 1024
        print(f"배치 임베딩 완료: {len(vectors)}개 문서")

    def test_similarity(self, embedding_model):
        """유사도 계산 테스트."""
        import math
        
        similar = embedding_model.embed_query("안녕하세요 반갑습니다.")
        dissimilar = embedding_model.embed_query("오늘 점심 메뉴 추천해줘.")
        
        # 코사인 유사도 계산
        def cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            return dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0
        
        # "안녕하세요"와 유사한 문장이 더 높은 유사도를 가져야 함
        base = embedding_model.embed_query("안녕하세요")
        
        sim1 = cosine_similarity(base, similar)
        sim2 = cosine_similarity(base, dissimilar)
        
        print(f"'안녕하세요' vs '안녕하세요 반갑습니다.': {sim1:.4f}")
        print(f"'안녕하세요' vs '오늘 점심 메뉴 추천해줘.': {sim2:.4f}")
        
        assert sim1 > sim2, "유사한 문장이 더 높은 유사도를 가져야 합니다."


class TestOpenSearchIntegration:
    """OpenSearch 연결 테스트."""

    @pytest.fixture
    def os_client(self):
        from app.rag.search.opensearch_engine import OpenSearchEngine
        from app.rag.config import settings
        
        return OpenSearchEngine(
            host=settings.opensearch_host,
            port=settings.opensearch_port,
            scheme=settings.opensearch_scheme,
            username=settings.opensearch_username,
            password=settings.opensearch_password,
        )

    def test_connection(self, os_client):
        """OpenSearch 연결 확인."""
        info = os_client.get_info()
        assert "version" in info
        print(f"OpenSearch 버전: {info['version']['number']}")

    def test_index_exists(self, os_client):
        """인덱스 존재 여부 확인."""
        exists = os_client.index_exists("chatbot_documents")
        if not exists:
            pytest.skip("chatbot_documents 인덱스가 없습니다. 먼저 문서를 업로드하세요.")


class TestFullPipelineE2E:
    """전체 파이프라인 E2E 테스트."""

    def test_chat_api(self):
        """채팅 API 호출 테스트 (REST)."""
        import requests
        
        # 로그인
        login_resp = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        
        if login_resp.status_code != 200:
            pytest.skip("로그인 실패. admin 계정이 설정되어 있지 않습니다.")
        
        token = login_resp.json()["access_token"]
        
        # 채팅 요청
        chat_resp = requests.post(
            "http://localhost:8000/api/v1/chat/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "안녕하세요. RAG 시스템에 대해 설명해주세요.",
                "session_id": None,
            },
        )
        
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "content" in data
        print(f"채팅 응답: {data['content'][:100]}...")
