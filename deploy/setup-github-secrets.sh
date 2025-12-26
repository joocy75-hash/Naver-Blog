#!/bin/bash
# ============================================
# GitHub Secrets 설정 스크립트
# SSH 키 생성 및 GitHub Secrets 자동 등록
# ============================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo "============================================"
echo "🔐 GitHub Secrets 설정 스크립트"
echo "============================================"
echo ""

# 변수 설정
HETZNER_HOST="${HETZNER_HOST:-5.161.112.248}"
HETZNER_USER="${HETZNER_USER:-root}"
GITHUB_REPO="${GITHUB_REPO:-joocy75-hash/Naver-Blog}"
SSH_KEY_PATH="$HOME/.ssh/hetzner_deploy_ed25519"

# ============================================
# Step 1: GitHub CLI 확인
# ============================================
log_step "1/5: GitHub CLI 확인"

if ! command -v gh &> /dev/null; then
    log_warn "GitHub CLI가 설치되어 있지 않습니다."
    echo ""
    echo "설치 방법:"
    echo "  macOS: brew install gh"
    echo "  Ubuntu: sudo apt install gh"
    echo ""
    echo "설치 후 'gh auth login' 으로 인증하세요."
    echo ""

    read -p "GitHub CLI 없이 계속 진행하시겠습니까? (수동 설정 필요) [y/N]: " continue_without_gh
    if [[ ! "$continue_without_gh" =~ ^[Yy]$ ]]; then
        exit 1
    fi
    GH_AVAILABLE=false
else
    # GitHub CLI 인증 확인
    if ! gh auth status &> /dev/null; then
        log_warn "GitHub CLI 인증이 필요합니다."
        gh auth login
    fi
    GH_AVAILABLE=true
    log_info "GitHub CLI 인증 확인 완료"
fi

# ============================================
# Step 2: SSH 키 생성
# ============================================
log_step "2/5: SSH 키 생성"

if [ -f "$SSH_KEY_PATH" ]; then
    log_warn "SSH 키가 이미 존재합니다: $SSH_KEY_PATH"
    read -p "새로운 키를 생성하시겠습니까? [y/N]: " regenerate
    if [[ "$regenerate" =~ ^[Yy]$ ]]; then
        rm -f "$SSH_KEY_PATH" "$SSH_KEY_PATH.pub"
    else
        log_info "기존 키 사용"
    fi
fi

if [ ! -f "$SSH_KEY_PATH" ]; then
    log_info "새 SSH 키 생성 중..."
    ssh-keygen -t ed25519 -C "github-actions-hetzner-deploy" -f "$SSH_KEY_PATH" -N ""
    log_info "SSH 키 생성 완료: $SSH_KEY_PATH"
fi

# ============================================
# Step 3: 서버에 공개키 등록
# ============================================
log_step "3/5: 서버에 공개키 등록"

echo ""
log_info "서버 정보:"
echo "  Host: $HETZNER_HOST"
echo "  User: $HETZNER_USER"
echo ""

read -p "서버에 공개키를 등록하시겠습니까? [Y/n]: " register_key
if [[ ! "$register_key" =~ ^[Nn]$ ]]; then
    log_info "서버에 공개키 등록 중..."

    # ssh-copy-id 사용
    if ssh-copy-id -i "$SSH_KEY_PATH.pub" "$HETZNER_USER@$HETZNER_HOST" 2>/dev/null; then
        log_info "공개키 등록 완료"
    else
        log_warn "ssh-copy-id 실패. 수동으로 등록하세요:"
        echo ""
        echo "서버에서 다음 명령 실행:"
        echo "  echo '$(cat "$SSH_KEY_PATH.pub")' >> ~/.ssh/authorized_keys"
        echo ""
    fi

    # 연결 테스트
    log_info "SSH 연결 테스트..."
    if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 "$HETZNER_USER@$HETZNER_HOST" "echo 'SSH 연결 성공'" 2>/dev/null; then
        log_info "✅ SSH 연결 테스트 성공"
    else
        log_error "SSH 연결 실패. 키 등록을 확인하세요."
    fi
