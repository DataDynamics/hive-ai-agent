import httpx
from config import HIVE_API_BASE_URL


class HiveApiClient:
    def __init__(self, token: str):
        self.base_url = HIVE_API_BASE_URL.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    @property
    def _auth_headers(self) -> dict:
        return {"agent_token": self.token}

    @staticmethod
    def login(username: str, password: str) -> str:
        """로그인 후 토큰을 반환합니다. 실패 시 예외를 발생시킵니다."""
        base_url = HIVE_API_BASE_URL.rstrip("/")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{base_url}/api/auth/login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            token = response.json().get("token")
            if not token:
                raise ValueError("응답에 token 필드가 없습니다.")
            return token

    def delete_table(self, schema: str, table_name: str) -> dict:
        url = f"{self.base_url}/api/hive/table"
        response = self.client.request(
            method="DELETE",
            url=url,
            headers=self._auth_headers,
            json={"schema": schema, "table": table_name},
        )
        return self._handle_response(response)

    def create_table(self, schema: str, table_name: str, columns: list) -> dict:
        url = f"{self.base_url}/api/hive/table"
        response = self.client.post(
            url=url,
            headers=self._auth_headers,
            json={"schema": schema, "table": table_name, "columns": columns},
        )
        return self._handle_response(response)

    def get_table_info(self, schema: str, table_name: str) -> dict:
        url = f"{self.base_url}/api/hive/table"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
            params={"schema": schema, "table": table_name},
        )
        return self._handle_response(response)

    def list_tables(self, schema: str) -> dict:
        url = f"{self.base_url}/api/hive/tables"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
            params={"schema": schema},
        )
        return self._handle_response(response)

    def list_databases(self) -> dict:
        url = f"{self.base_url}/api/hive/databases"
        response = self.client.get(
            url=url,
            headers=self._auth_headers,
        )
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict:
        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}
        return {
            "status_code": response.status_code,
            "success": response.is_success,
            "data": data,
        }

    def close(self):
        self.client.close()

    def execute_tool(self, tool_name: str, tool_args: dict) -> dict:
        dispatch = {
            "delete_table": lambda a: self.delete_table(a["schema"], a["table_name"]),
            "create_table": lambda a: self.create_table(a["schema"], a["table_name"], a["columns"]),
            "get_table_info": lambda a: self.get_table_info(a["schema"], a["table_name"]),
            "list_tables": lambda a: self.list_tables(a["schema"]),
            "list_databases": lambda a: self.list_databases(),
        }
        handler = dispatch.get(tool_name)
        if handler is None:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return handler(tool_args)
