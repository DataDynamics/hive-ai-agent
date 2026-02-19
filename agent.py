import json
from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from tools import TOOLS
from api_client import HiveApiClient
from rag import RAGRetriever


SYSTEM_PROMPT = """당신은 Hive 메타스토어를 관리하는 AI Agent입니다.
사용자의 자연어 요청을 분석하여 적절한 REST API를 호출합니다.

사용 가능한 작업:
- 테이블 삭제 (delete_table)
- 테이블 생성 (create_table)
- 테이블 정보 조회 (get_table_info)
- 테이블 목록 조회 (list_tables)
- 데이터베이스 목록 조회 (list_databases)

스키마와 테이블명이 'schema.table' 형식으로 주어지면 올바르게 파싱하세요.
예: 'public.measure' → schema='public', table_name='measure'
"""


class HiveAgent:
    def __init__(self, token: str):
        self.client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",  # Ollama는 API Key가 필요 없지만 형식상 필요
        )
        self.model = OLLAMA_MODEL
        self.api_client = HiveApiClient(token)
        self.retriever = RAGRetriever()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        # RAG: 사용자 입력과 관련된 API 문서/예제 검색
        rag_context = self.retriever.retrieve(user_input)

        augmented_input = (
            f"[관련 API 문서 및 예제]\n{rag_context}\n\n"
            f"[사용자 요청]\n{user_input}"
        )

        self.messages.append({"role": "user", "content": augmented_input})

        # 1단계: LLM에 요청 → tool call 결정
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Tool call이 없는 경우 (일반 응답)
        if not message.tool_calls:
            self.messages.append({"role": "assistant", "content": message.content})
            return message.content

        # 2단계: Tool call 실행
        self.messages.append(message)
        tool_results = []

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"  [Tool] {tool_name}({tool_args})")

            result = self.api_client.execute_tool(tool_name, tool_args)

            tool_results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)
            })

        self.messages.extend(tool_results)

        # 3단계: Tool 결과를 바탕으로 최종 응답 생성
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )

        final_message = final_response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": final_message})
        return final_message

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def close(self):
        self.api_client.close()
        self.retriever.close()
