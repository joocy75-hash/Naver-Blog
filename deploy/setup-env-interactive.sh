#!/bin/bash
# ============================================
# 대화형 .env 파일 설정 스크립트
# 서버에서 직접 .env 파일 생성
# ============================================

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 인자 받기
HETZNER_HOST="${1:-5.161.112.248}"
HETZNER_USER="${2:-root}"
DEPLOY_PATH="${3:-~/service_b/naver-blog-bot}"
SSH_KEY_PATH="$HOME/.ssh/hetzner_deploy_ed25519"

SSH_OPTS="-o StrictHostKeyChecking=no"
if [ -f "$SSH_KEY_PATH" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY_PATH"
fi

echo ""
echo "============================================"
echo "🔐 환경 변수 설정 (Interactive)"
echo "============================================"
echo ""
echo -e "${YELLOW}[필수]${NC} 표시된 항목은 반드시 입력해야 합니다."
echo -e "${CYAN}[선택]${NC} 표시된 항목은 Enter로 건너뛸 수 있습니다."
echo ""

# ============================================
# 필수 변수 입력
# ============================================
echo -e "${GREEN}=== 네이버 계정 ===${NC}"
read -p "[필수] NAVER_ID: " NAVER_ID
read -sp "[필수] NAVER_PW: " NAVER_PW
echo ""

echo ""
echo -e "${GREEN}=== AI API Keys ===${NC}"
read -p "[필수] ANTHROPIC_API_KEY (Claude): " ANTHROPIC_API_KEY
read -p "[선택] GOOGLE_API_KEY (Gemini): " GOOGLE_API_KEY
read -p "[선택] GCP_PROJECT_ID: " GCP_PROJECT_ID
read -p "[선택] PERPLEXITY_API_KEY: " PERPLEXITY_API_KEY

echo ""
echo -e "${GREEN}=== 텔레그램 알림 ===${NC}"
read -p "[선택] TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
read -p "[선택] TELEGRAM_CHAT_ID: " TELEGRAM_CHAT_ID

echo ""
echo -e "${GREEN}=== 블로그 설정 ===${NC}"
read -p "[선택] BLOG_CATEGORY (기본: 암호화폐): " BLOG_CATEGORY
BLOG_CATEGORY="${BLOG_CATEGORY:-암호화폐}"

read -p "[선택] MAX_DAILY_POSTS (기본: 12): " MAX_DAILY_POSTS
MAX_DAILY_POSTS="${MAX_DAILY_POSTS:-12}"

# ============================================
# .env 파일 생성
# ============================================
echo ""
echo "서버에 .env 파일 생성 중..."

ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "cat > $DEPLOY_PATH/.env << 'ENVEOF'
# ============================================
# 네이버 블로그 자동화 - 환경 변수
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================

# ===================
# Naver 계정 정보
# ===================
NAVER_ID=$NAVER_ID
NAVER_PW=$NAVER_PW

# ===================
# AI API Keys
# ===================
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
GOOGLE_API_KEY=$GOOGLE_API_KEY
GCP_PROJECT_ID=$GCP_PROJECT_ID
GCP_LOCATION=us-central1
PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY

# ===================
# 데이터베이스
# ===================
DATABASE_URL=sqlite:///./data/blog_bot.db

# ===================
# 보안 설정
# ===================
ENCRYPTION_KEY_PATH=./secrets/encryption.key
SESSION_ENCRYPTION=True

# ===================
# Rate Limiting
# ===================
MAX_DAILY_POSTS=$MAX_DAILY_POSTS
MIN_POST_INTERVAL_HOURS=1
API_COOLDOWN_SECONDS=60

# ===================
# 행동 시뮬레이션
# ===================
TYPING_SPEED_MIN_MS=80
TYPING_SPEED_MAX_MS=180
MOUSE_MOVEMENT_BEZIER=True
SCROLL_SPEED_HUMAN_LIKE=True
HEADLESS=True

# ===================
# 모니터링
# ===================
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
ENABLE_ALERTS=True

# ===================
# 콘텐츠 설정
# ===================
BLOG_CATEGORY=$BLOG_CATEGORY
DEFAULT_TAGS=비트코인,암호화폐,AI자동매매,투자
SEO_KEYWORD_DENSITY=1.8

# ===================
# 프로덕션 설정
# ===================
DEBUG=False
TEST_MODE=False
LOG_LEVEL=INFO
ENVEOF
"

# 파일 권한 설정
ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "chmod 600 $DEPLOY_PATH/.env"

echo ""
echo -e "${GREEN}✅ .env 파일 생성 완료!${NC}"
echo ""
echo "생성된 파일: $DEPLOY_PATH/.env"
echo ""
