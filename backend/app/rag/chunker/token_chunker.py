"""토큰 기반 청킹 모듈.

500 토큰 기준 + 50 토큰 오버랩 전략 구현.
"""

from typing import List, Optional


class TokenChunker:
    """토큰 기반 문서 청커.
    
    - chunk_size: 500 토큰 (기본)
    - overlap: 50 토큰 (인접 청크 간 중복)
    - min_chunk_size: 100 토큰 (이보다 작은 청크는 병합)
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        min_chunk_size: Optional[int] = None,
        tokenizer_name: Optional[str] = None,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # min_chunk_size 미설정 시 chunk_size의 20%로 자동 계산
        if min_chunk_size is None:
            self.min_chunk_size = max(1, chunk_size // 5)
        else:
            self.min_chunk_size = min_chunk_size

        # 토크나이저 설정 (없으면 단순 단어 기반 분할)
        try:
            from transformers import AutoTokenizer
            if tokenizer_name:
                self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
                self._use_tokenizer = True
            else:
                self._use_tokenizer = False
        except ImportError:
            self._use_tokenizer = False

    def chunk(self, text: str) -> List[str]:
        """텍스트를 청크로 분할합니다."""
        if not text.strip():
            return []

        # 1. 문단 단위로 먼저 분할
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            para_word_count = len(para.split())
            chunk_word_count = len(current_chunk.split()) if current_chunk else 0

            # 청크가 가득 찼으면 저장
            if chunk_word_count + para_word_count > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())

                # 오버랩 적용 (단어 단위)
                if self.overlap > 0 and chunks:
                    words = chunks[-1].split()
                    overlap_words = words[-self.overlap:] if len(words) >= self.overlap else words
                    current_chunk = " ".join(overlap_words) + " " + para
                else:
                    current_chunk = para
            else:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 2. chunk_size를 초과하는 청크를 단어 단위로 분할 (핵심 수정)
        chunks = [self._split_if_too_large(c) for c in chunks]
        flattened = []
        for c in chunks:
            if isinstance(c, list):
                flattened.extend(c)
            else:
                flattened.append(c)
        chunks = flattened

        # 3. 최소 크기보다 작은 청크 병합
        return self._merge_small_chunks(chunks)

    def _split_if_too_large(self, text: str) -> List[str]:
        """chunk_size를 초과하는 텍스트를 단어 단위로 분할."""
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]

        result = []
        for i in range(0, len(words), self.chunk_size - self.overlap):
            end = min(i + self.chunk_size, len(words))
            chunk = " ".join(words[i:end])
            if chunk.strip():
                result.append(chunk)
        return result

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """최소 크기보다 작은 청크를 이전 청크에 병합합니다."""
        if not chunks or len(chunks) <= 1:
            return chunks

        merged = []
        for chunk in chunks:
            word_count = len(chunk.split())
            if word_count < self.min_chunk_size and merged:
                # 이전 청크에 병합
                merged[-1] = f"{merged[-1]}\n\n{chunk}"
            else:
                merged.append(chunk)

        return merged
