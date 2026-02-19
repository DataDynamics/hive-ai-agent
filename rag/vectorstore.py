"""
rag/vectorstore.py
------------------
pgvector(PostgreSQL 벡터 확장)를 사용하는 벡터 저장소 모듈.
"""

import json
import logging
import psycopg2
from psycopg2 import sql
from pgvector.psycopg2 import register_vector
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, RAG_EMBEDDING_DIM

logger = logging.getLogger(__name__)


class VectorStore:
    """pgvector 기반 벡터 저장소 클래스."""

    def __init__(self, collection_name: str):
        """
        Args:
            collection_name: 문서가 저장될 PostgreSQL 테이블 이름
        """
        self.table = collection_name
        logger.info(
            "PostgreSQL 연결 시도 — host=%s, port=%s, db=%s, table=%s",
            PG_HOST, PG_PORT, PG_DATABASE, self.table,
        )
        self.conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
        )
        register_vector(self.conn)
        logger.info("PostgreSQL 연결 성공")
        self._init_table()

    def _init_table(self):
        """vector 확장을 활성화하고 문서 테이블을 생성한다."""
        logger.debug("테이블 초기화 시작 — table=%s, dim=%d", self.table, RAG_EMBEDDING_DIM)
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id        TEXT PRIMARY KEY,
                    document  TEXT NOT NULL,
                    metadata  JSONB,
                    embedding vector({dim})
                )
            """).format(
                sql.Identifier(self.table),
                dim=sql.Literal(RAG_EMBEDDING_DIM)
            ))
        self.conn.commit()
        logger.info("테이블 초기화 완료 — table=%s", self.table)

    def upsert(self, docs: list[dict], embeddings: list[list[float]]):
        """문서와 임베딩 벡터를 테이블에 삽입하거나 갱신한다.

        Args:
            docs: 문서 딕셔너리 리스트 ("id", "text", "metadata" 키 포함)
            embeddings: docs와 같은 순서의 임베딩 벡터 리스트
        """
        logger.info("upsert 시작 — %d 건", len(docs))
        with self.conn.cursor() as cur:
            for doc, emb in zip(docs, embeddings):
                cur.execute(
                    sql.SQL("""
                        INSERT INTO {} (id, document, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document  = EXCLUDED.document,
                            metadata  = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """).format(sql.Identifier(self.table)),
                    (
                        doc["id"],
                        doc["text"],
                        json.dumps(doc.get("metadata", {})),
                        emb
                    )
                )
        self.conn.commit()
        logger.info("upsert 완료 — %d 건 저장됨", len(docs))

    def query(self, query_embedding: list[float], n_results: int = 3) -> list[str]:
        """쿼리 벡터와 코사인 유사도가 높은 문서를 반환한다.

        Args:
            query_embedding: 사용자 입력을 임베딩한 벡터
            n_results: 반환할 최대 문서 수

        Returns:
            유사도 순으로 정렬된 문서 텍스트 리스트
        """
        logger.debug("벡터 검색 실행 — n_results=%d", n_results)
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    SELECT document
                    FROM {}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """).format(sql.Identifier(self.table)),
                (query_embedding, n_results)
            )
            results = [row[0] for row in cur.fetchall()]
        logger.debug("벡터 검색 완료 — %d 건 반환", len(results))
        return results

    def count(self) -> int:
        """테이블에 저장된 문서 수를 반환한다."""
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.table))
            )
            cnt = cur.fetchone()[0]
        logger.debug("문서 수 조회 — table=%s, count=%d", self.table, cnt)
        return cnt

    def close(self):
        """PostgreSQL 연결을 닫는다."""
        self.conn.close()
        logger.info("PostgreSQL 연결 종료")
