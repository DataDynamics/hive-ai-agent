import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_project_root = Path(__file__).parent

# config.yaml에서 기본값 로드
_config_path = _project_root / "config.yaml"
with open(_config_path, "r", encoding="utf-8") as f:
    _yaml = yaml.safe_load(f)


def _resolve_path(path_str: str) -> str:
    p = Path(path_str)
    return str(p if p.is_absolute() else _project_root / p)


# Ollama / Qwen 설정 (환경변수 우선, 없으면 config.yaml 기본값)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", _yaml["ollama"]["base_url"])
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", _yaml["ollama"]["model"])

# Hive REST API 설정
HIVE_API_BASE_URL = os.getenv("HIVE_API_BASE_URL", _yaml["hive"]["api_base_url"])

# RAG 설정
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", _yaml["rag"]["collection_name"])
RAG_KNOWLEDGE_DIR = _resolve_path(os.getenv("RAG_KNOWLEDGE_DIR", _yaml["rag"]["knowledge_dir"]))
RAG_N_RESULTS = int(os.getenv("RAG_N_RESULTS", str(_yaml["rag"]["n_results"])))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", _yaml["rag"]["embedding_model"])
RAG_EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", str(_yaml["rag"]["embedding_dim"])))

# pgvector (PostgreSQL) 설정
PG_HOST = os.getenv("PG_HOST", _yaml["pgvector"]["host"])
PG_PORT = int(os.getenv("PG_PORT", str(_yaml["pgvector"]["port"])))
PG_DATABASE = os.getenv("PG_DATABASE", _yaml["pgvector"]["database"])
PG_USER = os.getenv("PG_USER", _yaml["pgvector"]["user"])
PG_PASSWORD = os.getenv("PG_PASSWORD", _yaml["pgvector"]["password"])
