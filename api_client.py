"""
api_client.py
-------------
Hive REST API와 통신하는 HTTP 클라이언트 모듈.

주요 역할:
    - 로그인(POST /api/auth/login)을 통해 인증 토큰 획득
    - 인증 토큰을 모든 API 요청 헤더(agent_token)에 포함
    - Hive 테이블/데이터베이스 CRUD 작업을 각 메서드로 제공
    - LLM이 선택한 Tool 이름을 실제 메서드 호출로 연결(execute_tool)
"""

import httpx
from config import HIVE_API_BASE_URL


class HiveApiClient:
    """Hive REST API 클라이언트.

    인스턴스 생성 시 인증 토큰을 받아 저장하고,
    모든 API 호출마다 agent_token 헤더에 토큰을 포함시킨다.
    """

    def __init__(self, token: str):
        """
        Args:
            token: /api/auth/login 으로 발급받은 인증 토큰
        """
        # 슬래시 중복 방지를 위해 trailing slash 제거
        self.base_url = HIVE_API_BASE_URL.rstrip("/")
        # 인증 토큰 저장 — _auth_headers 프로퍼티에서 참조
        self.token = token
        # 공통 헤더(Content-Type)를 기본으로 설정한 HTTP 클라이언트
        # agent_token은 각 메서드에서 개별 요청마다 명시적으로 추가
        self.client = httpx.Client(
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    @property
    def _auth_headers(self) -> dict:
        """모든 API 요청에 포함할 인증 헤더를 반환한다.

        Returns:
            {"agent_token": <token>} 형태의 딕셔너리
        """
        return {"agent_token": self.token}

    @staticmethod
    def login(username: str, password: str) -> str:
        """사용자 인증을 수행하고 토큰을 반환한다.

        POST /api/auth/login 을 호출하여 서버로부터 토큰을 발급받는다.
        인증 실패(4xx/5xx) 또는 응답에 token 필드가 없는 경우 예외를 발생시킨다.

        Args:
            username: 로그인 사용자 이름
            password: 로그인 비밀번호

        Returns:
            서버로부터 발급받은 인증 토큰 문자열

        Raises:
            httpx.HTTPStatusError: HTTP 4xx/5xx 응답 시
            httpx.RequestError: 서버 연결 실패 시
            ValueError: 응답 JSON에 token 필드가 없을 때
        """
        base_url = HIVE_API_BASE_URL.rstrip("/")
        # with 블록으로 요청 후 클라이언트 자동 종료
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{base_url}/api/auth/login",
                json={"username": username, "password": password},
            )
            # HTTP 오류 상태코드(4xx, 5xx)이면 예외 발생
            response.raise_for_status()
            token = response.json().get("token")
            if not token:
                raise ValueError("응답에 token 필드가 없습니다.")
            return token

    def delete_table(self, schema: str, table_name: str) -> dict:
        """Hive 테이블을 삭제한다. (DELETE /api/hive/table)

        Args:
            schema: 테이블이 속한 스키마(데이터베이스) 이름
            table_name: 삭제할 테이블 이름

        Returns:
            _handle_response() 형식의 응답 딕셔너리
        """
        url = f"{self.base_url}/api/hive/table"
        response = self.client.request(
            method="DELETE",
            url=url,
            headers=self._auth_headers,  # agent_token 헤더 포함
            json={"schema": schema, "table": table_name},
        )
        return self._handle_response(response)

    def create_table(self, schema: str, table_name: str, columns: list) -> dict:
        """Hive 테이블을 생성한다. (POST /api/hive/table)

        Args:
            schema: 테이블을 생성할 스키마(데이터베이스) 이름
            table_name: 생성할 테이블 이름
            columns: 컬럼 정의 목록. 각 항목은 {"name": str, "type": str} 형식

        Returns:
            _handle_response() 형식의 응답 딕셔너리
        """
        url = f"{self.base_url}/api/hive/table"
        response = self.client.post(
            url=url,
            headers=self._auth_headers,  # agent_token 헤더 포함
            json={"schema": schema, "table": table_name, "columns": columns},
        )
        return self._handle_response(response)

    def get_table_info(self, schema: str, table_name: str) -> dict:
        """Hive 테이블의 상세 정보를 조회한다. (GET /api/hive/table)

        Args:
            schema: 스키마(데이터베이스) 이름
            table_name: 조회할 테이블 이름

        Returns:
            _handle_response() 형식의 응답 딕셔너리
        """
        url = f"{self.base_url}/api/hive/table"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,  # agent_token 헤더 포함
            params={"schema": schema, "table": table_name},
        )
        return self._handle_response(response)

    def list_tables(self, schema: str) -> dict:
        """특정 스키마의 테이블 목록을 조회한다. (GET /api/hive/tables)

        Args:
            schema: 조회할 스키마(데이터베이스) 이름

        Returns:
            _handle_response() 형식의 응답 딕셔너리
        """
        url = f"{self.base_url}/api/hive/tables"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,  # agent_token 헤더 포함
            params={"schema": schema},
        )
        return self._handle_response(response)

    def list_databases(self) -> dict:
        """전체 데이터베이스(스키마) 목록을 조회한다. (GET /api/hive/databases)

        Returns:
            _handle_response() 형식의 응답 딕셔너리
        """
        url = f"{self.base_url}/api/hive/databases"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,  # agent_token 헤더 포함
        )
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict:
        """HTTP 응답을 공통 형식의 딕셔너리로 변환한다.

        응답 본문이 JSON이 아닌 경우 raw 텍스트로 저장한다.

        Args:
            response: httpx.Response 객체

        Returns:
            {
                "status_code": int,   # HTTP 상태 코드
                "success": bool,      # 2xx 여부
                "data": dict | str    # 파싱된 응답 본문
            }
        """
        try:
            data = response.json()
        except Exception:
            # JSON 파싱 실패 시 원문 텍스트를 그대로 저장
            data = {"raw": response.text}
        return {
            "status_code": response.status_code,
            "success": response.is_success,
            "data": data,
        }

    def close(self):
        """HTTP 클라이언트 연결을 종료한다."""
        self.client.close()

    def execute_tool(self, tool_name: str, tool_args: dict) -> dict:
        """LLM이 선택한 Tool 이름을 해당 API 메서드 호출로 연결한다.

        tools.py에 정의된 Tool 이름과 이 메서드의 dispatch 키가 일치해야 한다.

        Args:
            tool_name: LLM이 선택한 Tool 이름 (예: "delete_table")
            tool_args: LLM이 추출한 파라미터 딕셔너리

        Returns:
            해당 API 메서드의 응답 딕셔너리.
            알 수 없는 tool_name인 경우 {"success": False, "error": ...} 반환
        """
        # Tool 이름 → 실제 메서드 호출 매핑 테이블
        dispatch = {
            "delete_table":   lambda a: self.delete_table(a["schema"], a["table_name"]),
            "create_table":   lambda a: self.create_table(a["schema"], a["table_name"], a["columns"]),
            "get_table_info": lambda a: self.get_table_info(a["schema"], a["table_name"]),
            "list_tables":    lambda a: self.list_tables(a["schema"]),
            "list_databases": lambda a: self.list_databases(),
        }
        handler = dispatch.get(tool_name)
        if handler is None:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return handler(tool_args)
