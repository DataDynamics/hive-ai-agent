"""
main.py
-------
Hive AI Agent CLI 진입점.
"""

import logging
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from logger import setup_logging
from api_client import HiveApiClient
from agent import HiveAgent

# 로깅 설정 — 가장 먼저 초기화
setup_logging()
logger = logging.getLogger(__name__)

console = Console()

# 로그인 실패 허용 최대 횟수
MAX_LOGIN_ATTEMPTS = 3


def authenticate() -> str:
    """사용자 인증을 수행하고 성공 시 토큰을 반환한다.

    Returns:
        인증 성공 시 서버로부터 발급받은 토큰 문자열

    Raises:
        SystemExit: 최대 로그인 시도 횟수 초과 시
    """
    console.print(Panel.fit(
        "[bold yellow]로그인[/bold yellow]\n인증 후 Agent를 사용할 수 있습니다.",
        border_style="yellow"
    ))

    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        username = Prompt.ask("[bold]Username[/bold]")
        password = Prompt.ask("[bold]Password[/bold]", password=True)

        logger.info("로그인 시도 %d/%d (username=%s)", attempt, MAX_LOGIN_ATTEMPTS, username)

        try:
            token = HiveApiClient.login(username, password)
            console.print("[bold green]인증 성공[/bold green]")
            return token

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (401, 403):
                msg = "아이디 또는 비밀번호가 올바르지 않습니다."
            else:
                msg = f"서버 오류 (HTTP {status})"
            logger.warning("로그인 실패 (username=%s, status=%s)", username, status)

        except httpx.RequestError:
            msg = "서버에 연결할 수 없습니다. API URL을 확인하세요."
            logger.error("로그인 중 연결 오류 (username=%s)", username)

        except ValueError as e:
            msg = str(e)
            logger.error("로그인 응답 오류 (username=%s): %s", username, msg)

        remaining = MAX_LOGIN_ATTEMPTS - attempt
        if remaining > 0:
            console.print(f"[bold red]인증 실패:[/bold red] {msg} (남은 시도: {remaining}회)")
        else:
            console.print(f"[bold red]인증 실패:[/bold red] {msg}")

    logger.critical("로그인 시도 횟수 초과 — 프로그램 종료")
    raise SystemExit("로그인 시도 횟수를 초과했습니다. 프로그램을 종료합니다.")


def main():
    """CLI 메인 함수. 인증 후 대화 루프를 실행한다."""
    logger.info("Hive AI Agent CLI 시작")

    console.print(Panel.fit(
        "[bold cyan]Hive AI Agent[/bold cyan]\n"
        "Model: Qwen (Ollama)\n"
        "자연어로 Hive 테이블을 관리하세요.\n"
        "[dim]종료: 'exit' 또는 'quit' | 대화 초기화: 'reset'[/dim]",
        border_style="cyan"
    ))

    token = authenticate()
    agent = HiveAgent(token=token)

    try:
        while True:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                logger.info("사용자 종료 요청")
                console.print("[dim]종료합니다.[/dim]")
                break
            if user_input.lower() == "reset":
                agent.reset()
                console.print("[dim]대화 기록을 초기화했습니다.[/dim]")
                continue

            console.print("[dim]처리 중...[/dim]")
            response = agent.chat(user_input)
            console.print(Panel(response, title="[bold blue]Agent[/bold blue]", border_style="blue"))

    finally:
        agent.close()
        logger.info("Hive AI Agent CLI 종료")


if __name__ == "__main__":
    main()
