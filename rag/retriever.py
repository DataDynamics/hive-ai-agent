"""
rag/retriever.py
----------------
RAG(Retrieval-Augmented Generation)의 핵심 검색 모듈.
"""

import logging
from rag.document_loader import load_knowledge_base
from rag.embedder import Embedder
from rag.vectorstore import VectorStore
from config import RAG_COLLECTION_NAME, RAG_KNOWLEDGE_DIR, RAG_N_RESULTS

logger = logging.getLogger(__name__)


class RAGRetriever:
    """지식 기반 문서를 검색하여 LLM 컨텍스트를 제공하는 검색기."""

    def __init__(self):
        logger.info("RAGRetriever 초기화 시작")
        self.embedder = Embedder()
        self.vectorstore = VectorStore(RAG_COLLECTION_NAME)

        # 테이블이 비어 있으면 knowledge 디렉토리 자동 인덱싱
        count = self.vectorstore.count()
        if count == 0:
            logger.info("인덱스가 비어 있음 — 자동 인덱싱 시작")
            self._build_index()
        else:
            logger.info("기존 인덱스 사용 — %d 건 로드됨", count)

    def _build_index(self):
        """knowledge 디렉토리의 JSON 문서를 읽어 pgvector에 인덱싱한다."""
        logger.info("인덱스 구축 시작 — knowledge_dir=%s", RAG_KNOWLEDGE_DIR)
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        self.vectorstore.upsert(docs, embeddings)
        logger.info("인덱스 구축 완료 — %d 개 문서 인덱싱됨", len(docs))
        print(f"  [RAG] {len(docs)}개 문서를 인덱싱했습니다.")

    def rebuild_index(self):
        """인덱스를 강제로 재구축한다."""
        logger.info("인덱스 재구축 시작")
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        self.vectorstore.upsert(docs, embeddings)
        logger.info("인덱스 재구축 완료 — %d 개 문서", len(docs))
        print(f"  [RAG] 인덱스를 재구축했습니다. ({len(docs)}개 문서)")

    def retrieve(self, query: str) -> str:
        """사용자 질의와 유사한 문서를 검색하여 하나의 문자열로 반환한다.

        Args:
            query: 사용자가 입력한 자연어 질의 문자열

        Returns:
            유사 문서들을 "\\n\\n"으로 연결한 단일 문자열
        """
        logger.debug("문서 검색 시작 — query=%s", query[:50])
        query_embedding = self.embedder.embed(query)
        docs = self.vectorstore.query(query_embedding, RAG_N_RESULTS)
        logger.info("문서 검색 완료 — %d 건 반환", len(docs))
        return "\n\n".join(docs)

    def close(self):
        """pgvector(PostgreSQL) 연결을 닫는다."""
        self.vectorstore.close()
        logger.info("RAGRetriever 연결 종료")
