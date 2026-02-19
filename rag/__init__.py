"""
rag/__init__.py
---------------
RAG(Retrieval-Augmented Generation) 패키지 초기화 모듈.

외부에서 `from rag import RAGRetriever` 형태로 간결하게 임포트할 수 있도록
RAGRetriever를 패키지 공개 인터페이스로 노출한다.
"""

from rag.retriever import RAGRetriever

# 패키지 공개 API — `from rag import *` 시 노출할 심볼 목록
__all__ = ["RAGRetriever"]
