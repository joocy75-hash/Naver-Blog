#!/bin/bash
#
# System Health Check Script
# Verify all components are functioning correctly
#

set -e

echo "======================================"
echo "NAVER BLOG BOT - HEALTH CHECK"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
HEALTH_OK=true

# ====================
# CHECK 1: Docker Container
# ====================
echo "🐳 CHECK 1: Docker Container Status"

if docker ps | grep -q naver-blog-bot; then
    echo -e "${GREEN}✅ Container running${NC}"
else
    echo -e "${RED}❌ Container not running${NC}"
    HEALTH_OK=false
fi

# Container health status
if docker inspect naver-blog-bot | grep -q '"Health"'; then
    HEALTH_STATUS=$(docker inspect naver-blog-bot | jq -r '.[0].State.Health.Status')
    if [ "$HEALTH_STATUS" == "healthy" ]; then
        echo -e "${GREEN}✅ Health status: healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Health status: $HEALTH_STATUS${NC}"
    fi
fi

# ====================
# CHECK 2: System Resources
# ====================
echo ""
echo "📊 CHECK 2: System Resources"

# CPU usage
CPU=$(docker stats naver-blog-bot --no-stream --format "{{.CPUPerc}}" | sed 's/%//')
if (( $(echo "$CPU < 80" | bc -l) )); then
    echo -e "${GREEN}✅ CPU: ${CPU}%${NC}"
else
    echo -e "${YELLOW}⚠️  CPU: ${CPU}% (high)${NC}"
    HEALTH_OK=false
fi

# Memory usage
MEM=$(docker stats naver-blog-bot --no-stream --format "{{.MemPerc}}" | sed 's/%//')
if (( $(echo "$MEM < 85" | bc -l) )); then
    echo -e "${GREEN}✅ Memory: ${MEM}%${NC}"
else
    echo -e "${YELLOW}⚠️  Memory: ${MEM}% (high)${NC}"
    HEALTH_OK=false
fi

# Disk space
DISK=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if (( DISK < 90 )); then
    echo -e "${GREEN}✅ Disk: ${DISK}% used${NC}"
else
    echo -e "${YELLOW}⚠️  Disk: ${DISK}% used (high)${NC}"
    HEALTH_OK=false
fi

# ====================
# CHECK 3: Session Files
# ====================
echo ""
echo "🔐 CHECK 3: Session Files"

if [ -f "data/sessions/wncksdid0750_clipboard.session.encrypted" ]; then
    echo -e "${GREEN}✅ Session file exists${NC}"

    # Check session validity with Python script
    if python scripts/validate-session.py wncksdid0750_clipboard > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Session is valid${NC}"
    else
        echo -e "${YELLOW}⚠️  Session may be expired${NC}"
        HEALTH_OK=false
    fi
else
    echo -e "${RED}❌ Session file not found${NC}"
    HEALTH_OK=false
fi

if [ -f "secrets/encryption.key" ]; then
    echo -e "${GREEN}✅ Encryption key exists${NC}"
else
    echo -e "${RED}❌ Encryption key not found${NC}"
    HEALTH_OK=false
fi

# ====================
# CHECK 4: Environment Variables
# ====================
echo ""
echo "⚙️  CHECK 4: Environment Variables"

if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"

    # Check critical variables
    REQUIRED_VARS=("NAVER_ID" "ANTHROPIC_API_KEY" "GOOGLE_API_KEY" "PERPLEXITY_API_KEY")

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env; then
            echo -e "${GREEN}✅ $var is set${NC}"
        else
            echo -e "${RED}❌ $var is missing or empty${NC}"
            HEALTH_OK=false
        fi
    done
else
    echo -e "${RED}❌ .env file not found${NC}"
    HEALTH_OK=false
fi

# ====================
# CHECK 5: Recent Logs
# ====================
echo ""
echo "📝 CHECK 5: Recent Logs"

if docker logs naver-blog-bot --tail 100 2>&1 | grep -qi "error"; then
    ERROR_COUNT=$(docker logs naver-blog-bot --tail 100 2>&1 | grep -ci "error")
    echo -e "${YELLOW}⚠️  Found $ERROR_COUNT errors in recent logs${NC}"

    echo ""
    echo "Recent errors:"
    docker logs naver-blog-bot --tail 100 2>&1 | grep -i "error" | tail -5
else
    echo -e "${GREEN}✅ No errors in recent logs${NC}"
fi

# ====================
# CHECK 6: Network Connectivity
# ====================
echo ""
echo "🌐 CHECK 6: Network Connectivity"

# Test Naver Blog access
if curl -s --max-time 5 https://blog.naver.com > /dev/null; then
    echo -e "${GREEN}✅ Naver Blog accessible${NC}"
else
    echo -e "${RED}❌ Cannot reach Naver Blog${NC}"
    HEALTH_OK=false
fi

# Test Claude API
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    if curl -s --max-time 5 -H "x-api-key: $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Claude API reachable${NC}"
    else
        echo -e "${YELLOW}⚠️  Claude API check inconclusive${NC}"
    fi
fi

# ====================
# SUMMARY
# ====================
echo ""
echo "======================================"

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ HEALTH CHECK PASSED${NC}"
    echo "======================================"
    exit 0
else
    echo -e "${YELLOW}⚠️  HEALTH CHECK WARNINGS DETECTED${NC}"
    echo "======================================"
    echo ""
    echo "Review the warnings above and take corrective action."
    exit 1
fi
