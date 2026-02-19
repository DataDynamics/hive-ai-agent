from rag.document_loader import load_knowledge_base
from rag.embedder import Embedder
from rag.vectorstore import VectorStore
from config import RAG_COLLECTION_NAME, RAG_KNOWLEDGE_DIR, RAG_N_RESULTS


class RAGRetriever:
    def __init__(self):
        self.embedder = Embedder()
        self.vectorstore = VectorStore(RAG_COLLECTION_NAME)
        if self.vectorstore.count() == 0:
            self._build_index()

    def _build_index(self):
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        self.vectorstore.upsert(docs, embeddings)
        print(f"  [RAG] {len(docs)}개 문서를 인덱싱했습니다.")

    def rebuild_index(self):
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        self.vectorstore.upsert(docs, embeddings)
        print(f"  [RAG] 인덱스를 재구축했습니다. ({len(docs)}개 문서)")

    def retrieve(self, query: str) -> str:
        query_embedding = self.embedder.embed(query)
        docs = self.vectorstore.query(query_embedding, RAG_N_RESULTS)
        return "\n\n".join(docs)

    def close(self):
        self.vectorstore.close()
