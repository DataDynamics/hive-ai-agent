"""
main.py
-------
Hive AI Agent CLI 진입점.

실행 흐름:
    1. 시작 배너 출력
    2. authenticate()로 로그인 수행 — 최대 3회 시도, 초과 시 종료
    3. 인증 토큰으로 HiveAgent 인스턴스 생성
    4. 대화 루프 진입 — 사용자 입력을 Agent에 전달하고 응답 출력
    5. 'exit'/'quit' 입력 시 종료, 'reset' 입력 시 대화 초기화

실행 방법:
    python main.py
"""

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from api_client import HiveApiClient
from agent import HiveAgent

# 터미널 출력을 담당하는 Rich 콘솔 객체 (색상, 패널 등 지원)
console = Console()

# 로그인 실패 허용 최대 횟수 — 초과 시 프로그램 강제 종료
MAX_LOGIN_ATTEMPTS = 3


def authenticate() -> str:
    """사용자 인증을 수행하고 성공 시 토큰을 반환한다.

    Username과 Password를 입력받아 /api/auth/login을 호출한다.
    실패 시 남은 시도 횟수를 안내하며 재입력을 요청한다.
    MAX_LOGIN_ATTEMPTS 초과 시 SystemExit 예외로 프로그램을 종료한다.

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
        # 사용자로부터 인증 정보 입력 (password=True 로 비밀번호 마스킹)
        username = Prompt.ask("[bold]Username[/bold]")
        password = Prompt.ask("[bold]Password[/bold]", password=True)

        try:
            token = HiveApiClient.login(username, password)
            console.print("[bold green]인증 성공[/bold green]")
            return token

        except httpx.HTTPStatusError as e:
            # 서버가 4xx/5xx를 반환한 경우
            status = e.response.status_code
            if status in (401, 403):
                # 인증 정보 불일치
                msg = "아이디 또는 비밀번호가 올바르지 않습니다."
            else:
                # 그 외 서버 측 오류
                msg = f"서버 오류 (HTTP {status})"

        except httpx.RequestError:
            # 네트워크 연결 실패 (서버 다운, 잘못된 URL 등)
            msg = "서버에 연결할 수 없습니다. API URL을 확인하세요."

        except ValueError as e:
            # 응답은 왔지만 token 필드가 없는 경우
            msg = str(e)

        # 남은 시도 횟수 계산 및 안내 메시지 출력
        remaining = MAX_LOGIN_ATTEMPTS - attempt
        if remaining > 0:
            console.print(f"[bold red]인증 실패:[/bold red] {msg} (남은 시도: {remaining}회)")
        else:
            console.print(f"[bold red]인증 실패:[/bold red] {msg}")

    # 모든 시도 소진 — 프로그램 종료
    raise SystemExit("로그인 시도 횟수를 초과했습니다. 프로그램을 종료합니다.")


def main():
    """CLI 메인 함수. 인증 후 대화 루프를 실행한다."""
    # 시작 배너 출력
    console.print(Panel.fit(
        "[bold cyan]Hive AI Agent[/bold cyan]\n"
        "Model: Qwen (Ollama)\n"
        "자연어로 Hive 테이블을 관리하세요.\n"
        "[dim]종료: 'exit' 또는 'quit' | 대화 초기화: 'reset'[/dim]",
        border_style="cyan"
    ))

    # 인증 수행 — 실패 시 이 줄에서 SystemExit 발생
    token = authenticate()

    # 발급받은 토큰으로 Agent 초기화
    agent = HiveAgent(token=token)

    try:
        # ── 대화 루프 ───────────────────────────────────────────────────
        while True:
            # 사용자 입력 수신 (앞뒤 공백 제거)
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()

            # 빈 입력 무시
            if not user_input:
                continue

            # 종료 명령어 처리
            if user_input.lower() in ("exit", "quit"):
                console.print("[dim]종료합니다.[/dim]")
                break

            # 대화 초기화 명령어 처리
            if user_input.lower() == "reset":
                agent.reset()
                console.print("[dim]대화 기록을 초기화했습니다.[/dim]")
                continue

            # Agent에 입력 전달 및 응답 수신
            console.print("[dim]처리 중...[/dim]")
            response = agent.chat(user_input)

            # Agent 응답을 패널 형식으로 출력
            console.print(Panel(response, title="[bold blue]Agent[/bold blue]", border_style="blue"))

    finally:
        # 루프 종료(정상/예외 모두) 시 리소스 해제
        agent.close()


if __name__ == "__main__":
    main()
