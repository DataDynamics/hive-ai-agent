"""
web_app.py
----------
Hive AI Agent 웹 인터페이스 서버 모듈.

실행 방법:
    python web_app.py
    또는
    uvicorn web_app:app --host 0.0.0.0 --port 8000 --reload
"""

import uuid
import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from logger import setup_logging
from agent import HiveAgent
from api_client import HiveApiClient

# 로깅 설정 — 가장 먼저 초기화
setup_logging()
logger = logging.getLogger(__name__)

# ── FastAPI 앱 초기화 ────────────────────────────────────────────────────────

app = FastAPI(title="Hive AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 세션 저장소 ─────────────────────────────────────────────────────────────

# { session_id(str): HiveAgent }
sessions: dict[str, HiveAgent] = {}


# ── 요청/응답 스키마 ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SessionRequest(BaseModel):
    session_id: str


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def get_agent(session_id: str) -> HiveAgent:
    """세션 ID로 HiveAgent를 조회한다. 없으면 401 예외를 발생시킨다."""
    agent = sessions.get(session_id)
    if not agent:
        logger.warning("유효하지 않은 세션 접근 — session_id=%s", session_id)
        raise HTTPException(status_code=401, detail="세션이 없거나 만료되었습니다. 다시 로그인해주세요.")
    return agent


# ── 엔드포인트 ──────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
def index():
    """웹 UI HTML 파일을 반환한다."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(str(html_path), media_type="text/html")


@app.post("/api/login")
def login(req: LoginRequest):
    """Hive API 인증을 수행하고 세션을 생성한다."""
    logger.info("로그인 요청 — username=%s", req.username)
    try:
        token = HiveApiClient.login(req.username, req.password)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.warning("로그인 실패 — username=%s, status=%s", req.username, status)
        if status in (401, 403):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
        raise HTTPException(status_code=status, detail=f"서버 오류 (HTTP {status})")
    except httpx.RequestError:
        logger.error("로그인 중 서버 연결 오류 — username=%s", req.username)
        raise HTTPException(status_code=503, detail="Hive 서버에 연결할 수 없습니다.")
    except ValueError as e:
        logger.error("로그인 응답 오류 — %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    session_id = str(uuid.uuid4())
    sessions[session_id] = HiveAgent(token=token)
    logger.info("세션 생성 완료 — username=%s, session_id=%s", req.username, session_id)
    return {"session_id": session_id}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """사용자 메시지를 Agent에 전달하고 응답을 반환한다."""
    logger.info("채팅 요청 — session_id=%s, message_length=%d", req.session_id, len(req.message))
    agent = get_agent(req.session_id)
    try:
        response = agent.chat(req.message)
    except Exception as e:
        logger.error("Agent 처리 오류 — session_id=%s, error=%s", req.session_id, str(e))
        raise HTTPException(status_code=500, detail=f"Agent 처리 오류: {str(e)}")
    logger.info("채팅 응답 완료 — session_id=%s, response_length=%d", req.session_id, len(response))
    return {"response": response}


@app.post("/api/reset")
def reset(req: SessionRequest):
    """현재 세션의 대화 기록을 초기화한다."""
    agent = get_agent(req.session_id)
    agent.reset()
    logger.info("대화 초기화 — session_id=%s", req.session_id)
    return {"ok": True}


@app.post("/api/logout")
def logout(req: SessionRequest):
    """세션을 종료하고 관련 리소스를 해제한다."""
    agent = sessions.pop(req.session_id, None)
    if agent:
        agent.close()
        logger.info("로그아웃 — session_id=%s", req.session_id)
    else:
        logger.debug("존재하지 않는 세션 로그아웃 시도 — session_id=%s", req.session_id)
    return {"ok": True}


# ── 서버 실행 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Hive AI Agent 웹 서버 시작 — http://0.0.0.0:8000")
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
