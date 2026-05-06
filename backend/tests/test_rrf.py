"""RRF (Reciprocal Rank Fusion) 테스트."""

import pytest
from app.rag.search.rrf import rrf_combine, rrf_combine_with_scores


class TestRRFCombine:
    """rrf_combine 함수 테스트."""

    def test_basic_rrf(self):
        """기본 RRF 동작 검증."""
        results = [
            [{"id": "doc1"}, {"id": "doc2"}],  # doc1=rank1, doc2=rank2
            [{"id": "doc2"}, {"id": "doc3"}],  # doc2=rank1, doc3=rank1
        ]

        fused = rrf_combine(results, k=60)

        # doc2가 두 검색에서 모두 등장하므로 가장 높은 점수
        assert len(fused) == 3
        assert fused[0][0] == "doc2"  # doc2가 1등
        assert fused[0][1] > fused[1][1]  # 첫 번째가 두 번째보다 점수가 높음

    def test_single_result(self):
        """단일 검색 결과."""
        results = [[{"id": "doc1"}, {"id": "doc2"}]]
        fused = rrf_combine(results, k=60)

        assert len(fused) == 2
        assert fused[0][0] == "doc1"  # rank 1이 더 높음

    def test_empty_results(self):
        """빈 결과."""
        results = []
        fused = rrf_combine(results, k=60)
        assert len(fused) == 0

    def test_k_parameter(self):
        """k 파라미터가 점수에 영향 미치는지 검증."""
        results = [[{"id": "doc1"}]]

        fused_k60 = rrf_combine(results, k=60)
        fused_k30 = rrf_combine(results, k=30)

        # k가 작을수록 점수가 높아짐 (1/(k+rank))
        assert fused_k30[0][1] > fused_k60[0][1]


class TestRRFCombineWithScores:
    """rrf_combine_with_scores 함수 테스트."""

    def test_returns_dicts(self):
        """Dict 리스트를 반환하는지 검증."""
        results = [
            [{"id": "doc1", "content": "test1"}],
            [{"id": "doc2", "content": "test2"}],
        ]

        fused = rrf_combine_with_scores(results)

        assert len(fused) == 2
        assert "rrf_score" in fused[0]
        assert isinstance(fused[0]["rrf_score"], float)


class TestRRFEdgeCases:
    """RRF 경계 케이스 테스트."""

    def test_duplicate_documents(self):
        """동일 문서가 여러 검색에 등장하는 경우."""
        results = [
            [{"id": "doc1"}, {"id": "doc2"}],
            [{"id": "doc1"}, {"id": "doc3"}],
        ]

        fused = rrf_combine(results, k=60)

        # doc1이 두 검색에서 모두 등장하므로 1등
        assert fused[0][0] == "doc1"

    def test_no_overlap(self):
        """중복 없는 문서들."""
        results = [
            [{"id": "doc1"}, {"id": "doc2"}],
            [{"id": "doc3"}, {"id": "doc4"}],
        ]

        fused = rrf_combine(results, k=60)
        assert len(fused) == 4
