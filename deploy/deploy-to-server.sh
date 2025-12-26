#!/bin/bash
# ============================================
# 서버 원클릭 배포 스크립트
# 서버 초기화 + 앱 배포 + 환경변수 설정
# ============================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 변수 설정
HETZNER_HOST="${HETZNER_HOST:-5.161.112.248}"
HETZNER_USER="${HETZNER_USER:-root}"
SSH_KEY_PATH="${SSH_KEY_PATH:-$HOME/.ssh/hetzner_deploy_ed25519}"
DEPLOY_PATH="~/service_b/naver-blog-bot"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "🚀 Hetzner 서버 원클릭 배포"
echo "============================================"
echo ""
echo "서버: $HETZNER_USER@$HETZNER_HOST"
echo "배포 경로: $DEPLOY_PATH"
echo "프로젝트: $PROJECT_DIR"
echo ""

# SSH 옵션
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=30"
if [ -f "$SSH_KEY_PATH" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY_PATH"
fi

# ============================================
# Step 1: SSH 연결 테스트
# ============================================
log_step "1/6: SSH 연결 테스트"

if ! ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "echo 'SSH 연결 성공'" 2>/dev/null; then
    log_error "SSH 연결 실패!"
    echo "다음을 확인하세요:"
    echo "  1. 서버 IP가 올바른지"
    echo "  2. SSH 키가 서버에 등록되어 있는지"
    echo "  3. 방화벽에서 SSH가 허용되어 있는지"
    exit 1
fi
log_info "SSH 연결 성공"

# ============================================
# Step 2: 서버 초기화 확인
# ============================================
log_step "2/6: 서버 초기화 상태 확인"

DOCKER_INSTALLED=$(ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "command -v docker &>/dev/null && echo 'yes' || echo 'no'")

if [ "$DOCKER_INSTALLED" = "no" ]; then
    log_warn "Docker가 설치되어 있지 않습니다."
    read -p "서버 초기화를 진행하시겠습니까? (Docker, Swap, UFW 등 설치) [Y/n]: " init_server

    if [[ ! "$init_server" =~ ^[Nn]$ ]]; then
        log_info "서버 초기화 스크립트 전송 및 실행..."

        # 스크립트 전송
        scp $SSH_OPTS "$PROJECT_DIR/deploy/server-init.sh" "$HETZNER_USER@$HETZNER_HOST:/tmp/"

        # 스크립트 실행
        ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "chmod +x /tmp/server-init.sh && /tmp/server-init.sh"

        log_info "서버 초기화 완료"
    fi
else
    log_info "Docker 이미 설치됨: $(ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "docker --version")"
fi

# ============================================
# Step 3: 배포 디렉토리 생성
# ============================================
log_step "3/6: 배포 디렉토리 생성"

ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "
    mkdir -p $DEPLOY_PATH/{logs,generated_images,data,secrets}
    echo '디렉토리 생성 완료'
"
log_info "배포 디렉토리 준비 완료"

# ============================================
# Step 4: 프로젝트 파일 전송
# ============================================
log_step "4/6: 프로젝트 파일 전송"

# 전송할 파일 목록
FILES_TO_TRANSFER=(
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    ".env.example"
    "main.py"
    "pipeline.py"
)

# 전송할 디렉토리 목록
DIRS_TO_TRANSFER=(
    "agents"
    "config"
    "models"
    "monitoring"
    "scheduler"
    "security"
    "utils"
)

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

log_info "파일 준비 중..."

# 파일 복사
for file in "${FILES_TO_TRANSFER[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        cp "$PROJECT_DIR/$file" "$TEMP_DIR/"
    fi
done

# 디렉토리 복사
for dir in "${DIRS_TO_TRANSFER[@]}"; do
    if [ -d "$PROJECT_DIR/$dir" ]; then
        cp -r "$PROJECT_DIR/$dir" "$TEMP_DIR/"
    fi
done

# __pycache__ 제거
find "$TEMP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 압축
log_info "파일 압축 중..."
cd "$TEMP_DIR"
tar -czf project.tar.gz *

# 전송
log_info "서버로 전송 중..."
scp $SSH_OPTS "$TEMP_DIR/project.tar.gz" "$HETZNER_USER@$HETZNER_HOST:$DEPLOY_PATH/"

# 압축 해제
ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "
    cd $DEPLOY_PATH
    tar -xzf project.tar.gz
    rm -f project.tar.gz
    echo '파일 전송 및 압축 해제 완료'
"

log_info "프로젝트 파일 전송 완료"

# ============================================
# Step 5: 환경 변수 설정
# ============================================
log_step "5/6: 환경 변수 설정"

# 서버에 .env 파일이 있는지 확인
ENV_EXISTS=$(ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "[ -f $DEPLOY_PATH/.env ] && echo 'yes' || echo 'no'")

if [ "$ENV_EXISTS" = "no" ]; then
    log_warn ".env 파일이 없습니다."

    # 로컬에 .env 파일이 있으면 사용
    if [ -f "$PROJECT_DIR/.env" ]; then
        read -p "로컬 .env 파일을 사용하시겠습니까? [Y/n]: " use_local_env
        if [[ ! "$use_local_env" =~ ^[Nn]$ ]]; then
            scp $SSH_OPTS "$PROJECT_DIR/.env" "$HETZNER_USER@$HETZNER_HOST:$DEPLOY_PATH/"
            log_info "로컬 .env 파일 전송 완료"
        fi
    else
        log_warn ".env 파일을 생성해야 합니다."
        echo ""
        echo "다음 명령으로 .env 파일을 편집하세요:"
        echo "  ssh $HETZNER_USER@$HETZNER_HOST"
        echo "  cd $DEPLOY_PATH"
        echo "  cp .env.example .env"
        echo "  vim .env"
        echo ""

        read -p "지금 .env 파일을 설정하시겠습니까? [Y/n]: " setup_env_now
        if [[ ! "$setup_env_now" =~ ^[Nn]$ ]]; then
            # 대화형 환경 변수 설정
            ./deploy/setup-env-interactive.sh "$HETZNER_HOST" "$HETZNER_USER" "$DEPLOY_PATH"
        fi
    fi
else
    log_info ".env 파일 이미 존재"
fi

# ============================================
# Step 6: Docker 컨테이너 빌드 및 실행
# ============================================
log_step "6/6: Docker 컨테이너 빌드 및 실행"

read -p "Docker 컨테이너를 빌드하고 실행하시겠습니까? [Y/n]: " run_docker
if [[ ! "$run_docker" =~ ^[Nn]$ ]]; then

    log_info "Docker 이미지 빌드 중... (시간이 걸릴 수 있습니다)"

    ssh $SSH_OPTS "$HETZNER_USER@$HETZNER_HOST" "
        cd $DEPLOY_PATH

        # 기존 컨테이너 중지
        docker-compose down --remove-orphans 2>/dev/null || true

        # 이미지 빌드
        docker-compose build --no-cache

        # 컨테이너 실행
        docker-compose up -d

        # 상태 확인
        echo ''
        echo '=========================================='
        echo '컨테이너 상태:'
        docker-compose ps
        echo ''
        echo '최근 로그:'
        docker-compose logs --tail 20
        echo '=========================================='
    "

    log_info "Docker 컨테이너 실행 완료"
fi

# ============================================
# 완료
# ============================================
echo ""
echo "============================================"
echo -e "${GREEN}✅ 서버 배포 완료!${NC}"
echo "============================================"
echo ""
echo "📍 서버 정보:"
echo "   IP: $HETZNER_HOST"
echo "   경로: $DEPLOY_PATH"
echo ""
echo "🔧 유용한 명령어:"
echo "   # SSH 접속"
echo "   ssh $HETZNER_USER@$HETZNER_HOST"
echo ""
echo "   # 컨테이너 상태"
echo "   ssh $HETZNER_USER@$HETZNER_HOST 'cd $DEPLOY_PATH && docker-compose ps'"
echo ""
echo "   # 로그 확인"
echo "   ssh $HETZNER_USER@$HETZNER_HOST 'cd $DEPLOY_PATH && docker-compose logs -f'"
echo ""
echo "   # 재시작"
echo "   ssh $HETZNER_USER@$HETZNER_HOST 'cd $DEPLOY_PATH && docker-compose restart'"
echo ""
echo "🎉 이제 GitHub에 push하면 자동 배포됩니다!"
echo "============================================"
