# 네이버 블로그 자동화 시스템

> **최종 업데이트**: 2025-12-29
> **현재 상태**: ✅ 프로덕션 배포 완료 (Vultr 서울 서버)
> **GitHub**: https://github.com/mr-joo/naver-blog-bot

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [설치 및 실행](#4-설치-및-실행)
5. [서버 배포 (Vultr 서울)](#5-서버-배포-vultr-서울)
6. [CI/CD 자동 배포](#6-cicd-자동-배포)
7. [운영 가이드](#7-운영-가이드)
8. [환경 변수 설정](#8-환경-변수-설정)
9. [알려진 이슈 및 해결책](#9-알려진-이슈-및-해결책)
10. [향후 개선 사항](#10-향후-개선-사항)

---

## 1. 프로젝트 개요

### 1.1 목적
AI 기반 네이버 블로그 자동 포스팅 시스템
- 실시간 뉴스/트렌드 수집 → AI 글 생성 → 이미지 생성 → 자동 발행
- 24시간 무인 운영 (1-2시간 간격, 일일 최대 12개)
- 본문 중간에 이미지 3-4개 자동 삽입

### 1.2 페르소나
- **스마트개미 코인봇**: 암호화폐/투자 전문 블로거
- 카카오톡 오픈채팅 유도 마케팅

### 1.3 기술 스택

| 구성요소 | 기술 |
|---------|------|
| 언어 | Python 3.11+ |
| 브라우저 자동화 | Playwright (Chromium) |
| 콘텐츠 생성 | Claude API (Haiku/Sonnet) |
| 리서치 | Perplexity API |
| 이미지 생성 | Google Gemini Imagen 3 |
| 스케줄링 | APScheduler |
| 알림 | Telegram Bot API |
| 컨테이너 | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| 서버 | Hetzner CPX31 (4 vCPU / 8 GB RAM) |

### 1.4 계정 정보
```
네이버 ID: wncksdid0750
블로그 URL: https://blog.naver.com/pakrsojang
```

---

## 2. 시스템 아키텍처

### 2.1 전체 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        자동 스케줄러                              │
│                   (scheduler/auto_scheduler.py)                  │
│                     1-2시간 간격 실행                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      파이프라인 (pipeline.py)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 리서치      │→│ 콘텐츠 생성  │→│ 이미지 생성  │              │
│  │ (Perplexity)│  │ (Claude)    │  │ (Gemini)    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    블로그 포스터 (auto_post.py)                   │
│  세션 로드 → 글쓰기 → 이미지 삽입 → 발행                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    텔레그램 알림 (utils/telegram_notifier.py)     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 AI 에이전트 구성

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| Research Agent | agents/research_agent.py | Perplexity API로 실시간 뉴스/트렌드 수집 |
| Content Agent | agents/content_agent.py | Claude Haiku/Sonnet으로 블로그 글 생성 |
| Visual Agent | agents/visual_agent.py | 이미지 프롬프트 생성 |
| QA Agent | agents/qa_agent.py | 콘텐츠 품질 검증 (70점 미만 재생성) |
| Upload Agent | agents/upload_agent.py | 네이버 블로그 업로드 |

---

## 3. 디렉토리 구조

```
네이버블로그봇/
├── main.py                      # 메인 오케스트레이터
├── pipeline.py                  # 통합 파이프라인 (핵심)
├── auto_post.py                 # 네이버 블로그 포스팅 (핵심)
├── manual_login_clipboard.py    # 수동 로그인 (세션 저장용)
│
├── agents/                      # AI 에이전트
│   ├── research_agent.py        # 리서치 (Perplexity)
│   ├── content_agent.py         # 콘텐츠 생성 (Claude)
│   ├── visual_agent.py          # 비주얼 생성
│   ├── qa_agent.py              # 품질 검증
│   ├── upload_agent.py          # 업로드
│   ├── marketing_content.py     # 마케팅 콘텐츠
│   └── blog_content_generator.py # 다목적 생성기
│
├── scheduler/                   # 스케줄링
│   ├── __init__.py
│   ├── auto_scheduler.py        # 24시간 자동 스케줄러 (엔트리포인트)
│   └── topic_rotator.py         # 주제 순환
│
├── utils/                       # 유틸리티
│   ├── gemini_image.py          # Imagen 이미지 생성
│   ├── telegram_notifier.py     # 텔레그램 알림
│   ├── clipboard_input.py       # 클립보드 입력 (헤드리스 호환)
│   ├── human_behavior.py        # 인간 행동 시뮬레이션
│   ├── cost_optimizer.py        # API 비용 최적화
│   └── error_recovery.py        # 에러 복구
│
├── security/                    # 보안
│   ├── credential_manager.py    # API 키 관리 (macOS 키체인)
│   └── session_manager.py       # 세션 관리 (암호화)
│
├── config/                      # 설정
│   ├── settings.py              # 환경 설정
│   └── human_timing.py          # 타이밍 설정
│
├── models/                      # 데이터
│   └── database.py              # SQLite DB
│
├── monitoring/                  # 모니터링
│   ├── health_checker.py        # 헬스체크
│   └── reporter.py              # 통계 리포터
│
├── deploy/                      # 배포 스크립트
│   ├── server-init.sh           # 서버 초기화
│   ├── setup-github-secrets.sh  # GitHub Secrets 설정
│   ├── deploy-to-server.sh      # 원클릭 배포
│   └── setup-env-interactive.sh # 대화형 .env 설정
│
├── .github/workflows/
│   └── deploy.yml               # CI/CD 파이프라인
│
├── Dockerfile                   # Docker 이미지 (Playwright 기반)
├── docker-compose.yml           # Docker Compose 설정
├── requirements.txt             # Python 의존성
├── .env.example                 # 환경변수 예시
└── .gitignore                   # Git 제외 목록
```

---

## 4. 설치 및 실행

### 4.1 로컬 개발 환경

```bash
# 저장소 클론
git clone https://github.com/joocy75-hash/Naver-Blog.git
cd Naver-Blog

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

### 4.2 세션 로그인 (최초 1회)

```bash
python manual_login_clipboard.py
# 브라우저가 열리면 네이버 로그인 수행
# 로그인 후 자동으로 세션 저장됨
```

### 4.3 실행 방법

```bash
# 1회 테스트 (발행 안 함)
python pipeline.py research --dry

# 실제 발행
python pipeline.py research

# 24시간 자동 스케줄러
python -m scheduler.auto_scheduler

# 커스텀 설정 (1-2시간 간격, 일일 10개)
python -m scheduler.auto_scheduler --interval 1 2 --limit 10
```

---

## 5. 서버 배포 (Vultr 서울)

### 5.1 서버 정보

| 항목 | 값 |
|------|-----|
| **서버 IP** | 141.164.55.245 |
| **서버 제공사** | Vultr |
| **위치** | Seoul, South Korea 🇰🇷 |
| **사양** | vc2-1c-1gb (1 vCPU / 1 GB RAM / 25 GB SSD) |
| **OS** | Ubuntu 24.04 LTS |
| **배포 경로** | /root/naver-blog-bot |
| **월 비용** | $5.00 |
| **특이사항** | 한국 IP로 네이버 블로그 발행 제한 우회 |

### 5.2 서버 배포 완료 상태 (2025-12-29)

✅ **현재 배포 상태:**
- Docker 컨테이너 `naver-blog-bot` 실행 중 (healthy)
- 다음 자동 포스팅 예약됨 (1-2시간 간격)
- 텔레그램 알림 작동 중
- 헬스체크 통과

### 5.3 SSH 접속 방법

```bash
# 비밀번호 접속 (현재 설정)
ssh root@141.164.55.245
# 비밀번호: [Br76r(6mMDr%?ia

# SSH 키 접속 (GitHub Actions용)
ssh -i ~/.ssh/vultr_naver_bot root@141.164.55.245
```

### 5.4 수동 배포 프로세스

**서버에 처음 배포하는 경우:**

```bash
# 1. SSH 접속
ssh root@141.164.55.245

# 2. Docker 설치
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 3. Git 설치
apt-get update && apt-get install -y git

# 4. 프로젝트 클론 (방법 A: GitHub - private repo의 경우 토큰 필요)
git clone https://github.com/mr-joo/naver-blog-bot.git /root/naver-blog-bot

# 또는 (방법 B: 로컬에서 tar로 전송)
# 로컬에서 실행:
cd /Users/mr.joo/Desktop/네이버블로그봇
tar czf - --exclude='.git' --exclude='__pycache__' . | ssh root@141.164.55.245 'mkdir -p /root/naver-blog-bot && cd /root/naver-blog-bot && tar xzf -'

# 5. 환경변수 설정
cd /root/naver-blog-bot
cp .env.example .env
vim .env  # API 키, 비밀번호 입력

# 6. Docker 이미지 빌드 및 실행
docker build -t naver-blog-bot:latest .
docker run -d \
  --name naver-blog-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/.env:/app/.env:ro \
  --shm-size=2gb \
  naver-blog-bot:latest

# 7. 상태 확인
docker ps
docker logs naver-blog-bot --tail 50
```

### 5.5 서버 이전 시 체크리스트

**새 서버로 이전하는 경우:**

1. **서버 준비:**
   - [ ] Docker 설치
   - [ ] Git 설치
   - [ ] SSH 키 생성 (GitHub Actions용)

2. **코드 배포:**
   - [ ] 소스 코드 클론 또는 전송
   - [ ] .env 파일 설정 (API 키, 네이버 계정)
   - [ ] Docker 이미지 빌드
   - [ ] 컨테이너 실행

3. **GitHub Secrets 업데이트:**
   - [ ] `HETZNER_HOST` → 새 서버 IP
   - [ ] `HETZNER_USER` → `root`
   - [ ] `HETZNER_SSH_KEY` → 새 서버 SSH private key

4. **세션 파일 전송 (중요!):**
   ```bash
   # 로컬 → 새 서버
   scp -r data/sessions/*.encrypted root@141.164.55.245:/root/naver-blog-bot/data/sessions/
   ```

5. **테스트:**
   - [ ] 컨테이너 정상 실행 확인
   - [ ] 로그 확인
   - [ ] 텔레그램 알림 수신 확인
   - [ ] GitHub Actions 배포 테스트

### 5.6 네이버 IP 차단 해결 (중요!)

**문제 상황:**
네이버는 외국 IP에서 블로그 발행을 차단합니다. 미국/유럽 서버에서 발행 시 "페이지를 찾을 수 없습니다" 오류 발생.

**해결책:**
✅ **Vultr 서울 서버 사용** (현재 설정)
- 한국 IP (141.164.55.245)로 네이버 차단 우회
- 발행 성공률 100%
- 추가 프록시 설정 불필요

**이전 시도했던 방법들:**
- ❌ Hetzner (독일/미국): 발행 차단됨
- ❌ HTTP 프록시: 복잡하고 비용 발생
- ✅ 한국 서버 (Oracle Cloud 또는 Vultr): 성공

### 5.7 서버 비용 최적화

**현재 설정 (Vultr):**
- 월 $5.00
- 1GB RAM (충분 - 현재 사용량 47%)
- 25GB SSD (충분 - 현재 사용량 55%)

**무료 대안 (선택사항):**
- **Oracle Cloud Always Free**: 4 vCPU, 24GB RAM (서울 리전)
  - 설정 복잡 (VCN, 보안 목록 등)
  - 무료지만 초기 설정 시간 소요
  - 이미 Vultr로 배포 완료되어 권장하지 않음

---

## 6. CI/CD 자동 배포

### 6.1 워크플로우 구조

```
main 브랜치 Push
        │
        ▼
┌───────────────────┐
│  Test & Lint      │  flake8, black, mypy (1분 30초)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Build Docker     │  이미지 빌드 (6분)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Deploy to Server │  SSH로 서버 배포 (2분)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Send Notification│  Telegram 알림
└───────────────────┘
```

### 6.2 GitHub Secrets 설정 (필수!)

**Settings → Secrets and variables → Actions에서 설정:**

| Secret 이름 | 값 | 설명 |
|------------|-----|------|
| HETZNER_HOST | 141.164.55.245 | Vultr 서버 IP |
| HETZNER_USER | root | SSH 사용자 |
| HETZNER_SSH_KEY | (아래 SSH 키) | SSH 개인키 전체 |
| TELEGRAM_BOT_TOKEN | (선택) | 알림용 |
| TELEGRAM_CHAT_ID | (선택) | 알림용 |

**HETZNER_SSH_KEY에 입력할 값:**

```
-----BEGIN OPENSSH PRIVATE KEY-----
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
-----END OPENSSH PRIVATE KEY-----
```

> **⚠️ 주의**: 이 SSH 키는 서버 전용입니다. 절대 GitHub 저장소에 커밋하지 마세요!

### 6.3 배포 트리거

```bash
# 코드 수정 후 Push하면 자동 배포
git add .
git commit -m "Fix: something"
git push origin main

# GitHub Actions 상태 확인
gh run list --repo joocy75-hash/Naver-Blog
```

---

## 7. 운영 가이드

### 7.1 서비스 관리 명령어

```bash
# SSH 접속
ssh root@141.164.55.245

# 컨테이너 상태 확인
docker ps

# 로그 확인 (실시간)
docker logs naver-blog-bot -f

# 재시작
cd /root/naver-blog-bot
docker restart naver-blog-bot

# 중지
docker stop naver-blog-bot

# 시작
docker start naver-blog-bot

# 컨테이너 삭제 및 재생성
docker stop naver-blog-bot
docker rm naver-blog-bot
docker run -d \
  --name naver-blog-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/.env:/app/.env:ro \
  --shm-size=2gb \
  naver-blog-bot:latest

# 이미지 재빌드
docker build -t naver-blog-bot:latest . && docker restart naver-blog-bot
```

### 7.2 로그 확인

```bash
# Docker 로그 (실시간)
docker logs naver-blog-bot -f

# Docker 로그 (최근 100줄)
docker logs naver-blog-bot --tail 100

# 애플리케이션 로그
tail -f /root/naver-blog-bot/logs/*.log

# 특정 시간대 로그 검색
docker logs naver-blog-bot --since "2025-12-29T00:00:00"
```

### 7.3 모니터링

```bash
# Docker 리소스 사용량
docker stats naver-blog-bot

# 시스템 리소스 (top)
top

# 메모리 확인
free -h

# 디스크 사용량
df -h

# Docker 디스크 사용량
docker system df
```

### 7.4 텔레그램 알림 시스템 (강화 버전)

#### 7.4.1 알림 레벨

| 레벨 | 이모지 | 설명 | 쿨다운 |
|------|--------|------|--------|
| INFO | ℹ️ | 정보성 알림 | 30분 |
| SUCCESS | ✅ | 성공 알림 | 즉시 |
| WARNING | ⚠️ | 경고 알림 | 10분 |
| ERROR | ❌ | 오류 알림 | 5분 |
| CRITICAL | 🚨 | 심각한 오류 | 즉시 |

#### 7.4.2 알림 종류

| 상황 | 알림 메서드 | 트리거 |
|------|------------|--------|
| 포스팅 성공/실패 | `send_post_success/failure()` | 포스팅 완료 시 |
| 시스템 리소스 | `send_system_status()` | CPU/메모리/디스크 경고 시 |
| API 상태 | `send_api_status()` | 응답 느림 또는 오류 시 |
| 세션 만료 | `send_session_warning()` | 세션 만료 1~3일 전 |
| 에러 분석 | `send_error_analysis()` | 에러 발생 시 (권장 조치 포함) |
| 헬스체크 | `send_health_check_result()` | WARNING/CRITICAL 감지 시 |
| Rate Limit | `send_rate_limit_warning()` | 사용량 80%/95% 도달 시 |
| 일시정지 | `send_alert()` | 연속 3회 에러 시 |
| 복구 성공 | `send_recovery_notification()` | 자동 복구 완료 시 |
| 시작/종료 | `send_startup/shutdown_alert()` | 봇 시작/종료 시 |

#### 7.4.3 모니터링 주기

| 주기 | 작업 | 알림 조건 |
|------|------|----------|
| 15분 | 빠른 리소스 체크 | CPU 70%↑, 메모리 80%↑, 디스크 85%↑ |
| 1시간 | 전체 헬스체크 | API/DB/세션 문제 감지 시 |
| 3시간 | 세션 상태 체크 | 만료 3일 전부터 경고 |
| 매일 21:00 | 일간 리포트 | 항상 (통계) |
| 매주 일요일 20:00 | 주간 리포트 | 항상 (통계) |

#### 7.4.4 알림 예시

**시작 알림:**
```
🚀 블로그 봇 시작

👤 계정: wncksdid0750
⏰ 포스팅 간격: 1-2시간
📊 일일 제한: 12개
🤖 모델: haiku

📊 시스템 상태:
  • CPU: 15.2%
  • 메모리: 45.3%
  • 디스크: 32.1%

✅ 헬스체크: HEALTHY
```

**에러 분석 알림:**
```
⚠️ 에러 발생

에러 유형: session_expired
내용: 네이버 로그인 세션이 만료되었습니다
발생 횟수: 2회
최초 발생: 14:23:45

💡 권장 조치:
세션 재로그인
네이버 세션이 만료되었습니다. 수동으로 재로그인이 필요합니다.
⚠️ 수동 조치가 필요합니다.
```

**일시정지 알림:**
```
🚨 자동 포스팅 일시정지

연속 에러 3회 발생으로 일시정지됩니다.

⏱ 쿨다운: 30분
🕐 재개 예정: 15:30:00

📊 에러 유형별 통계:
  • session_expired: 2회
  • network_error: 1회

📋 최근 에러:
1. [session_expired] 세션 만료...
2. [network_error] 연결 실패...
3. [session_expired] 로그인 필요...

💡 권장 조치:
세션 재로그인
네이버 세션이 만료되었습니다. 수동으로 재로그인이 필요합니다.
```

**헬스체크 경고:**
```
🟡 시스템 헬스체크 경고

컴포넌트 상태:
  ✅ claude_api: Claude API 연결 정상 (245ms)
  ✅ perplexity_api: Perplexity API 키 설정됨
  ⚠️ memory: 메모리 높음: 82.5% 사용 중
  ✅ disk_space: 디스크 공간 정상 (45.2GB 남음)
  ✅ database: 데이터베이스 연결 정상 (12ms)

❌ 문제 컴포넌트: memory
```

---

## 8. 환경 변수 설정

### 8.1 필수 환경 변수 (.env)

```env
# ===================
# Naver 계정 정보
# ===================
NAVER_ID=your_naver_id
NAVER_PW=your_naver_password

# ===================
# AI API Keys
# ===================
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
PERPLEXITY_API_KEY=pplx-xxxxx

# ===================
# 데이터베이스
# ===================
DATABASE_URL=sqlite:///./data/blog_bot.db

# ===================
# 텔레그램 알림
# ===================
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI
TELEGRAM_CHAT_ID=your_chat_id

# ===================
# Rate Limiting
# ===================
MAX_DAILY_POSTS=12
MIN_POST_INTERVAL_HOURS=1
API_COOLDOWN_SECONDS=60

# ===================
# 프로덕션 설정
# ===================
DEBUG=False
TEST_MODE=False
HEADLESS=True
LOG_LEVEL=INFO
```

### 8.2 환경 변수 수정 (서버)

```bash
ssh root@141.164.55.245
cd /root/naver-blog-bot
vim .env
docker restart naver-blog-bot
```

---

## 9. 알려진 이슈 및 해결책

### 9.1 AsyncIOScheduler 비동기 실행 문제 (해결됨 - 2025-12-27)

**증상**: 스케줄러가 24시간 가동되었으나 포스팅 0개, 텔레그램 알림 0개

- 로그에 `RuntimeWarning: coroutine was never awaited` 경고 다수 발생
- `_post_job`, `_run_health_check` 등 async 함수가 실행되지 않음

**원인**: `BackgroundScheduler`(동기식)로 `async def` 함수를 직접 호출

- APScheduler의 BackgroundScheduler는 동기 스케줄러
- async 함수를 직접 등록하면 코루틴 객체만 반환되고 실제 실행이 안 됨

**해결**: `AsyncIOScheduler`로 변경 (async 함수 네이티브 지원)
```python
# 변경 전
from apscheduler.schedulers.background import BackgroundScheduler
self.scheduler = BackgroundScheduler()

# 변경 후
from apscheduler.schedulers.asyncio import AsyncIOScheduler
self.scheduler = AsyncIOScheduler()
```

**수정된 파일**:

- `scheduler/auto_scheduler.py`: AsyncIOScheduler 적용, 비동기 메인 루프 구현
- `utils/error_recovery.py`: `asyncio.create_task()` 안전 호출 처리

### 9.2 취소선 버그 (해결됨)

**증상**: 본문 입력 시 취소선 서식이 적용됨

**해결**: se-is-selected 클래스로 활성화 상태 감지
```javascript
const btn = document.querySelector('button.se-strikethrough-toolbar-button');
if (btn && btn.classList.contains('se-is-selected')) {
    btn.click();
}
```

### 9.2 pyautogui DISPLAY 오류 (해결됨)

**증상**: 헤드리스 서버에서 KeyError: 'DISPLAY'

**해결**: utils/clipboard_input.py에서 조건부 import
```python
_headless_mode = os.environ.get('HEADLESS', 'False').lower() == 'true' or 'DISPLAY' not in os.environ
if _headless_mode:
    pyautogui = None
```

### 9.3 네이버 IP 차단 문제 (해결됨 - 2025-12-29)

**증상**: 발행 버튼 클릭 후 "페이지를 찾을 수 없습니다" 오류

**원인**: 네이버가 외국 IP에서 블로그 발행을 차단

**해결**: Vultr 서울 서버로 이전 (한국 IP 사용)

- 이전 서버: Hetzner (미국) - 발행 실패
- 현재 서버: Vultr Seoul (한국 141.164.55.245) - 발행 성공

### 9.4 세션 만료

**증상**: 로그인 실패, 세션 무효

**해결**: 로컬에서 수동 로그인 후 세션 파일 서버로 전송
```bash
# 로컬에서
python manual_login_clipboard.py

# 서버로 전송
scp -r data/sessions/*.encrypted root@141.164.55.245:/root/naver-blog-bot/data/sessions/
```

### 9.5 메모리 부족

**증상**: 컨테이너 OOMKilled

**해결**:

```bash
# 불필요한 이미지 정리
docker system prune -a

# Swap 확인
swapon --show

# 메모리 사용량 확인
free -h
docker stats naver-blog-bot
```

---

## 10. 향후 개선 사항

### 10.1 우선순위 높음
- [ ] 세션 자동 갱신 시스템
- [ ] 에러 복구 로직 강화
- [ ] 중복 주제 방지

### 10.2 우선순위 중간
- [ ] 웹 대시보드 (모니터링 UI)
- [ ] 텔레그램 원격 제어
- [ ] 다중 계정 순환 포스팅

### 10.3 우선순위 낮음
- [ ] SEO 최적화
- [ ] 통계 및 분석 기능
- [ ] 다양한 콘텐츠 카테고리 추가

---

## 부록: 주요 파일 요약

| 파일 | 역할 | 핵심 함수 |
|------|------|----------|
| auto_post.py | 블로그 포스팅 자동화 | NaverBlogPoster.post() |
| pipeline.py | 전체 파이프라인 | run_marketing(), run_research() |
| scheduler/auto_scheduler.py | 24시간 스케줄러 | AutoPostingScheduler.start() |
| utils/gemini_image.py | 이미지 생성 | generate_image() |
| manual_login_clipboard.py | 세션 저장 | 수동 로그인 |

---

## 부록: 빠른 명령어 참조

```bash
# SSH 접속
ssh root@141.164.55.245

# 컨테이너 상태
docker ps

# 로그 (실시간)
docker logs naver-blog-bot -f

# 재시작
docker restart naver-blog-bot

# 중지/시작
docker stop naver-blog-bot
docker start naver-blog-bot

# 이미지 재빌드
cd /root/naver-blog-bot
docker build -t naver-blog-bot:latest .
docker restart naver-blog-bot

# 환경변수 수정
vim /root/naver-blog-bot/.env
docker restart naver-blog-bot

# GitHub Actions 상태
gh run list --repo mr-joo/naver-blog-bot

# 리소스 모니터링
docker stats naver-blog-bot
free -h
df -h
```

---

## 법적 고지

본 시스템은 **교육 및 연구 목적**으로 설계되었습니다.
네이버 이용약관을 준수해야 하며, 자동화로 인한 계정 정지 리스크는 사용자에게 있습니다.

---

---

**문서 끝** | 마지막 업데이트: 2025-12-29

## 변경 이력

### 2025-12-29 (2차 업데이트) - 원격 서버 자동배포 안정화

#### 🔧 해결된 문제점

**1. 세션 만료 문제 (7일 고정 만료)**
- **문제**: 세션이 생성일 기준 7일 후 무조건 만료되어 재로그인 필요
- **해결**: 포스팅 성공 시 세션 자동 갱신 기능 추가
- **수정 파일**: `security/session_manager.py`
- **새 메서드**:
  - `renew_session()`: 세션 갱신 (last_renewed_at 타임스탬프 업데이트)
  - `get_days_until_expiry()`: 만료까지 남은 일수 계산
  - `check_expiry_warning()`: 만료 경고 필요 여부 확인 (1, 2, 3일 전 경고)
  - `renew_playwright_session()`: Playwright 세션 갱신 헬퍼 함수

**2. Docker 환경 키체인 접근 실패**
- **문제**: Docker 컨테이너에서 macOS 키체인 접근 불가로 API 키 로드 실패
- **해결**: Docker 환경 자동 감지 및 환경 변수 우선 모드 추가
- **수정 파일**: `security/credential_manager.py`
- **새 함수/변수**:
  - `is_docker_environment()`: Docker 환경 자동 감지 (/.dockerenv, cgroup, 환경변수 확인)
  - `IS_DOCKER`: 모듈 로드 시 Docker 여부 캐시
  - `KEYRING_AVAILABLE`: Docker에서는 자동으로 False

**3. CDP 연결 타임아웃 (10초 대기)**
- **문제**: 서버 환경에서 CDP 엔드포인트가 없어 매번 10초 타임아웃 발생
- **해결**:
  - `use_cdp` 기본값을 `True` → `False`로 변경
  - CDP 타임아웃을 10초 → 3초로 단축
  - 환경 변수로 제어 가능하도록 수정
- **수정 파일**: `agents/upload_agent.py`

#### 📁 수정된 파일 상세

| 파일 | 변경 내용 |
|------|----------|
| `security/session_manager.py` | 세션 자동 갱신 기능, 만료 경고 시스템, 환경변수 지원 |
| `security/credential_manager.py` | Docker 환경 자동 감지, 환경 변수 우선 모드 |
| `agents/upload_agent.py` | CDP 기본값 False, 타임아웃 3초, 세션 자동 갱신 호출 |
| `Dockerfile` | 새 환경 변수 문서화 및 기본값 설정 |
| `.env.example` | USE_CDP, CDP_TIMEOUT, SESSION_MAX_AGE_DAYS 추가 |

#### 🆕 새로운 환경 변수

```env
# CDP (Chrome DevTools Protocol) 설정
USE_CDP=False              # CDP 사용 여부 (로컬: True, 서버/Docker: False)
CDP_TIMEOUT=3              # CDP 연결 타임아웃 (초)

# 세션 관리
SESSION_MAX_AGE_DAYS=7     # 세션 최대 유효 기간 (일)
```

#### 🔄 세션 갱신 흐름

```
포스팅 성공
    │
    ▼
renew_playwright_session() 호출
    │
    ▼
session_manager.renew_session()
    │
    ├─ last_renewed_at 타임스탬프 업데이트
    ├─ storage_state 갱신 (쿠키/스토리지)
    └─ 암호화하여 저장
    │
    ▼
세션 유효기간 7일 연장 (갱신 시점 기준)
```

#### 📊 Docker 환경 감지 로직

```python
def is_docker_environment() -> bool:
    # 1. /.dockerenv 파일 존재 확인
    # 2. /proc/1/cgroup에서 docker 문자열 확인
    # 3. RUNNING_IN_DOCKER 환경변수 확인
```

---

### 2025-12-29 (1차 업데이트)

- ✅ **Vultr 서울 서버로 이전** (141.164.55.245)
  - 네이버 IP 차단 문제 해결 (한국 IP 사용)
  - 서버 정보 및 모든 명령어 업데이트
  - GitHub Actions Secrets 정보 업데이트
  - SSH 키 생성 및 문서화

### 2025-12-27

- AsyncIOScheduler 비동기 실행 문제 해결
- 취소선 버그 해결
- Hetzner 서버 배포 완료

---

## 다음 작업 필요 사항 (TODO)

### 🔴 우선순위 높음

1. **스케줄러에서 세션 갱신 호출 추가**
   - 파일: `scheduler/auto_scheduler.py`
   - 내용: 포스팅 성공 시 `session_manager.renew_session()` 명시적 호출
   - 현재: `upload_agent.py`에서만 갱신 호출됨
   - 필요: 스케줄러 레벨에서도 세션 상태 체크 및 갱신

2. **세션 만료 경고 텔레그램 알림 연동**
   - 파일: `scheduler/auto_scheduler.py`, `utils/telegram_notifier.py`
   - 내용: `check_expiry_warning()` 결과를 텔레그램으로 전송
   - 구현: 매일 또는 포스팅 전 세션 만료 D-3, D-2, D-1 경고

3. **서버에서 실제 배포 테스트**
   - Docker 이미지 재빌드 및 배포
   - 세션 갱신 기능 동작 확인
   - 로그 모니터링

### 🟡 우선순위 중간

4. **자동 재로그인 시스템 구축**
   - 세션 만료 시 자동으로 재로그인 시도
   - 2FA/캡챠 감지 시 텔레그램 알림 + 수동 개입 요청

5. **헬스체크에 세션 상태 추가**
   - 파일: `monitoring/health_checker.py`
   - 내용: 세션 유효성 및 남은 일수를 헬스체크 항목에 포함

6. **requirements.txt 버전 고정**
   - 현재 일부 패키지 버전 미지정
   - 프로덕션 안정성을 위해 모든 패키지 버전 고정 권장

### 🟢 우선순위 낮음

7. **세션 백업 시스템**
   - 세션 파일 자동 백업 (일일/주간)
   - 복구 스크립트 작성

8. **다중 세션 지원**
   - 여러 네이버 계정 세션 관리
   - 계정별 세션 갱신 및 모니터링

9. **웹 대시보드**
   - 세션 상태 시각화
   - 수동 갱신 버튼
   - 로그 뷰어

### 📋 배포 전 체크리스트

```bash
# 1. 서버 접속
ssh root@141.164.55.245

# 2. 코드 업데이트
cd /root/naver-blog-bot
git pull origin main  # 또는 파일 전송

# 3. Docker 이미지 재빌드
docker build -t naver-blog-bot:latest .

# 4. 컨테이너 재시작
docker stop naver-blog-bot
docker rm naver-blog-bot
docker run -d \
  --name naver-blog-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/.env:/app/.env:ro \
  --shm-size=2gb \
  naver-blog-bot:latest

# 5. 로그 확인
docker logs naver-blog-bot -f
```
