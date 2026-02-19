"""
tools.py
--------
LLM(Qwen)에 전달할 Tool(함수 호출) 목록을 정의한다.

OpenAI function calling 형식을 사용하며, 각 Tool은 Hive REST API
엔드포인트와 1:1로 대응된다. LLM은 사용자의 자연어 입력을 분석하여
이 목록 중 적절한 Tool을 선택하고 파라미터를 채워 반환한다.

지원 Tool:
    - delete_table   : 테이블 삭제   (DELETE /api/hive/table)
    - create_table   : 테이블 생성   (POST   /api/hive/table)
    - get_table_info : 테이블 정보   (GET    /api/hive/table)
    - list_tables    : 테이블 목록   (GET    /api/hive/tables)
    - list_databases : 데이터베이스  (GET    /api/hive/databases)
"""

# LLM에 전달되는 Tool 명세 목록.
# OpenAI Chat Completions API의 tools 파라미터 형식을 따른다.
TOOLS = [
    {
        # Tool 유형: 함수 호출 방식
        "type": "function",
        "function": {
            # Tool 이름 — api_client.execute_tool()의 dispatch 키와 일치해야 함
            "name": "delete_table",
            # LLM이 이 Tool의 목적을 판단할 때 사용하는 설명
            "description": "Hive 테이블을 삭제합니다. (DELETE /api/hive/table)",
            # LLM이 추출해야 할 파라미터의 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        # LLM이 파라미터 의미를 파악하기 위한 설명
                        "description": "테이블이 속한 스키마/데이터베이스 이름 (예: public)"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "삭제할 테이블 이름 (예: measure)"
                    }
                },
                # LLM이 반드시 채워야 하는 필수 파라미터
                "required": ["schema", "table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_table",
            "description": "Hive 테이블을 생성합니다. (POST /api/hive/table)",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "테이블을 생성할 스키마/데이터베이스 이름"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "생성할 테이블 이름"
                    },
                    "columns": {
                        "type": "array",
                        "description": "컬럼 정의 목록",
                        # 배열 내 각 요소(컬럼)의 구조 정의
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "컬럼 이름"},
                                # 지원 타입: STRING, INT, BIGINT, DOUBLE, FLOAT, BOOLEAN, DATE, TIMESTAMP
                                "type": {"type": "string", "description": "컬럼 타입 (예: STRING, INT, DOUBLE)"}
                            },
                            "required": ["name", "type"]
                        }
                    }
                },
                "required": ["schema", "table_name", "columns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_info",
            "description": "Hive 테이블 상세 정보를 조회합니다. (GET /api/hive/table)",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "스키마/데이터베이스 이름"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "조회할 테이블 이름"
                    }
                },
                "required": ["schema", "table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "특정 스키마의 Hive 테이블 목록을 조회합니다. (GET /api/hive/tables)",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "조회할 스키마/데이터베이스 이름"
                    }
                },
                "required": ["schema"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_databases",
            "description": "Hive 데이터베이스(스키마) 목록을 조회합니다. (GET /api/hive/databases)",
            # 파라미터 없음 — 전체 데이터베이스 목록을 반환하므로 인자 불필요
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
