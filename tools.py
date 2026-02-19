# OpenAI function calling 형식의 Tool 정의
# 각 Tool은 Hive REST API 엔드포인트와 1:1 대응

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "delete_table",
            "description": "Hive 테이블을 삭제합니다. (DELETE /api/hive/table)",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "테이블이 속한 스키마/데이터베이스 이름 (예: public)"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "삭제할 테이블 이름 (예: measure)"
                    }
                },
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
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "컬럼 이름"},
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
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
