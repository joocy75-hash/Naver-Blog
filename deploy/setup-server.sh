#!/bin/bash
# 서버 초기 설정 스크립트 (Ubuntu/Debian)
# 사용법: chmod +x setup-server.sh && sudo ./setup-server.sh

set -e

echo "=========================================="
echo "네이버 블로그 봇 서버 설정 시작"
echo "=========================================="

# 시스템 업데이트
echo "[1/7] 시스템 업데이트..."
apt-get update && apt-get upgrade -y

# Python 3.11 설치
echo "[2/7] Python 3.11 설치..."
apt-get install -y python3.11 python3.11-venv python3-pip

# Playwright 의존성 설치
echo "[3/7] Playwright 의존성 설치..."
apt-get install -y \
    wget \
    gnupg \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    fonts-nanum \
    fonts-nanum-coding

# 사용자 디렉토리 설정
echo "[4/7] 프로젝트 디렉토리 설정..."
PROJECT_DIR="/home/ubuntu/naver-blog-bot"
mkdir -p $PROJECT_DIR/{logs,generated_images,data,secrets}
mkdir -p /var/log/naver-blog-bot

# 가상환경 생성
echo "[5/7] 가상환경 생성..."
cd $PROJECT_DIR
python3.11 -m venv venv
source venv/bin/activate

# 의존성 설치
echo "[6/7] Python 패키지 설치..."
pip install --upgrade pip
pip install -r requirements.txt

# Playwright 브라우저 설치
echo "[7/7] Playwright 브라우저 설치..."
playwright install chromium
playwright install-deps chromium

# 권한 설정
chown -R ubuntu:ubuntu $PROJECT_DIR
chown -R ubuntu:ubuntu /var/log/naver-blog-bot

echo "=========================================="
echo "서버 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. .env 파일을 $PROJECT_DIR/.env 로 복사"
echo "2. secrets 디렉토리에 인증 파일 복사"
echo "3. systemd 서비스 활성화:"
echo "   sudo cp deploy/naver-blog-bot.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable naver-blog-bot"
echo "   sudo systemctl start naver-blog-bot"
echo ""
echo "로그 확인:"
echo "   journalctl -u naver-blog-bot -f"
echo "=========================================="
