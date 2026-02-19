"""
api_client.py
-------------
Hive REST API와 통신하는 HTTP 클라이언트 모듈.
"""

import logging
import httpx
from config import HIVE_API_BASE_URL

# 모듈 단위 로거 — 로그에 "api_client" 이름으로 출력됨
logger = logging.getLogger(__name__)


class HiveApiClient:
    """Hive REST API 클라이언트."""

    def __init__(self, token: str):
        """
        Args:
            token: /api/auth/login 으로 발급받은 인증 토큰
        """
        self.base_url = HIVE_API_BASE_URL.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        logger.debug("HiveApiClient 초기화 완료 (base_url=%s)", self.base_url)

    @property
    def _auth_headers(self) -> dict:
        """모든 API 요청에 포함할 인증 헤더를 반환한다."""
        return {"agent_token": self.token}

    @staticmethod
    def login(username: str, password: str) -> str:
        """사용자 인증을 수행하고 토큰을 반환한다.

        Raises:
            httpx.HTTPStatusError: HTTP 4xx/5xx 응답 시
            httpx.RequestError: 서버 연결 실패 시
            ValueError: 응답 JSON에 token 필드가 없을 때
        """
        base_url = HIVE_API_BASE_URL.rstrip("/")
        login_url = f"{base_url}/api/auth/login"
        logger.info("로그인 시도 (username=%s, url=%s)", username, login_url)

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                login_url,
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            token = response.json().get("token")
            if not token:
                raise ValueError("응답에 token 필드가 없습니다.")

        logger.info("로그인 성공 (username=%s)", username)
        return token

    def delete_table(self, schema: str, table_name: str) -> dict:
        """Hive 테이블을 삭제한다. (DELETE /api/hive/table)"""
        url = f"{self.base_url}/api/hive/table"
        logger.info("DELETE 테이블 — %s.%s", schema, table_name)
        response = self.client.request(
            method="DELETE",
            url=url,
            headers=self._auth_headers,
            json={"schema": schema, "table": table_name},
        )
        result = self._handle_response(response)
        logger.debug("DELETE 응답 — status=%s, success=%s", result["status_code"], result["success"])
        return result

    def create_table(self, schema: str, table_name: str, columns: list) -> dict:
        """Hive 테이블을 생성한다. (POST /api/hive/table)"""
        url = f"{self.base_url}/api/hive/table"
        logger.info("POST 테이블 생성 — %s.%s, 컬럼 수=%d", schema, table_name, len(columns))
        response = self.client.post(
            url=url,
            headers=self._auth_headers,
            json={"schema": schema, "table": table_name, "columns": columns},
        )
        result = self._handle_response(response)
        logger.debug("POST 응답 — status=%s, success=%s", result["status_code"], result["success"])
        return result

    def get_table_info(self, schema: str, table_name: str) -> dict:
        """Hive 테이블의 상세 정보를 조회한다. (GET /api/hive/table)"""
        url = f"{self.base_url}/api/hive/table"
        logger.info("GET 테이블 정보 — %s.%s", schema, table_name)
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
            params={"schema": schema, "table": table_name},
        )
        result = self._handle_response(response)
        logger.debug("GET 테이블 응답 — status=%s", result["status_code"])
        return result

    def list_tables(self, schema: str) -> dict:
        """특정 스키마의 테이블 목록을 조회한다. (GET /api/hive/tables)"""
        url = f"{self.base_url}/api/hive/tables"
        logger.info("GET 테이블 목록 — schema=%s", schema)
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
            params={"schema": schema},
        )
        result = self._handle_response(response)
        logger.debug("GET 테이블 목록 응답 — status=%s", result["status_code"])
        return result

    def list_databases(self) -> dict:
        """전체 데이터베이스 목록을 조회한다. (GET /api/hive/databases)"""
        url = f"{self.base_url}/api/hive/databases"
        logger.info("GET 데이터베이스 목록")
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
        )
        result = self._handle_response(response)
        logger.debug("GET 데이터베이스 목록 응답 — status=%s", result["status_code"])
        return result

    def _handle_response(self, response: httpx.Response) -> dict:
        """HTTP 응답을 공통 형식의 딕셔너리로 변환한다."""
        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        if not response.is_success:
            logger.warning("API 오류 응답 — status=%s, url=%s", response.status_code, response.url)

        return {
            "status_code": response.status_code,
            "success": response.is_success,
            "data": data,
        }

    def close(self):
        """HTTP 클라이언트 연결을 종료한다."""
        self.client.close()
        logger.debug("HiveApiClient 연결 종료")

    def execute_tool(self, tool_name: str, tool_args: dict) -> dict:
        """LLM이 선택한 Tool 이름을 해당 API 메서드 호출로 연결한다."""
        logger.info("Tool 실행 — name=%s, args=%s", tool_name, tool_args)
        dispatch = {
            "delete_table":   lambda a: self.delete_table(a["schema"], a["table_name"]),
            "create_table":   lambda a: self.create_table(a["schema"], a["table_name"], a["columns"]),
            "get_table_info": lambda a: self.get_table_info(a["schema"], a["table_name"]),
            "list_tables":    lambda a: self.list_tables(a["schema"]),
            "list_databases": lambda a: self.list_databases(),
        }
        handler = dispatch.get(tool_name)
        if handler is None:
            logger.error("알 수 없는 Tool — name=%s", tool_name)
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return handler(tool_args)
