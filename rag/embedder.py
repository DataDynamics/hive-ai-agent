"""
rag/embedder.py
---------------
Ollama 임베딩 엔드포인트를 통해 텍스트를 벡터로 변환하는 모듈.

Ollama의 OpenAI 호환 /v1/embeddings API를 사용하며,
config.yaml에 지정된 임베딩 모델(기본값: nomic-embed-text)로
텍스트를 고정 차원의 부동소수점 벡터로 변환한다.

사전 준비:
    ollama pull nomic-embed-text
"""

from openai import OpenAI
from config import OLLAMA_BASE_URL, RAG_EMBEDDING_MODEL


class Embedder:
    """Ollama 임베딩 모델을 사용하여 텍스트를 벡터로 변환하는 클래스."""

    def __init__(self):
        # Ollama의 OpenAI 호환 엔드포인트에 연결
        # api_key는 Ollama에서 사용하지 않지만 SDK 형식상 필요
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        # 사용할 임베딩 모델 이름 (예: nomic-embed-text, mxbai-embed-large)
        self.model = RAG_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다.

        Args:
            text: 임베딩할 텍스트 문자열

        Returns:
            임베딩 벡터 (float 리스트, 차원 수는 모델에 따라 결정)
        """
        response = self.client.embeddings.create(model=self.model, input=text)
        # 단일 입력이므로 첫 번째 결과만 반환
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트를 한 번의 API 호출로 일괄 임베딩한다.

        단건 호출보다 효율적이며, 응답의 index 기준으로 입력 순서를 보장한다.

        Args:
            texts: 임베딩할 텍스트 문자열 리스트

        Returns:
            각 텍스트에 대응하는 임베딩 벡터 리스트 (입력 순서 보장)
        """
        response = self.client.embeddings.create(model=self.model, input=texts)
        # API 응답이 입력 순서를 보장하지 않을 수 있으므로 index 기준 정렬
        return [d.embedding for d in sorted(response.data, key=lambda x: x.index)]
