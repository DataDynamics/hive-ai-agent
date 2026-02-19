"""
rag/document_loader.py
----------------------
knowledge 디렉토리의 JSON 파일을 읽어 문서 목록으로 반환하는 모듈.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_knowledge_base(knowledge_dir: str) -> list[dict]:
    """knowledge 디렉토리의 모든 JSON 파일을 읽어 문서 목록을 반환한다.

    Args:
        knowledge_dir: JSON 파일들이 위치한 디렉토리 경로

    Returns:
        {"id", "text", "metadata"} 키를 가진 딕셔너리의 리스트
    """
    docs = []
    path = Path(knowledge_dir)
    files = sorted(path.glob("*.json"))
    logger.debug("knowledge 디렉토리 스캔 — 경로=%s, 파일 수=%d", knowledge_dir, len(files))

    for file in files:
        logger.debug("JSON 파일 로드 — %s", file.name)
        with open(file, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            docs.append({
                "id":       item["id"],
                "text":     item["text"].strip(),
                "metadata": item.get("metadata", {})
            })

    logger.info("knowledge base 로드 완료 — 총 %d 개 문서", len(docs))
    return docs
