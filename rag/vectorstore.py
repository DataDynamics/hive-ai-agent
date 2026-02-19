import json
import psycopg2
from psycopg2 import sql
from pgvector.psycopg2 import register_vector
from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, RAG_EMBEDDING_DIM


class VectorStore:
    def __init__(self, collection_name: str):
        self.table = collection_name
        self.conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
        )
        register_vector(self.conn)
        self._init_table()

    def _init_table(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id       TEXT PRIMARY KEY,
                    document TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({dim})
                )
            """).format(
                sql.Identifier(self.table),
                dim=sql.Literal(RAG_EMBEDDING_DIM)
            ))
        self.conn.commit()

    def upsert(self, docs: list[dict], embeddings: list[list[float]]):
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
                    (doc["id"], doc["text"], json.dumps(doc.get("metadata", {})), emb)
                )
        self.conn.commit()

    def query(self, query_embedding: list[float], n_results: int = 3) -> list[str]:
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
            return [row[0] for row in cur.fetchall()]

    def count(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.table))
            )
            return cur.fetchone()[0]

    def close(self):
        self.conn.close()
