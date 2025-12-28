# Headless Server Setup Guide

Complete configuration guide for running Naver Blog automation in headless server environments (Docker, VPS).

## Critical Configuration Requirements

### 1. Fixed Window Size (MANDATORY)

**Why**: Button positions and element visibility depend on consistent viewport dimensions.

**Implementation in `auto_post.py`**:

```python
async def start_browser(self):
    browser = await self.playwright.chromium.launch(
        headless=self.headless,
        args=[
            '--window-size=1920,1080',  # CRITICAL
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',  # Required in Docker
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},  # CRITICAL
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
        locale="ko-KR",
        timezone_id="Asia/Seoul"
    )
```

### 2. Text-Based Selectors (MANDATORY)

**Never use position-based selectors** - they break when layout changes.

```python
# ❌ BAD - Position-based
button = page.locator('button').nth(2)

# ✅ GOOD - Text-based with fallbacks
SELECTORS = [
    'button:has-text("발행")',
    'button:has-text("Publish")',
    'button[class*="publish_btn"]',
]

for selector in SELECTORS:
    try:
        btn = page.locator(selector)
        await btn.wait_for(state="visible", timeout=30000)
        await btn.click()
        break
    except:
        continue
```

### 3. 30-Second Timeout Rule

All critical interactions MUST wait up to 30 seconds:

```python
await element.wait_for(state="visible", timeout=30000)
```

### 4. Step-by-Step Logging

Log every major operation with clear markers:

```python
logger.info("🚀 STEP 1: Clicking initial publish button...")
await self._click_publish_button()
logger.success("✅ STEP 1 COMPLETE")

logger.info("🚀 STEP 2: Handling publish popup...")
await self._handle_publish_popup()
logger.success("✅ STEP 2 COMPLETE")
```

## Docker Configuration

### Dockerfile (Optimized)

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fonts-nanum fonts-nanum-coding \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application
COPY . .

# Create required directories
RUN mkdir -p data/sessions logs generated_images secrets

# Environment
ENV HEADLESS=True \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul

