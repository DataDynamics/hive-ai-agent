"""
agent.py
--------
Hive AI Agent의 핵심 로직 모듈.

동작 흐름:
    1. 사용자의 자연어 입력을 받는다.
    2. RAGRetriever로 관련 API 문서/예제를 검색하여 컨텍스트를 구성한다.
    3. Qwen LLM(Ollama)에 컨텍스트와 사용자 요청을 전달한다.
    4. LLM이 Tool call을 반환하면 HiveApiClient로 실제 REST API를 호출한다.
    5. API 응답을 다시 LLM에 전달하여 사람이 읽기 쉬운 최종 답변을 생성한다.
"""

import json
from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from tools import TOOLS
from api_client import HiveApiClient
from rag import RAGRetriever


# LLM에게 역할과 행동 방식을 지시하는 시스템 프롬프트.
# 대화 내내 messages 리스트의 첫 번째 항목으로 유지된다.
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
    """자연어 입력을 Hive REST API 호출로 변환하는 AI Agent.

    Qwen LLM의 function calling 기능과 RAG를 결합하여
    사용자의 한국어 요청을 정확한 API 호출로 처리한다.
    """

    def __init__(self, token: str):
        """
        Args:
            token: 로그인 후 발급받은 인증 토큰.
                   HiveApiClient에 전달되어 모든 API 호출 헤더에 포함된다.
        """
        # Ollama의 OpenAI 호환 엔드포인트에 연결하는 LLM 클라이언트
        # api_key는 Ollama에서 요구하지 않지만 OpenAI SDK 형식상 필요
        self.client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
        )
        # 사용할 LLM 모델명 (예: qwen2.5:7b)
        self.model = OLLAMA_MODEL
        # Hive REST API 호출 클라이언트 — 인증 토큰 전달
        self.api_client = HiveApiClient(token)
        # RAG 검색기 — pgvector에서 관련 문서를 검색
        self.retriever = RAGRetriever()
        # 대화 히스토리 — 시스템 프롬프트를 첫 번째 메시지로 초기화
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        """사용자 입력을 처리하고 Agent의 최종 응답을 반환한다.

        내부적으로 3단계로 동작한다:
            1단계: RAG 컨텍스트를 포함하여 LLM에 요청 → Tool call 결정
            2단계: LLM이 선택한 Tool을 실행 → REST API 호출
            3단계: API 결과를 LLM에 전달 → 자연어 최종 응답 생성

        Args:
            user_input: 사용자가 입력한 자연어 문자열

        Returns:
            LLM이 생성한 최종 응답 문자열
        """
        # ── 전처리: RAG로 관련 API 문서 및 예제 검색 ──────────────────────
        rag_context = self.retriever.retrieve(user_input)

        # 검색된 컨텍스트를 사용자 요청 앞에 붙여 LLM의 이해를 돕는다
        augmented_input = (
            f"[관련 API 문서 및 예제]\n{rag_context}\n\n"
            f"[사용자 요청]\n{user_input}"
        )

        # 대화 히스토리에 사용자 메시지(컨텍스트 포함) 추가
        self.messages.append({"role": "user", "content": augmented_input})

        # ── 1단계: LLM에 요청 → Tool call 결정 ──────────────────────────
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=TOOLS,        # LLM이 선택할 수 있는 Tool 목록
            tool_choice="auto", # LLM이 Tool 사용 여부를 자동 판단
        )

        message = response.choices[0].message

        # Tool call이 없는 경우 — LLM이 일반 텍스트로 응답한 경우
        if not message.tool_calls:
            self.messages.append({"role": "assistant", "content": message.content})
            return message.content

        # ── 2단계: Tool call 실행 ─────────────────────────────────────────
        # LLM의 응답 메시지(tool_calls 포함)를 히스토리에 추가
        self.messages.append(message)
        tool_results = []

        for tool_call in message.tool_calls:
            # LLM이 선택한 Tool 이름과 파라미터 추출
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # 실행 중인 Tool 정보를 콘솔에 출력 (디버깅용)
            print(f"  [Tool] {tool_name}({tool_args})")

            # HiveApiClient를 통해 실제 REST API 호출
            result = self.api_client.execute_tool(tool_name, tool_args)

            # Tool 실행 결과를 OpenAI 형식에 맞춰 수집
            tool_results.append({
                "tool_call_id": tool_call.id,   # LLM의 tool_call과 결과를 연결하는 ID
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)
            })

        # 모든 Tool 결과를 대화 히스토리에 추가
        self.messages.extend(tool_results)

        # ── 3단계: Tool 결과를 바탕으로 최종 응답 생성 ────────────────────
        # LLM이 API 응답을 해석하여 사람이 읽기 좋은 텍스트로 변환
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )

        final_message = final_response.choices[0].message.content
        # 최종 응답도 대화 히스토리에 추가 (다음 대화에서 참조)
        self.messages.append({"role": "assistant", "content": final_message})
        return final_message

    def reset(self):
        """대화 히스토리를 초기화한다.

        시스템 프롬프트만 남기고 이전 대화 내용을 모두 삭제한다.
        사용자가 'reset' 명령어를 입력했을 때 호출된다.
        """
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def close(self):
        """Agent가 사용하는 외부 리소스를 해제한다.

        HTTP 클라이언트 연결과 PostgreSQL(pgvector) 연결을 닫는다.
        프로그램 종료 시 반드시 호출해야 한다.
        """
        self.api_client.close()
        self.retriever.close()
