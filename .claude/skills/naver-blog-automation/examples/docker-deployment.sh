#!/bin/bash
#
# Docker Deployment Example
# Complete setup script for deploying to production server
#

set -e  # Exit on error

echo "========================================"
echo "NAVER BLOG BOT - DOCKER DEPLOYMENT"
echo "========================================"

# Configuration
SERVER_IP="${SERVER_IP:-141.164.55.245}"
SERVER_USER="${SERVER_USER:-root}"
DEPLOY_PATH="/root/naver-blog-bot"

echo ""
echo "Target Server: $SERVER_USER@$SERVER_IP"
echo "Deploy Path: $DEPLOY_PATH"
echo ""

# ====================
# STEP 1: Prerequisites Check
# ====================
echo "📋 STEP 1: Checking prerequisites..."

if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Copy .env.example to .env and configure it"
    exit 1
fi

if [ ! -f "data/sessions/wncksdid0750_clipboard.session.encrypted" ]; then
    echo "❌ Error: Session file not found"
    echo "Run: python manual_login_clipboard.py"
    exit 1
fi

if [ ! -f "secrets/encryption.key" ]; then
    echo "❌ Error: Encryption key not found"
    exit 1
fi

echo "✅ Prerequisites OK"

# ====================
# STEP 2: Server Connection Test
# ====================
echo ""
echo "🔌 STEP 2: Testing server connection..."

if ! ssh -o ConnectTimeout=5 "$SERVER_USER@$SERVER_IP" "echo 'Connected'" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to server"
    echo "Check SSH access: ssh $SERVER_USER@$SERVER_IP"
    exit 1
fi

echo "✅ Server connection OK"

# ====================
# STEP 3: Transfer Files
# ====================
echo ""
echo "📦 STEP 3: Transferring files to server..."

# Create directories on server
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $DEPLOY_PATH/{data/sessions,logs,secrets,generated_images}"

# Transfer code (exclude unnecessary files)
echo "  Transferring codebase..."
rsync -avz --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           --exclude='logs/*.log' \
           --exclude='data/*.db' \
           ./ "$SERVER_USER@$SERVER_IP:$DEPLOY_PATH/"

# Transfer sensitive files separately
echo "  Transferring .env file..."
scp .env "$SERVER_USER@$SERVER_IP:$DEPLOY_PATH/.env"

echo "  Transferring session files..."
scp data/sessions/*.encrypted "$SERVER_USER@$SERVER_IP:$DEPLOY_PATH/data/sessions/"

echo "  Transferring encryption key..."
scp secrets/encryption.key "$SERVER_USER@$SERVER_IP:$DEPLOY_PATH/secrets/"

echo "✅ Files transferred"

# ====================
# STEP 4: Build Docker Image
# ====================
echo ""
echo "🐳 STEP 4: Building Docker image on server..."

ssh "$SERVER_USER@$SERVER_IP" << 'EOF'
cd /root/naver-blog-bot

echo "Building Docker image..."
docker build -t naver-blog-bot:latest . || {
    echo "❌ Docker build failed"
    exit 1
}

echo "✅ Docker image built"
EOF

# ====================
# STEP 5: Stop Old Container
# ====================
echo ""
echo "🛑 STEP 5: Stopping old container..."

ssh "$SERVER_USER@$SERVER_IP" << 'EOF'
if docker ps -a | grep -q naver-blog-bot; then
    echo "Stopping old container..."
    docker stop naver-blog-bot || true
    docker rm naver-blog-bot || true
    echo "✅ Old container removed"
else
    echo "No existing container found"
fi
EOF

# ====================
# STEP 6: Start New Container
# ====================
echo ""
echo "🚀 STEP 6: Starting new container..."

ssh "$SERVER_USER@$SERVER_IP" << 'EOF'
cd /root/naver-blog-bot

docker run -d \
  --name naver-blog-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/generated_images:/app/generated_images \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/.env:/app/.env:ro \
  --shm-size=2gb \
  -e HEADLESS=True \
  -e USE_CDP=False \
  naver-blog-bot:latest

echo "✅ Container started"
EOF

# ====================
# STEP 7: Verify Deployment
# ====================
echo ""
echo "✅ STEP 7: Verifying deployment..."

echo ""
echo "Container status:"
ssh "$SERVER_USER@$SERVER_IP" "docker ps | grep naver-blog-bot"

echo ""
echo "Recent logs (last 20 lines):"
ssh "$SERVER_USER@$SERVER_IP" "docker logs naver-blog-bot --tail 20"

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "Monitor logs: ssh $SERVER_USER@$SERVER_IP 'docker logs naver-blog-bot -f'"
echo "Check status: ssh $SERVER_USER@$SERVER_IP 'docker ps'"
echo "Restart: ssh $SERVER_USER@$SERVER_IP 'docker restart naver-blog-bot'"
echo ""