CMD ["python", "-m", "scheduler.auto_scheduler"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  naver-blog-bot:
    build: .
    container_name: naver-blog-bot
    restart: unless-stopped

    environment:
      - HEADLESS=True
      - USE_CDP=False  # CRITICAL for Docker
      - CDP_TIMEOUT=3
      - TZ=Asia/Seoul
      - PYTHONUNBUFFERED=1

    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./generated_images:/app/generated_images
      - ./secrets:/app/secrets
      - ./.env:/app/.env:ro

    # Resource limits (adjust for your server)
    deploy:
      resources:
        limits:
          cpus: '0.8'
          memory: 900M
        reservations:
          cpus: '0.2'
          memory: 256M

    # Shared memory for Chromium
    shm_size: '2gb'

    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

## Environment Variables

### Required .env Configuration

```bash
# Naver credentials
NAVER_ID=your_naver_id
NAVER_PW=your_password

# AI API keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# HEADLESS MODE SETTINGS (CRITICAL)
HEADLESS=True
USE_CDP=False  # MUST be False in Docker
CDP_TIMEOUT=3

# Session management
SESSION_MAX_AGE_DAYS=7

# Scheduling
MAX_DAILY_POSTS=12
MIN_POST_INTERVAL_HOURS=1

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

## Session Management for Headless

### Initial Session Creation (Local Machine with GUI)

```bash
# Run on your LOCAL machine (macOS/Windows with GUI)
python manual_login_clipboard.py

# Browser opens, log in manually to Naver
# Session saved to: data/sessions/wncksdid0750_clipboard.session.encrypted
```

### Transfer Session to Server

```bash
# Transfer encrypted session file
scp data/sessions/wncksdid0750_clipboard.session.encrypted \
    root@SERVER_IP:/root/naver-blog-bot/data/sessions/

# Transfer encryption key
scp secrets/encryption.key \
    root@SERVER_IP:/root/naver-blog-bot/secrets/
```

### Session Auto-Renewal

```python
# In upload_agent.py or auto_post.py after successful publish
from security.session_manager import renew_playwright_session

await renew_playwright_session(page, "wncksdid0750_clipboard")
logger.success("Session renewed - valid for 7 more days")
```

## Server Selection (Korean IP Required)

### Why Korean IP Matters

Naver blocks foreign IPs from publishing blog posts. Symptoms:
- Publish button clicks succeed locally but fail on server
- URL changes to `PostView.naver?...` but shows "페이지를 찾을 수 없습니다" (Page not found)

### Recommended Providers with Seoul Region

| Provider | Plan | Location | IP | Cost/Month |
|----------|------|----------|-----|------------|
| Vultr | vc2-1c-1gb | Seoul | Korean | $5 |
| Oracle Cloud | Always Free (2 VMs) | Seoul | Korean | Free |
| AWS Lightsail | 512MB | Seoul | Korean | $3.50 |
| Naver Cloud | Micro | Korea | Korean | ~$7 |

**Current Production**: Vultr Seoul (141.164.55.245)

## Deployment Checklist

### Pre-Deployment (Local)

- [ ] Test posting locally with `--headless` flag
- [ ] Verify all selectors work in headless mode
- [ ] Check logs for warnings or errors
- [ ] Confirm session file exists and is valid

### Server Setup

- [ ] SSH access configured
- [ ] Docker and Docker Compose installed
- [ ] Git installed (for code updates)
- [ ] Firewall allows outbound HTTPS (443)

### Initial Deployment

1. Clone or transfer code to server
2. Create `.env` file with all variables
3. Transfer session files from local
4. Build Docker image
5. Run container
6. Monitor logs for first post

### Verification

```bash
# Check container running
docker ps

# View logs
docker logs naver-blog-bot -f

# Check session
python scripts/validate-session.py wncksdid0750_clipboard

# Test single post
docker exec -it naver-blog-bot python auto_post.py wncksdid0750 "Test" "Content" --headless
```

## Monitoring in Production

### Daily Checks

```bash
# Container status
docker ps -a | grep naver-blog-bot

# Recent logs (last 100 lines)
docker logs naver-blog-bot --tail 100

# Resource usage
docker stats naver-blog-bot --no-stream

# Disk space
df -h
```

### Automated Monitoring

Set up cron job for health checks:

```bash
# /etc/cron.d/blog-bot-monitor
*/15 * * * * root docker exec naver-blog-bot python monitoring/health_checker.py

# Runs every 15 minutes
```

## Common Headless-Specific Issues

### Issue: DISPLAY not set

**Error**: `KeyError: 'DISPLAY'`

**Solution**: Already handled in `utils/clipboard_input.py`:
```python
if os.environ.get('HEADLESS') == 'True' or 'DISPLAY' not in os.environ:
    pyautogui = None
```

### Issue: CDP Connection Timeout

**Error**: `CDP endpoint timeout after 10 seconds`

**Solution**: Set `USE_CDP=False` in `.env`

### Issue: Fonts Not Rendering

**Symptom**: Screenshots show boxes instead of Korean characters

**Solution**: Install Korean fonts in Dockerfile:
```dockerfile
RUN apt-get install -y fonts-nanum fonts-nanum-coding
```

### Issue: Shared Memory Error

**Error**: `Failed to create shared memory`

**Solution**: Add to docker-compose.yml:
```yaml
shm_size: '2gb'
```

Or add to docker run:
```bash
docker run --shm-size=2gb ...
```

## Performance Optimization

### Reduce Screenshot Overhead

Disable screenshots in production:

```python
# In auto_post.py
if os.getenv("DEBUG") != "True":
    # Skip screenshot saving
    pass
```

### Minimize Log File Size

Rotate logs daily:

```python
from loguru import logger

logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    compression="zip"
)
```

### Clean Up Old Images

```bash
# Add to cron
0 2 * * * find /root/naver-blog-bot/generated_images -name "*.png" -mtime +7 -delete
```

---

**End of Headless Setup Guide**
