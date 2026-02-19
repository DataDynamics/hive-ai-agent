from openai import OpenAI
from config import OLLAMA_BASE_URL, RAG_EMBEDDING_MODEL


class Embedder:
    def __init__(self):
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        self.model = RAG_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in sorted(response.data, key=lambda x: x.index)]
