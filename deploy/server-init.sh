#!/bin/bash
# ============================================
# Hetzner 서버 초기 설정 스크립트
# Ubuntu 24.04 LTS / CPX31 (4 vCPU / 8 GB RAM)
# ============================================

set -e  # 오류 발생 시 스크립트 중단

echo "============================================"
echo "🚀 Hetzner Server Initial Setup"
echo "============================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 1. 시스템 업데이트
# ============================================
log_info "시스템 패키지 업데이트..."
apt-get update && apt-get upgrade -y

# ============================================
# 2. 필수 패키지 설치
# ============================================
log_info "필수 패키지 설치..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    vim \
    htop \
    ncdu \
    tree \
    unzip \
    jq

# ============================================
# 3. Docker 설치
# ============================================
log_info "Docker 설치..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Docker 서비스 시작 및 자동 시작 설정
    systemctl start docker
    systemctl enable docker

    log_info "Docker 설치 완료: $(docker --version)"
else
    log_info "Docker 이미 설치됨: $(docker --version)"
fi

# Docker Compose 플러그인 설치 (V2)
log_info "Docker Compose 설치..."
apt-get install -y docker-compose-plugin
log_info "Docker Compose 버전: $(docker compose version)"

# ============================================
# 4. Swap 파일 설정 (2GB)
# ============================================
log_info "Swap 파일 설정 (2GB)..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

    # 영구 설정
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

    # Swappiness 조정 (낮은 값 = RAM 우선 사용)
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    sysctl -p

    log_info "Swap 설정 완료"
else
    log_info "Swap 이미 설정됨"
fi

# ============================================
# 5. UFW 방화벽 설정
# ============================================
log_info "UFW 방화벽 설정..."
apt-get install -y ufw

# 기본 정책
ufw default deny incoming
ufw default allow outgoing

# SSH 허용
ufw allow ssh

# HTTP/HTTPS 허용 (필요시)
ufw allow 80/tcp
ufw allow 443/tcp

# UFW 활성화
echo "y" | ufw enable
ufw status verbose

log_info "UFW 설정 완료"

# ============================================
# 6. Fail2Ban 설치 및 설정
# ============================================
log_info "Fail2Ban 설치..."
apt-get install -y fail2ban

# Fail2Ban 설정
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400
EOF

systemctl enable fail2ban
systemctl restart fail2ban

log_info "Fail2Ban 설정 완료"

# ============================================
# 7. 서비스 디렉토리 구조 생성
# ============================================
log_info "서비스 디렉토리 구조 생성..."

# Group A: Freqtrade Service
mkdir -p ~/service_a/{user1,user2,user3,user4}

# Group B: Personal Automation
mkdir -p ~/service_b/{naver-blog-bot,sports-analysis,tradingview-collector}

# Group C: AI Trading Platform
mkdir -p ~/service_c/ai-trading-platform

# 네이버 블로그 봇 하위 디렉토리
mkdir -p ~/service_b/naver-blog-bot/{logs,generated_images,data,secrets}

log_info "디렉토리 구조 생성 완료"

# ============================================
# 8. 시스템 최적화
# ============================================
log_info "시스템 최적화..."

# 파일 디스크립터 제한 증가
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF

# 커널 파라미터 최적화
cat >> /etc/sysctl.conf << 'EOF'
# Network optimization
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# Memory optimization
vm.overcommit_memory = 1
EOF

sysctl -p

log_info "시스템 최적화 완료"

# ============================================
# 9. Docker 네트워크 생성
# ============================================
log_info "Docker 네트워크 생성..."

# Group B 네트워크
docker network create --driver bridge \
    --subnet=172.20.0.0/24 \
    group-b-personal-automation 2>/dev/null || log_warn "네트워크가 이미 존재합니다"

log_info "Docker 네트워크 생성 완료"

# ============================================
# 10. 타임존 설정
# ============================================
log_info "타임존 설정 (Asia/Seoul)..."
timedatectl set-timezone Asia/Seoul

# ============================================
# 완료 메시지
# ============================================
echo ""
echo "============================================"
echo -e "${GREEN}✅ 서버 초기 설정 완료!${NC}"
echo "============================================"
echo ""
echo "📁 디렉토리 구조:"
echo "   ~/service_a/ - Freqtrade (Group A)"
echo "   ~/service_b/ - Personal Automation (Group B)"
echo "   ~/service_c/ - AI Trading Platform (Group C)"
echo ""
echo "🔐 다음 단계:"
echo "   1. GitHub Secrets 설정:"
echo "      - HETZNER_HOST: $(curl -s ifconfig.me)"
echo "      - HETZNER_USER: root"
echo "      - HETZNER_SSH_KEY: (SSH 개인키)"
echo ""
echo "   2. .env 파일 생성:"
echo "      cd ~/service_b/naver-blog-bot"
echo "      cp .env.example .env"
echo "      vim .env  # API 키 입력"
echo ""
echo "   3. GitHub에 push하면 자동 배포됩니다!"
echo ""
echo "============================================"
