"""
agent.py
--------
Hive AI Agent의 핵심 로직 모듈.
"""

import json
import logging
from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from tools import TOOLS
from api_client import HiveApiClient
from rag import RAGRetriever

logger = logging.getLogger(__name__)

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
    """자연어 입력을 Hive REST API 호출로 변환하는 AI Agent."""

    def __init__(self, token: str):
        """
        Args:
            token: 로그인 후 발급받은 인증 토큰
        """
        self.client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
        )
        self.model = OLLAMA_MODEL
        self.api_client = HiveApiClient(token)
        self.retriever = RAGRetriever()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        logger.info("HiveAgent 초기화 완료 (model=%s)", self.model)

    def chat(self, user_input: str) -> str:
        """사용자 입력을 처리하고 최종 응답을 반환한다.

        Args:
            user_input: 사용자가 입력한 자연어 문자열

        Returns:
            LLM이 생성한 최종 응답 문자열
        """
        logger.info("사용자 입력 수신 (length=%d)", len(user_input))
        logger.debug("사용자 입력 내용: %s", user_input)

        # ── 1단계: RAG 컨텍스트 검색 ─────────────────────────────────
        rag_context = self.retriever.retrieve(user_input)
        logger.debug("RAG 컨텍스트 검색 완료 (length=%d)", len(rag_context))

        augmented_input = (
            f"[관련 API 문서 및 예제]\n{rag_context}\n\n"
            f"[사용자 요청]\n{user_input}"
        )
        self.messages.append({"role": "user", "content": augmented_input})
        logger.debug("대화 히스토리 크기: %d 건", len(self.messages))

        # ── 2단계: LLM 요청 → Tool call 결정 ────────────────────────
        logger.debug("LLM 요청 시작 (model=%s)", self.model)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        # Tool call이 없는 경우 — 일반 텍스트 응답
        if not message.tool_calls:
            logger.info("LLM 일반 응답 반환 (Tool call 없음)")
            self.messages.append({"role": "assistant", "content": message.content})
            return message.content

        # ── 3단계: Tool call 실행 ────────────────────────────────────
        logger.info("Tool call %d 건 실행 시작", len(message.tool_calls))
        self.messages.append(message)
        tool_results = []

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            logger.info("Tool 실행 — %s(%s)", tool_name, tool_args)
            print(f"  [Tool] {tool_name}({tool_args})")

            result = self.api_client.execute_tool(tool_name, tool_args)
            logger.debug("Tool 결과 — success=%s, status=%s", result.get("success"), result.get("status_code"))

            tool_results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)
            })

        self.messages.extend(tool_results)

        # ── 4단계: 최종 응답 생성 ────────────────────────────────────
        logger.debug("최종 응답 생성 요청")
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )
        final_message = final_response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": final_message})
        logger.info("최종 응답 생성 완료 (length=%d)", len(final_message))
        return final_message

    def reset(self):
        """대화 히스토리를 초기화한다."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        logger.info("대화 히스토리 초기화")

    def close(self):
        """Agent가 사용하는 외부 리소스를 해제한다."""
        self.api_client.close()
        self.retriever.close()
        logger.info("HiveAgent 리소스 해제 완료")
