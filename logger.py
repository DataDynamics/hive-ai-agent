"""
logger.py
---------
애플리케이션 로깅 설정 모듈.

config.yaml의 logging 섹션을 읽어 두 가지 핸들러를 구성한다.
    - StreamHandler  : 콘솔(표준 출력) 로깅
    - TimedRotatingFileHandler : 일 단위 롤링 파일 로깅 (app.log)

사용법:
    # 애플리케이션 시작 시 1회 호출
    from logger import setup_logging
    setup_logging()

    # 각 모듈에서는 표준 방식으로 로거 획득
    import logging
    logger = logging.getLogger(__name__)

롤링 파일 규칙:
    - 매일 자정에 현재 app.log를 app.log.YYYY-MM-DD 로 이름 변경
    - 새로운 app.log에 다음 날 로그 기록
    - backup_count 일치 이전 파일은 자동 삭제
"""

import logging
import logging.handlers
import yaml
from pathlib import Path

# 로깅 설정이 중복 적용되는 것을 방지하기 위한 플래그
_initialized = False


def setup_logging(config_path: str | None = None) -> None:
    """config.yaml의 logging 섹션을 읽어 루트 로거를 구성한다.

    이미 한 번 호출된 경우 중복 핸들러 등록을 방지하기 위해 즉시 반환한다.

    Args:
        config_path: config.yaml 파일 경로.
                     None이면 이 파일과 같은 디렉토리의 config.yaml을 사용.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # ── config.yaml 로드 ────────────────────────────────────────────────
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["logging"]

    # ── 로그 포맷터 생성 (콘솔/파일 공통) ─────────────────────────────
    formatter = logging.Formatter(
        fmt=cfg["format"],
        datefmt=cfg["date_format"],
    )

    # ── 루트 로거 레벨 설정 ────────────────────────────────────────────
    # 루트 레벨을 가장 낮게 설정하고, 각 핸들러에서 필터링
    root_logger = logging.getLogger()
    root_logger.setLevel(cfg["level"])

    # ── 콘솔 핸들러 ────────────────────────────────────────────────────
    if cfg["console"]["enabled"]:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(cfg["console"]["level"])
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # ── 파일 핸들러 (일 단위 롤링) ────────────────────────────────────
    if cfg["file"]["enabled"]:
        # 상대 경로는 프로젝트 루트(이 파일 위치) 기준으로 절대 경로 변환
        log_path = Path(cfg["file"]["path"])
        if not log_path.is_absolute():
            log_path = Path(__file__).parent / log_path

        # 로그 디렉토리가 없으면 자동 생성
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_path),
            when=cfg["file"]["when"],             # "midnight" → 매일 자정 롤링
            backupCount=cfg["file"]["backup_count"],  # 보관할 과거 로그 파일 수
            encoding=cfg["file"]["encoding"],
        )
        file_handler.setLevel(cfg["file"]["level"])
        file_handler.setFormatter(formatter)
        # 롤링 파일명 형식: app.log.2024-01-15
        file_handler.suffix = "%Y-%m-%d"
        root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "로깅 설정 완료 — 콘솔: %s, 파일: %s (%s)",
        cfg["console"]["level"],
        cfg["file"]["level"],
        cfg["file"]["path"],
    )
