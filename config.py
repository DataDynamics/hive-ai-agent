"""
config.py
---------
프로젝트 전역 설정 모듈.

우선순위: 환경변수(.env) > config.yaml 기본값
- 환경변수가 존재하면 환경변수 값을 사용
- 환경변수가 없으면 config.yaml에 정의된 기본값을 사용
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# .env 파일이 존재하면 환경변수로 로드 (없어도 오류 없음)
load_dotenv()

# 이 파일이 위치한 디렉토리를 프로젝트 루트로 사용
_project_root = Path(__file__).parent

# config.yaml 파일을 읽어 기본값 딕셔너리로 파싱
_config_path = _project_root / "config.yaml"
with open(_config_path, "r", encoding="utf-8") as f:
    _yaml = yaml.safe_load(f)


def _resolve_path(path_str: str) -> str:
    """
    상대 경로를 프로젝트 루트 기준 절대 경로로 변환한다.
    이미 절대 경로인 경우 그대로 반환한다.

    Args:
        path_str: 변환할 경로 문자열

    Returns:
        절대 경로 문자열
    """
    p = Path(path_str)
    return str(p if p.is_absolute() else _project_root / p)


# ──────────────────────────────────────────────
# Ollama / Qwen 설정
# ──────────────────────────────────────────────

# Ollama 서버의 OpenAI 호환 API 엔드포인트 URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", _yaml["ollama"]["base_url"])

# Ollama에서 사용할 LLM 모델 이름 (예: qwen2.5:7b)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", _yaml["ollama"]["model"])

# ──────────────────────────────────────────────
# Hive REST API 설정
# ──────────────────────────────────────────────

# Hive REST API 서버의 기본 URL (예: http://localhost:8080)
HIVE_API_BASE_URL = os.getenv("HIVE_API_BASE_URL", _yaml["hive"]["api_base_url"])

# ──────────────────────────────────────────────
# RAG 설정
# ──────────────────────────────────────────────

# pgvector 테이블(컬렉션) 이름 — 문서 벡터가 저장되는 테이블
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", _yaml["rag"]["collection_name"])

# knowledge 디렉토리 경로 — JSON 문서 파일들이 위치하는 폴더 (절대 경로로 변환)
RAG_KNOWLEDGE_DIR = _resolve_path(os.getenv("RAG_KNOWLEDGE_DIR", _yaml["rag"]["knowledge_dir"]))

# 유사 문서 검색 시 반환할 최대 문서 수
RAG_N_RESULTS = int(os.getenv("RAG_N_RESULTS", str(_yaml["rag"]["n_results"])))

# Ollama에서 사용할 임베딩 모델 이름 (예: nomic-embed-text)
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", _yaml["rag"]["embedding_model"])

# 임베딩 벡터의 차원 수 — pgvector 테이블 생성 시 사용 (nomic-embed-text: 768)
RAG_EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", str(_yaml["rag"]["embedding_dim"])))

# ──────────────────────────────────────────────
# pgvector (PostgreSQL) 설정
# ──────────────────────────────────────────────

# PostgreSQL 서버 호스트
PG_HOST = os.getenv("PG_HOST", _yaml["pgvector"]["host"])

# PostgreSQL 서버 포트
PG_PORT = int(os.getenv("PG_PORT", str(_yaml["pgvector"]["port"])))

# 연결할 데이터베이스 이름
PG_DATABASE = os.getenv("PG_DATABASE", _yaml["pgvector"]["database"])

# PostgreSQL 접속 사용자명
PG_USER = os.getenv("PG_USER", _yaml["pgvector"]["user"])

# PostgreSQL 접속 비밀번호
PG_PASSWORD = os.getenv("PG_PASSWORD", _yaml["pgvector"]["password"])
