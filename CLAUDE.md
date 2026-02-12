# Naver Blog Automation - Claude Code Instructions

## Project Overview
- 네이버 블로그 자동 포스팅 시스템 (AI 콘텐츠 생성 + 브라우저 자동화)
- Stack: Python 3.11, Patchright, Claude/Gemini API, SQLAlchemy, Docker
- Deploy: Docker on Hetzner VPS

## Browser Automation: Patchright (NOT Playwright)

### 2026-02-12 마이그레이션 완료: Playwright → Patchright

**Patchright**는 Playwright의 anti-detection 포크로, CDP(Chrome DevTools Protocol) leak을 차단하여 네이버 봇 감지를 우회한다.

**절대 `playwright`로 되돌리지 말 것.** 네이버 로그인 시 봇 감지 문제가 재발한다.

### 변경된 파일 (9개)

| 파일 | 변경 내용 |
|------|-----------|
| `requirements.txt` | `playwright` + `playwright-stealth` 제거 → `patchright>=1.57.0` |
| `Dockerfile` | `mcr.microsoft.com/playwright` 이미지 → `python:3.11-slim-bookworm` + `patchright install --with-deps chromium` |
| `auto_post.py` | import 전환 + `playwright_stealth` 의존성 제거 + stealth JS 패치 코드 제거 |
| `agents/upload_agent.py` | import 전환 + `navigator.webdriver` 패치 제거 |
| `manual_login.py` | import 전환 + `add_init_script` webdriver 패치 제거 |
| `manual_login_clipboard.py` | import 전환 |
| `debug_toolbar.py` | import 전환 |
| `debug_strikethrough_exact.py` | import 전환 |
| `debug_title.py` | import 전환 |
| `debug_inline_toolbar.py` | import 전환 |
| `.claude/skills/.../test-headless.py` | import 전환 |

### 핵심 규칙

```python
# O 올바른 import
from patchright.async_api import async_playwright

# X 사용 금지
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
```

### Patchright가 자체 처리하는 것 (추가 코드 불필요)
- `navigator.webdriver` 속성 숨김
- CDP Runtime.enable 호출 차단 (핵심 anti-detection)
- 브라우저 핑거프린트 정규화

### 브라우저 설치 명령
```bash
# 로컬
pip install patchright
patchright install chromium

# Docker (Dockerfile에 이미 포함)
patchright install --with-deps chromium
```

## Architecture

### Entry Points
- `scheduler/auto_scheduler.py` - Docker CMD (24/7 자동화)
- `main.py` - 5단계 파이프라인 오케스트레이터
- `pipeline.py` - 통합 파이프라인 CLI

### Key Modules
- `auto_post.py` - 네이버 스마트에디터 브라우저 자동화 (2800줄, 리팩토링 필요)
- `agents/` - 리서치, 콘텐츠, 이미지, QA, 업로드 에이전트
- `security/session_manager.py` - Fernet 암호화 세션 관리
- `security/credential_manager.py` - 키체인/환경변수 자격증명 관리
- `config/human_timing.py` - 봇 감지 회피용 딜레이 설정
- `utils/clipboard_input.py` - 클립보드 기반 텍스트 입력 (fill() 대안)

### Session Flow
1. `manual_login.py` 로 수동 로그인 (캡차/2FA 직접 처리)
2. 세션 암호화 저장 (`data/sessions/*.session.encrypted`)
3. `auto_post.py` / `upload_agent.py`가 저장된 세션으로 브라우저 시작
4. 포스팅 성공 시 세션 자동 갱신 (유효기간 연장)
5. 세션 만료 시 텔레그램 알림 → 수동 재로그인

## Code Style
- Python 3.11+, async/await 기반
- loguru 로깅 (한국어 메시지)
- 변수명: snake_case
- 코드 주석: 영어
- 커밋 메시지: 한국어

## Don'ts
- `playwright` 패키지로 되돌리지 않기
- `navigator.webdriver` JS 패치 추가하지 않기 (Patchright가 처리)
- 하드코딩된 네이버 ID (`wncksdid0750`) 추가하지 않기 → 환경변수 사용
- `except:` (bare except) 사용하지 않기 → `except Exception:` 이상 사용
- Chrome UA 버전을 120으로 고정하지 않기 → 최신 버전 유지
