# 네이버 블로그 자동 포스팅 봇 - 배포 가이드

## 개요

이 프로젝트는 AI를 활용하여 네이버 블로그에 자동으로 포스팅하는 봇입니다.
24시간 스케줄러가 1~2시간 간격으로 암호화폐 관련 콘텐츠를 자동 생성하고 포스팅합니다.

---

## 서버 정보

| 항목 | 값 |
|------|-----|
| 호스팅 | DigitalOcean Droplet |
| 서버 이름 | Deep |
| IP 주소 | `152.42.169.132` |
| OS | Ubuntu 22.04 LTS |
| 사양 | 1GB RAM / 25GB Disk |
| SSH 접속 | `ssh root@152.42.169.132` |

---

## 프로젝트 구조

```
/opt/naver-blog-bot/          # 서버 배포 경로
├── scheduler/
│   ├── auto_scheduler.py     # 메인 스케줄러 (24시간 자동 포스팅)
│   └── topic_rotator.py      # 토픽 로테이션
├── automation/
│   ├── browser_controller.py # Playwright 브라우저 제어
│   └── naver_poster.py       # 네이버 블로그 포스팅
├── content/
│   └── blog_generator.py     # AI 콘텐츠 생성
├── security/
│   └── session_manager.py    # 네이버 세션 관리 (암호화)
├── monitoring/
│   ├── health_checker.py     # 헬스체크
│   └── reporter.py           # 통계 리포트
├── models/
│   └── database.py           # SQLite 데이터베이스
├── utils/
│   ├── telegram_notifier.py  # 텔레그램 알림
│   └── error_recovery.py     # 에러 복구
├── data/                     # 데이터베이스 파일
├── logs/                     # 로그 파일
├── secrets/                  # 암호화 키 (encryption.key)
├── sessions/                 # 네이버 세션 파일 (암호화됨)
├── .env                      # 환경 변수
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 환경 변수 (.env)

```env
# Database
DATABASE_URL=sqlite:///./data/blog_bot.db
ENCRYPTION_KEY_PATH=./secrets/encryption.key

# Rate Limiting
MAX_DAILY_POSTS=3
MIN_POST_INTERVAL_HOURS=6

# Behavior Simulation (봇 탐지 우회)
HEADLESS=True                 # 서버에서는 반드시 True
TYPING_SPEED_MIN_MS=80
TYPING_SPEED_MAX_MS=180

# Telegram 알림
ENABLE_ALERTS=True
TELEGRAM_BOT_TOKEN=<텔레그램_봇_토큰>
TELEGRAM_CHAT_ID=<텔레그램_채팅_ID>

# API Keys
ANTHROPIC_API_KEY=<Claude_API_키>
GEMINI_API_KEY=<Gemini_API_키>
PERPLEXITY_API_KEY=<Perplexity_API_키>

# Content Settings
BLOG_CATEGORY=암호화폐
DEFAULT_TAGS=비트코인,암호화폐,AI자동매매,투자
```

---

## Docker 설정

### Dockerfile 주요 내용

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

# 한글 폰트 및 가상 디스플레이
RUN apt-get install -y fonts-nanum xvfb python3-tk

# 가상 디스플레이 설정 (Headless 브라우저용)
ENV DISPLAY=:99
ENV XAUTHORITY=/tmp/.Xauthority

# 시작 스크립트 (Xvfb 실행 후 스케줄러 시작)
CMD ["/app/start.sh"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  blog-bot:
    build: .
    container_name: naver-blog-bot
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./secrets:/app/secrets
      - ./sessions:/app/sessions
    environment:
      - TZ=Asia/Seoul
```

---

## 운영 명령어

### 서버 접속
```bash
ssh root@152.42.169.132
cd /opt/naver-blog-bot
```

### 컨테이너 관리
```bash
# 상태 확인
docker ps

# 로그 확인
docker logs naver-blog-bot
docker logs -f naver-blog-bot        # 실시간 로그

# 컨테이너 재시작
docker-compose restart

# 컨테이너 중지/시작
docker-compose down
docker-compose up -d

# 재빌드 (코드 변경 시)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 디스크 정리 (공간 부족 시)
```bash
docker system prune -af --volumes
docker builder prune -af
```

---

## 스케줄러 동작 방식

1. **시작**: 컨테이너 시작 시 `scheduler/auto_scheduler.py` 실행
2. **포스팅 주기**: 1~2시간 랜덤 간격
3. **일일 제한**: 최대 12개 포스팅
4. **헬스체크**: 30분마다 시스템 상태 확인
5. **알림**: 포스팅 성공/실패 시 텔레그램 알림

### 로그 예시
```
🚀 24시간 자동 포스팅 스케줄러 시작
   네이버 ID: wncksdid0750
   포스팅 간격: 1.0-2.0시간
   일일 제한: 12개
   모델: haiku
   텔레그램 알림: ON
⏰ 다음 포스팅 예정: 12:23:07 (1.1시간 후)
```

---

## 네이버 세션 관리

세션은 암호화되어 `/opt/naver-blog-bot/sessions/` 에 저장됩니다.

### 현재 등록된 세션
- `wncksdid0750_clipboard`
- `wncksdid0750_manual`

### 세션 갱신 필요 시
세션이 만료되면 로컬에서 로그인 후 세션 파일을 서버로 업로드해야 합니다.

```bash
# 로컬에서 서버로 세션 파일 전송
rsync -avz ./sessions/ root@152.42.169.132:/opt/naver-blog-bot/sessions/
```

---

## 알려진 이슈

### 1. httpx 버전 충돌 (WARNING)
- `google-genai`는 `httpx>=0.28.1` 요구
- `python-telegram-bot`은 `httpx~=0.25.2` 요구
- **현재 설정**: httpx 0.25.2 (텔레그램 우선)
- **영향**: google-genai에서 경고 발생하지만 기능은 정상 작동

### 2. Python 버전 경고
- Python 3.10.12 사용 중
- Google API에서 2026-10-04 이후 지원 중단 경고
- **조치 필요**: 추후 Python 3.11+ 업그레이드 권장

---

## 트러블슈팅

### 컨테이너가 시작되지 않을 때
```bash
docker logs naver-blog-bot
```

### 디스크 공간 부족
```bash
df -h /
docker system prune -af
```

### 포스팅이 안 될 때
1. 네이버 세션 만료 확인
2. API 키 유효성 확인
3. 네트워크 연결 확인

### Xvfb 관련 에러
```bash
# 컨테이너 내부에서 확인
docker exec naver-blog-bot ps aux | grep Xvfb
```

---

## 배포 체크리스트

- [ ] SSH 접속 확인
- [ ] Docker 실행 확인 (`docker ps`)
- [ ] 로그에 에러 없는지 확인
- [ ] 다음 포스팅 예약 시간 확인
- [ ] 디스크 공간 5GB 이상 확인
- [ ] 텔레그램 알림 수신 확인

---

## 연락처

문제 발생 시 텔레그램으로 알림이 전송됩니다.
- 텔레그램 채팅 ID: `7980845952`

---

## 최종 배포 일시

**2025-12-26 11:15 KST**

- 상태: 정상 운영 중
- 컨테이너: `naver-blog-bot` (healthy)
- 다음 포스팅: 스케줄러에 의해 자동 예약됨
