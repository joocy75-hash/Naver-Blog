# 네이버 블로그 자동화 시스템 - 배포 가이드

## 서버 정보

| 항목 | 값 |
|------|-----|
| 서버 IP | 5.161.112.248 |
| 서버 이름 | deep-server |
| 위치 | Ashburn, VA (USA) |
| 사양 | CPX31 (4 vCPU / 8 GB RAM / 160 GB SSD) |
| OS | Ubuntu 24.04 LTS |
| 배포 그룹 | Group B (Personal Automation) |

---

## 아키텍처 개요

```
Hetzner CPX31 (8GB RAM)
├── Group A: Freqtrade Service (격리)
├── Group B: Personal Automation ← 네이버 블로그 봇
│   ├── naver-blog-bot (2GB)
│   ├── sports-analysis
│   └── tradingview-collector
└── Group C: AI Trading Platform (격리)
```

---

## 1단계: 서버 초기 설정

### 1.1 SSH 접속

```bash
ssh root@5.161.112.248
```

### 1.2 초기 설정 스크립트 실행

```bash
# 스크립트 다운로드 및 실행
curl -sSL https://raw.githubusercontent.com/joocy75-hash/Naver-Blog/main/deploy/server-init.sh | bash
```

또는 수동으로:

```bash
# 저장소 클론
git clone https://github.com/joocy75-hash/Naver-Blog.git ~/temp-repo
cd ~/temp-repo

# 스크립트 실행
chmod +x deploy/server-init.sh
./deploy/server-init.sh
```

이 스크립트가 수행하는 작업:
- 시스템 패키지 업데이트
- Docker & Docker Compose 설치
- 2GB Swap 파일 생성
- UFW 방화벽 설정
- Fail2Ban 설치
- 서비스 디렉토리 구조 생성
- 시스템 최적화

---

## 2단계: GitHub Secrets 설정

### 2.1 SSH 키 생성 (로컬에서)

```bash
# 로컬 머신에서 실행
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/hetzner_deploy

# 공개키를 서버에 추가
ssh-copy-id -i ~/.ssh/hetzner_deploy.pub root@5.161.112.248
```

### 2.2 GitHub Secrets 추가

GitHub 저장소 → Settings → Secrets and variables → Actions

| Secret 이름 | 값 | 설명 |
|------------|-----|------|
| `HETZNER_HOST` | `5.161.112.248` | 서버 IP |
| `HETZNER_USER` | `root` | SSH 사용자 |
| `HETZNER_SSH_KEY` | (개인키 내용) | `~/.ssh/hetzner_deploy` 파일 내용 |
| `TELEGRAM_BOT_TOKEN` | (선택) | Telegram 알림용 |
| `TELEGRAM_CHAT_ID` | (선택) | Telegram 채팅 ID |

### 2.3 SSH 키 내용 복사

```bash
# 개인키 내용 복사
cat ~/.ssh/hetzner_deploy
```

이 내용 전체를 `HETZNER_SSH_KEY` Secret에 붙여넣기

---

## 3단계: 환경 변수 설정

### 3.1 서버에서 .env 파일 생성

```bash
ssh root@5.161.112.248

cd ~/service_b/naver-blog-bot
cp .env.example .env
vim .env
```

### 3.2 필수 환경 변수

```env
# Naver 계정
NAVER_ID=your_naver_id
NAVER_PW=your_naver_password

# AI API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
GCP_PROJECT_ID=your-project-id
PERPLEXITY_API_KEY=pplx-xxxxx

# 데이터베이스
DATABASE_URL=sqlite:///./data/blog_bot.db

# 텔레그램 알림
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI
TELEGRAM_CHAT_ID=your_chat_id

# 프로덕션 설정
DEBUG=False
TEST_MODE=False
HEADLESS=True
```

---

## 4단계: 배포

### 4.1 자동 배포 (권장)

GitHub에 코드를 push하면 자동으로 배포됩니다:

```bash
git add .
git commit -m "Deploy to Hetzner"
git push origin main
```

### 4.2 수동 배포

GitHub Actions 페이지에서 "Run workflow" 버튼 클릭

### 4.3 배포 확인

```bash
ssh root@5.161.112.248

# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs naver-blog-bot -f

# 서비스 상태
cd ~/service_b/naver-blog-bot
docker-compose ps
```

---

## 5단계: 운영 가이드

### 5.1 서비스 관리 명령어

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 재시작
docker-compose restart

# 로그 확인 (실시간)
docker-compose logs -f

# 컨테이너 접속
docker exec -it naver-blog-bot bash
```

### 5.2 리소스 모니터링

```bash
# Docker 리소스 사용량
docker stats

# 시스템 리소스
htop

# 디스크 사용량
df -h
ncdu /
```

### 5.3 로그 관리

```bash
# 애플리케이션 로그
tail -f ~/service_b/naver-blog-bot/logs/*.log

# Docker 로그
docker logs naver-blog-bot --tail 100

# 로그 정리 (7일 이상 된 로그)
find ~/service_b/naver-blog-bot/logs -name "*.log" -mtime +7 -delete
```

---

## 트러블슈팅

### 컨테이너가 시작되지 않음

```bash
# 상세 로그 확인
docker logs naver-blog-bot

# 이미지 재빌드
cd ~/service_b/naver-blog-bot
docker-compose build --no-cache
docker-compose up -d
```

### 메모리 부족

```bash
# 메모리 확인
free -h

# Swap 확인
swapon --show

# 불필요한 이미지 정리
docker system prune -a
```

### SSH 연결 실패

```bash
# 서버에서 SSH 서비스 상태 확인
systemctl status sshd

# 방화벽 확인
ufw status
```

---

## CI/CD 워크플로우 구조

```
main/master 브랜치 push
        │
        ▼
┌───────────────────┐
│   Job 1: Test     │  ← flake8, black, mypy
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Job 2: Build    │  ← Docker 이미지 빌드
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Job 3: Deploy   │  ← SSH로 서버 배포
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Job 4: Notify   │  ← Telegram 알림
└───────────────────┘
```

---

## 보안 체크리스트

- [ ] SSH 키 기반 인증만 사용
- [ ] root 비밀번호 비활성화
- [ ] UFW 방화벽 활성화
- [ ] Fail2Ban 설치 및 설정
- [ ] .env 파일 Git에 포함되지 않음
- [ ] secrets/ 디렉토리 Git에 포함되지 않음
- [ ] API 키 정기적으로 로테이션

---

## 문의 및 지원

- GitHub Issues: https://github.com/joocy75-hash/Naver-Blog/issues
