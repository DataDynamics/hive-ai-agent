"""
rag/embedder.py
---------------
Ollama 임베딩 엔드포인트를 통해 텍스트를 벡터로 변환하는 모듈.
"""

import logging
from openai import OpenAI
from config import OLLAMA_BASE_URL, RAG_EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class Embedder:
    """Ollama 임베딩 모델을 사용하여 텍스트를 벡터로 변환하는 클래스."""

    def __init__(self):
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        self.model = RAG_EMBEDDING_MODEL
        logger.debug("Embedder 초기화 완료 (model=%s)", self.model)

    def embed(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다.

        Args:
            text: 임베딩할 텍스트 문자열

        Returns:
            임베딩 벡터 (float 리스트)
        """
        logger.debug("단일 임베딩 요청 (length=%d)", len(text))
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트를 한 번의 API 호출로 일괄 임베딩한다.

        Args:
            texts: 임베딩할 텍스트 문자열 리스트

        Returns:
            각 텍스트에 대응하는 임베딩 벡터 리스트 (입력 순서 보장)
        """
        logger.info("배치 임베딩 요청 — %d 건", len(texts))
        response = self.client.embeddings.create(model=self.model, input=texts)
        # 응답이 입력 순서를 보장하지 않을 수 있으므로 index 기준 정렬
        result = [d.embedding for d in sorted(response.data, key=lambda x: x.index)]
        logger.debug("배치 임베딩 완료 — %d 건", len(result))
        return result
