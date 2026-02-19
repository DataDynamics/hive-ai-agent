"""
web_app.py
----------
Hive AI Agent 웹 인터페이스 서버 모듈.

FastAPI를 사용하여 브라우저에서 AI Agent와 대화할 수 있는
REST API와 HTML 화면을 제공한다.

API 엔드포인트:
    GET  /              → 채팅 웹 UI (index.html) 반환
    POST /api/login     → Hive 인증 후 세션 발급
    POST /api/chat      → 메시지 전송 및 Agent 응답 수신
    POST /api/reset     → 현재 세션의 대화 기록 초기화
    POST /api/logout    → 세션 종료 및 리소스 해제

세션 관리:
    로그인 성공 시 UUID 기반의 session_id를 발급하고,
    서버 메모리(sessions dict)에 HiveAgent 인스턴스를 저장한다.
    클라이언트는 이후 모든 요청에 session_id를 포함해야 한다.

실행 방법:
    python web_app.py
    또는
    uvicorn web_app:app --host 0.0.0.0 --port 8000 --reload
"""

import uuid
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from agent import HiveAgent
from api_client import HiveApiClient


# ── FastAPI 앱 초기화 ────────────────────────────────────────────────────────

app = FastAPI(title="Hive AI Agent", version="1.0.0")

# 개발 환경에서의 CORS 허용 (프론트엔드가 다른 포트에서 실행될 경우 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 세션 저장소 ─────────────────────────────────────────────────────────────

# 로그인한 사용자의 HiveAgent 인스턴스를 session_id 키로 보관
# { session_id(str): HiveAgent }
sessions: dict[str, HiveAgent] = {}


# ── 요청/응답 스키마 (Pydantic 모델) ────────────────────────────────────────

class LoginRequest(BaseModel):
    """로그인 요청 본문 스키마."""
    username: str  # Hive API 사용자명
    password: str  # Hive API 비밀번호


class ChatRequest(BaseModel):
    """채팅 메시지 요청 본문 스키마."""
    session_id: str  # 로그인 시 발급받은 세션 ID
    message: str     # 사용자가 입력한 자연어 메시지


class SessionRequest(BaseModel):
    """세션 ID만 포함하는 요청 본문 스키마 (reset, logout에 사용)."""
    session_id: str


# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────

def get_agent(session_id: str) -> HiveAgent:
    """세션 ID로 HiveAgent를 조회한다.

    세션이 존재하지 않으면 401 에러를 발생시킨다.

    Args:
        session_id: 클라이언트가 보유한 세션 ID

    Returns:
        해당 세션의 HiveAgent 인스턴스

    Raises:
        HTTPException: 세션이 없거나 만료된 경우 (401)
    """
    agent = sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=401, detail="세션이 없거나 만료되었습니다. 다시 로그인해주세요.")
    return agent


# ── API 엔드포인트 ────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
def index():
    """웹 UI HTML 파일을 반환한다."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(str(html_path), media_type="text/html")


@app.post("/api/login")
def login(req: LoginRequest):
    """Hive API 인증을 수행하고 세션을 생성한다.

    HiveApiClient.login()으로 Hive 서버에서 토큰을 발급받고,
    해당 토큰으로 HiveAgent를 초기화하여 세션에 저장한다.

    Args:
        req: username, password를 담은 로그인 요청

    Returns:
        {"session_id": str} — 이후 모든 요청에 사용할 세션 ID

    Raises:
        HTTPException 401: 인증 실패 (잘못된 credentials)
        HTTPException 503: Hive 서버 연결 불가
        HTTPException 500: 기타 서버 오류
    """
    try:
        # Hive REST API 서버에서 인증 토큰 발급
        token = HiveApiClient.login(req.username, req.password)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (401, 403):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
        raise HTTPException(status_code=status, detail=f"서버 오류 (HTTP {status})")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Hive 서버에 연결할 수 없습니다.")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # UUID 기반 세션 ID 생성 및 HiveAgent 초기화
    session_id = str(uuid.uuid4())
    sessions[session_id] = HiveAgent(token=token)

    return {"session_id": session_id}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """사용자 메시지를 Agent에 전달하고 응답을 반환한다.

    RAG 검색 → LLM Tool call → Hive REST API → 최종 응답 생성의
    전체 파이프라인을 실행한다.

    Args:
        req: session_id와 message를 담은 채팅 요청

    Returns:
        {"response": str} — Agent가 생성한 자연어 응답

    Raises:
        HTTPException 401: 유효하지 않은 세션 ID
        HTTPException 500: Agent 처리 중 오류
    """
    agent = get_agent(req.session_id)
    try:
        response = agent.chat(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 처리 오류: {str(e)}")
    return {"response": response}


@app.post("/api/reset")
def reset(req: SessionRequest):
    """현재 세션의 대화 기록을 초기화한다.

    시스템 프롬프트만 남기고 이전 대화 내용을 모두 삭제한다.

    Args:
        req: session_id를 담은 요청

    Returns:
        {"ok": True}
    """
    agent = get_agent(req.session_id)
    agent.reset()
    return {"ok": True}


@app.post("/api/logout")
def logout(req: SessionRequest):
    """세션을 종료하고 관련 리소스를 해제한다.

    HiveAgent의 HTTP 클라이언트와 pgvector 연결을 닫고
    세션 저장소에서 제거한다.

    Args:
        req: session_id를 담은 요청

    Returns:
        {"ok": True}
    """
    # 세션이 없어도 오류 없이 처리 (멱등성 보장)
    agent = sessions.pop(req.session_id, None)
    if agent:
        agent.close()
    return {"ok": True}


# ── 서버 실행 진입점 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",  # 모든 네트워크 인터페이스에서 수신
        port=8000,
        reload=True,     # 코드 변경 시 자동 재시작 (개발 모드)
    )
