# 🚀 원클릭 배포 가이드

## 서버 정보
- **IP**: 5.161.112.248
- **사용자**: root
- **OS**: Ubuntu 24.04 LTS
- **그룹**: Group B (Personal Automation)

---

## 📋 배포 순서 (3단계)

### Step 1: GitHub Secrets 설정
```bash
cd /Users/mr.joo/Desktop/네이버블로그봇
./deploy/setup-github-secrets.sh
```

이 스크립트가 수행하는 작업:
- SSH 키 생성 (ed25519)
- 서버에 공개키 등록
- GitHub Secrets 자동 등록 (gh cli 사용)

### Step 2: 서버 배포
```bash
./deploy/deploy-to-server.sh
```

이 스크립트가 수행하는 작업:
- 서버 초기화 (Docker, Swap, UFW, Fail2Ban)
- 프로젝트 파일 전송
- .env 파일 설정
- Docker 컨테이너 빌드 및 실행

### Step 3: GitHub Push → 자동 배포
```bash
git add .
git commit -m "Deploy to Hetzner server"
git push origin main
```

---

## 🔧 개별 명령어

### SSH 접속
```bash
ssh root@5.161.112.248
```

### 컨테이너 상태 확인
```bash
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose ps'
```

### 로그 확인 (실시간)
```bash
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose logs -f'
```

### 재시작
```bash
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose restart'
```

### 중지
```bash
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose down'
```

### 이미지 재빌드
```bash
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose build --no-cache && docker-compose up -d'
```

---

## 🔐 환경 변수 수정

```bash
ssh root@5.161.112.248
cd ~/service_b/naver-blog-bot
vim .env
docker-compose restart
```

---

## 📊 모니터링

### 시스템 리소스
```bash
ssh root@5.161.112.248 'htop'
```

### Docker 리소스
```bash
ssh root@5.161.112.248 'docker stats'
```

### 디스크 사용량
```bash
ssh root@5.161.112.248 'df -h'
```

---

## 🆘 트러블슈팅

### 컨테이너가 시작되지 않음
```bash
# 로그 확인
ssh root@5.161.112.248 'docker logs naver-blog-bot'

# 이미지 재빌드
ssh root@5.161.112.248 'cd ~/service_b/naver-blog-bot && docker-compose build --no-cache'
```

### 메모리 부족
```bash
# 메모리 확인
ssh root@5.161.112.248 'free -h'

# 불필요한 이미지 정리
ssh root@5.161.112.248 'docker system prune -a'
```

### CI/CD 실패
1. GitHub Actions 탭에서 로그 확인
2. Secrets 설정 확인 (HETZNER_HOST, HETZNER_USER, HETZNER_SSH_KEY)
3. 서버 SSH 연결 테스트

---

## ✅ 체크리스트

- [ ] GitHub Secrets 설정 완료
- [ ] 서버 초기화 완료
- [ ] .env 파일 설정 완료
- [ ] Docker 컨테이너 실행 확인
- [ ] Telegram 알림 테스트 (선택)
- [ ] CI/CD 테스트 배포
