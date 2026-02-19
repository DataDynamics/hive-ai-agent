"""
rag/vectorstore.py
------------------
pgvector(PostgreSQL 벡터 확장)를 사용하는 벡터 저장소 모듈.

주요 기능:
    - PostgreSQL에 vector 확장 및 문서 테이블 자동 생성
    - 문서와 임베딩 벡터를 upsert(삽입 또는 갱신)
    - 코사인 유사도(<=> 연산자)를 기준으로 유사 문서 검색
    - 저장된 문서 수 조회

테이블 구조:
    id        TEXT PRIMARY KEY    -- 문서 고유 식별자
    document  TEXT NOT NULL       -- 원문 텍스트
    metadata  JSONB               -- 추가 메타데이터
    embedding vector(N)           -- N차원 임베딩 벡터
"""

import json
import psycopg2
from psycopg2 import sql
from pgvector.psycopg2 import register_vector
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, RAG_EMBEDDING_DIM


class VectorStore:
    """pgvector 기반 벡터 저장소 클래스.

    초기화 시 PostgreSQL에 연결하고, vector 확장 및 문서 테이블이
    없으면 자동으로 생성한다.
    """

    def __init__(self, collection_name: str):
        """
        Args:
            collection_name: 문서가 저장될 PostgreSQL 테이블 이름.
                             config.yaml의 rag.collection_name 값을 사용한다.
        """
        # 문서가 저장될 테이블 이름
        self.table = collection_name

        # PostgreSQL 서버에 연결
        self.conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
        )

        # psycopg2 커넥션에 pgvector 타입 지원 등록
        # 이를 통해 Python list를 vector 타입으로 자동 변환
        register_vector(self.conn)

        # vector 확장 및 테이블 초기화
        self._init_table()

    def _init_table(self):
        """vector 확장을 활성화하고 문서 테이블을 생성한다.

        테이블과 확장이 이미 존재하면 건너뛴다(IF NOT EXISTS).
        임베딩 벡터의 차원 수는 config의 RAG_EMBEDDING_DIM 값을 사용한다.
        """
        with self.conn.cursor() as cur:
            # pgvector 확장 활성화 (최초 1회, superuser 권한 필요)
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # 문서 저장 테이블 생성
            # sql.Identifier로 테이블명을 안전하게 처리하여 SQL 인젝션 방지
            cur.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id        TEXT PRIMARY KEY,
                    document  TEXT NOT NULL,
                    metadata  JSONB,
                    embedding vector({dim})
                )
            """).format(
                sql.Identifier(self.table),       # 테이블명을 식별자로 안전하게 삽입
                dim=sql.Literal(RAG_EMBEDDING_DIM) # 벡터 차원 수
            ))
        self.conn.commit()

    def upsert(self, docs: list[dict], embeddings: list[list[float]]):
        """문서와 임베딩 벡터를 테이블에 삽입하거나 갱신한다.

        동일한 id가 이미 존재하면 document, metadata, embedding을 갱신한다.
        (INSERT ... ON CONFLICT DO UPDATE)

        Args:
            docs: 문서 딕셔너리 리스트. 각 항목은 "id", "text", "metadata" 키를 가진다.
            embeddings: docs와 같은 순서의 임베딩 벡터 리스트.
        """
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
                        json.dumps(doc.get("metadata", {})),  # dict → JSONB 문자열
                        emb                                    # list → vector 타입
                    )
                )
        # 모든 upsert 완료 후 한 번에 커밋
        self.conn.commit()

    def query(self, query_embedding: list[float], n_results: int = 3) -> list[str]:
        """쿼리 벡터와 코사인 유사도가 높은 문서를 반환한다.

        pgvector의 <=> 연산자(코사인 거리)를 사용하여 가장 유사한 문서를
        오름차순(거리 짧은 순 = 유사도 높은 순)으로 정렬하여 반환한다.

        Args:
            query_embedding: 사용자 입력을 임베딩한 벡터
            n_results: 반환할 최대 문서 수

        Returns:
            유사도 순으로 정렬된 문서 텍스트 리스트
        """
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
            # 각 행의 첫 번째 컬럼(document)만 추출하여 리스트로 반환
            return [row[0] for row in cur.fetchall()]

    def count(self) -> int:
        """테이블에 저장된 문서 수를 반환한다.

        인덱스 구축 여부 확인 및 첫 실행 시 자동 인덱싱 결정에 사용된다.

        Returns:
            저장된 문서 레코드 수
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.table))
            )
            return cur.fetchone()[0]

    def close(self):
        """PostgreSQL 연결을 닫는다.

        프로그램 종료 시 RAGRetriever.close()를 통해 호출된다.
        """
        self.conn.close()
