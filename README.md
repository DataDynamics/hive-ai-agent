# AI Agent for Hive Table Management

## 목적

Hive Table을 관리하기 위한 AI Agent입니다.

## Requirement

- Python
- Ollama
- PostgreSQL + pgvector

## Model

QWEN 2.5 7B 모델을 사용했으나 더 좋은 모델로 업그레이드를 해서 사용할 수 있습니다.

## Model Serving

Model Serving은 Ollama를 사용합니다.

```shell
ollama serve
ollama run qwen2.5:7b
```

---

## 실행 방법

### 사전 준비 (최초 1회)

**1. Python 의존성 설치**

```bash
cd /Users/fharenheit/PycharmProjects/ai_agent_hive
pip install -r requirements.txt
```

---

**2. Ollama 설치 및 모델 다운로드**

```bash
# Ollama 설치 (https://ollama.com)
brew install ollama        # macOS

# Ollama 서버 실행
ollama serve

# LLM 모델 다운로드 (대화용)
ollama pull qwen2.5:7b

# 임베딩 모델 다운로드 (RAG용)
ollama pull nomic-embed-text
```

---

**3. PostgreSQL + pgvector 설치 및 설정**

```bash
# PostgreSQL 설치
brew install postgresql@16
brew services start postgresql@16

# pgvector 확장 설치
brew install pgvector

# DB 접속 후 확장 활성화
psql -U postgres
```

```sql
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

---

**4. 환경변수 설정 (선택)**

기본값은 `config.yaml`을 사용하므로 변경이 필요한 항목만 설정합니다.

```bash
cp .env.example .env
```

`.env` 파일에서 실제 환경에 맞게 수정:

```ini
HIVE_API_BASE_URL=http://실제서버주소:8080
PG_HOST=localhost
PG_USER=postgres
PG_PASSWORD=postgres
```

---

### 실행

**방법 A — 웹 UI (권장)**

```bash
python web_app.py
```

브라우저에서 `http://localhost:8000` 접속

```
[웹 화면 흐름]
로그인 화면 → Username/Password 입력 → 채팅 화면 → 자연어로 질문
```

---

**방법 B — 터미널 CLI**

```bash
python main.py
```

```
[터미널 흐름]
Username: admin
Password: ****
인증 성공
You> public.measure 테이블을 삭제해줘
  [Tool] delete_table({'schema': 'public', 'table_name': 'measure'})
╭── Agent ──────────────────────────────╮
│ public.measure 테이블이 삭제되었습니다. │
╰───────────────────────────────────────╯
```

터미널 명령어:

| 입력 | 동작 |
|------|------|
| 자연어 질문 | Agent에 전달 |
| `reset` | 대화 기록 초기화 |
| `exit` 또는 `quit` | 종료 |

---

### 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/app.log

# 날짜별 롤링 파일
ls logs/
# app.log             ← 오늘
# app.log.2026-02-18  ← 전날
```

---

### 전체 구성 확인

```
Ollama (포트 11434)    ← LLM(qwen2.5:7b) + 임베딩(nomic-embed-text)
PostgreSQL (포트 5432) ← pgvector 벡터 저장소
Hive API (포트 8080)   ← 실제 Hive REST API 서버
web_app.py (포트 8000) ← 웹 UI 서버
```
