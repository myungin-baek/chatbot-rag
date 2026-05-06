"""RRF (Reciprocal Rank Fusion) 알고리즘 구현."""

from typing import Dict, List, Tuple


def rrf_combine(
    results: List[List[Dict]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """RRF 알고리즘으로 여러 검색 결과의 순위를 결합합니다.
    
    공식: score = Σ (1 / (k + rank_i))
    
    Args:
        results: 각 검색 엔진에서 반환된 결과 리스트 (각각은 document_id 목록)
        k: RRF 상수 (기본 60)
        
    Returns:
        (document_id, fused_score) 튜플의 내림차순 정렬 리스트
        
    Example:
        >>> dense_results = [{"id": "doc1"}, {"id": "doc2"}]
        >>> bm25_results = [{"id": "doc2"}, {"id": "doc3"}]
        >>> rrf_combine([dense_results, bm25_results])
        [('doc2', 0.033), ('doc1', 0.016), ('doc3', 0.016)]
    """
    score_map: Dict[str, float] = {}

    for result_set in results:
        for rank, doc in enumerate(result_set, start=1):
            # document_id 추출 (문서에 따라 다양한 키 가능)
            doc_id = doc.get("id") or doc.get("_id") or str(doc)
            
            if doc_id not in score_map:
                score_map[doc_id] = 0.0
            score_map[doc_id] += 1 / (k + rank - 1)

    # 점수 내림차순 정렬
    sorted_results = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


def rrf_combine_with_scores(
    results: List[List[Dict]],
    k: int = 60,
) -> List[Dict]:
    """RRF 결합 결과를 정렬된 Dict 리스트로 반환합니다."""
    fused = rrf_combine(results, k)
    
    # 결과에서 원본 문서 정보 찾기
    all_docs = {}
    for result_set in results:
        for doc in result_set:
            doc_id = doc.get("id") or doc.get("_id") or str(doc)
            if doc_id not in all_docs:
                all_docs[doc_id] = dict(doc)

    ranked_results = []
    for doc_id, score in fused:
        if doc_id in all_docs:
            result = dict(all_docs[doc_id])
            result["rrf_score"] = round(score, 6)
            ranked_results.append(result)

    return ranked_results
