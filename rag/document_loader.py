"""
rag/document_loader.py
----------------------
knowledge 디렉토리의 JSON 파일을 읽어 문서 목록으로 반환하는 모듈.

knowledge 디렉토리에는 Hive API 엔드포인트 설명과 한국어 예제가
JSON 형식으로 저장되어 있으며, 이 모듈이 해당 파일들을 로드하여
RAGRetriever의 인덱싱 작업에 제공한다.

JSON 파일 구조 (배열):
    [
        {
            "id": "문서 고유 ID",
            "text": "임베딩 및 검색에 사용할 본문 텍스트",
            "metadata": { "tool": "...", "method": "...", ... }
        },
        ...
    ]
"""

import json
from pathlib import Path


def load_knowledge_base(knowledge_dir: str) -> list[dict]:
    """knowledge 디렉토리의 모든 JSON 파일을 읽어 문서 목록을 반환한다.

    디렉토리 내 *.json 파일을 파일명 알파벳 순으로 읽으며,
    각 파일은 문서 객체 배열을 담고 있어야 한다.

    Args:
        knowledge_dir: JSON 파일들이 위치한 디렉토리 경로

    Returns:
        다음 키를 가진 딕셔너리의 리스트:
            - "id"       (str): 문서 고유 식별자
            - "text"     (str): 전처리된 본문 텍스트 (앞뒤 공백 제거)
            - "metadata" (dict): 추가 메타데이터 (없으면 빈 dict)
    """
    docs = []
    path = Path(knowledge_dir)

    # 파일명 알파벳 순으로 *.json 파일을 순회
    for file in sorted(path.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            items = json.load(f)  # JSON 배열을 Python 리스트로 파싱

        for item in items:
            docs.append({
                "id":       item["id"],
                "text":     item["text"].strip(),       # 앞뒤 공백/개행 제거
                "metadata": item.get("metadata", {})   # 메타데이터 없으면 빈 dict
            })

    return docs
