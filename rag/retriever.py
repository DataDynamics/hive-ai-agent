"""
rag/retriever.py
----------------
RAG(Retrieval-Augmented Generation)의 핵심 검색 모듈.

Embedder와 VectorStore를 조합하여 다음 기능을 제공한다:
    - 초기화 시 pgvector 테이블이 비어 있으면 자동으로 지식 기반 인덱싱
    - 사용자 질의를 임베딩하여 유사 문서 검색
    - 필요 시 인덱스 재구축

일반적인 사용 흐름:
    retriever = RAGRetriever()       # 초기화 (필요 시 자동 인덱싱)
    context = retriever.retrieve(q)  # 질의와 유사한 문서 반환
    retriever.close()                # 연결 종료
"""

from rag.document_loader import load_knowledge_base
from rag.embedder import Embedder
from rag.vectorstore import VectorStore
from config import RAG_COLLECTION_NAME, RAG_KNOWLEDGE_DIR, RAG_N_RESULTS


class RAGRetriever:
    """지식 기반 문서를 검색하여 LLM 컨텍스트를 제공하는 검색기."""

    def __init__(self):
        # 텍스트 → 벡터 변환 담당 (Ollama 임베딩 모델 사용)
        self.embedder = Embedder()
        # pgvector 벡터 저장소 연결
        self.vectorstore = VectorStore(RAG_COLLECTION_NAME)

        # 테이블이 비어 있으면 knowledge 디렉토리의 문서를 자동 인덱싱
        # 최초 실행 시 또는 테이블이 초기화된 경우에 해당
        if self.vectorstore.count() == 0:
            self._build_index()

    def _build_index(self):
        """knowledge 디렉토리의 JSON 문서를 읽어 pgvector에 인덱싱한다.

        문서 텍스트를 일괄 임베딩하여 VectorStore에 upsert한다.
        인덱싱 완료 후 처리된 문서 수를 출력한다.
        """
        # JSON 파일에서 문서 목록 로드
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        # 모든 문서 텍스트를 한 번의 API 호출로 일괄 임베딩
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        # 문서와 임베딩을 pgvector 테이블에 저장
        self.vectorstore.upsert(docs, embeddings)
        print(f"  [RAG] {len(docs)}개 문서를 인덱싱했습니다.")

    def rebuild_index(self):
        """인덱스를 강제로 재구축한다.

        knowledge 디렉토리의 문서가 수정된 경우 호출하여
        pgvector 테이블의 내용을 최신 상태로 갱신한다.
        기존 문서는 id 기준으로 upsert되므로 중복 없이 갱신된다.
        """
        docs = load_knowledge_base(RAG_KNOWLEDGE_DIR)
        embeddings = self.embedder.embed_batch([d["text"] for d in docs])
        self.vectorstore.upsert(docs, embeddings)
        print(f"  [RAG] 인덱스를 재구축했습니다. ({len(docs)}개 문서)")

    def retrieve(self, query: str) -> str:
        """사용자 질의와 유사한 문서를 검색하여 하나의 문자열로 반환한다.

        질의를 임베딩한 후 코사인 유사도 기준으로 가장 관련성 높은
        문서를 RAG_N_RESULTS 개만큼 검색하고, 빈 줄로 구분하여 합친다.

        Args:
            query: 사용자가 입력한 자연어 질의 문자열

        Returns:
            유사 문서들을 "\n\n"으로 연결한 단일 문자열.
            agent.py에서 LLM 입력의 컨텍스트 섹션으로 사용된다.
        """
        # 질의 텍스트를 벡터로 변환
        query_embedding = self.embedder.embed(query)
        # 코사인 유사도 기준으로 상위 N개 문서 검색
        docs = self.vectorstore.query(query_embedding, RAG_N_RESULTS)
        # 여러 문서를 빈 줄로 구분하여 하나의 문자열로 합침
        return "\n\n".join(docs)

    def close(self):
        """pgvector(PostgreSQL) 연결을 닫는다.

        HiveAgent.close()에서 호출되며, 프로그램 종료 시 반드시 실행된다.
        """
        self.vectorstore.close()