fi

# ============================================
# Step 4: GitHub Secrets 등록
# ============================================
log_step "4/5: GitHub Secrets 등록"

SSH_PRIVATE_KEY=$(cat "$SSH_KEY_PATH")

if [ "$GH_AVAILABLE" = true ]; then
    log_info "GitHub Secrets 자동 등록 중..."

    # HETZNER_HOST
    echo "$HETZNER_HOST" | gh secret set HETZNER_HOST --repo "$GITHUB_REPO"
    log_info "  ✅ HETZNER_HOST 등록 완료"

    # HETZNER_USER
    echo "$HETZNER_USER" | gh secret set HETZNER_USER --repo "$GITHUB_REPO"
    log_info "  ✅ HETZNER_USER 등록 완료"

    # HETZNER_SSH_KEY
    echo "$SSH_PRIVATE_KEY" | gh secret set HETZNER_SSH_KEY --repo "$GITHUB_REPO"
    log_info "  ✅ HETZNER_SSH_KEY 등록 완료"

    log_info "GitHub Secrets 등록 완료!"

else
    log_warn "GitHub CLI를 사용할 수 없습니다. 수동으로 등록하세요."
    echo ""
    echo "============================================"
    echo "📋 GitHub Secrets 수동 등록 가이드"
    echo "============================================"
    echo ""
    echo "1. https://github.com/$GITHUB_REPO/settings/secrets/actions 접속"
    echo ""
    echo "2. 다음 Secrets 추가:"
    echo ""
    echo "   [HETZNER_HOST]"
    echo "   $HETZNER_HOST"
    echo ""
    echo "   [HETZNER_USER]"
    echo "   $HETZNER_USER"
    echo ""
    echo "   [HETZNER_SSH_KEY]"
    echo "   (아래 내용 전체 복사)"
    echo "   ─────────────────────────────────────"
    cat "$SSH_KEY_PATH"
    echo ""
    echo "   ─────────────────────────────────────"
    echo ""
fi

# ============================================
# Step 5: Telegram Secrets (선택)
# ============================================
log_step "5/5: Telegram 알림 설정 (선택)"

read -p "Telegram 알림을 설정하시겠습니까? [y/N]: " setup_telegram
if [[ "$setup_telegram" =~ ^[Yy]$ ]]; then
    echo ""
    read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
    read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID

    if [ "$GH_AVAILABLE" = true ] && [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo "$TELEGRAM_BOT_TOKEN" | gh secret set TELEGRAM_BOT_TOKEN --repo "$GITHUB_REPO"
        echo "$TELEGRAM_CHAT_ID" | gh secret set TELEGRAM_CHAT_ID --repo "$GITHUB_REPO"
        log_info "Telegram Secrets 등록 완료"
    else
        echo ""
        echo "수동으로 등록하세요:"
        echo "  TELEGRAM_BOT_TOKEN: $TELEGRAM_BOT_TOKEN"
        echo "  TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"
    fi
fi

# ============================================
# 완료
# ============================================
echo ""
echo "============================================"
echo -e "${GREEN}✅ GitHub Secrets 설정 완료!${NC}"
echo "============================================"
echo ""
echo "📁 생성된 SSH 키:"
echo "   개인키: $SSH_KEY_PATH"
echo "   공개키: $SSH_KEY_PATH.pub"
echo ""
echo "🔐 등록된 Secrets:"
echo "   - HETZNER_HOST"
echo "   - HETZNER_USER"
echo "   - HETZNER_SSH_KEY"
if [[ "$setup_telegram" =~ ^[Yy]$ ]]; then
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_CHAT_ID"
fi
echo ""
echo "다음 단계:"
echo "   ./deploy/deploy-to-server.sh  # 서버 초기화 및 배포"
echo "============================================"
