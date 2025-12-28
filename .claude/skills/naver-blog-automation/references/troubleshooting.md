# Troubleshooting Guide

Comprehensive troubleshooting for common issues in Naver Blog automation.

## Publishing Failures

### Symptom: "Page Not Found" After Publish

**Error Log**:
```
URL changed to: https://blog.naver.com/PostView.naver?...
But page shows: 페이지를 찾을 수 없습니다
```

**Cause**: Foreign IP blocked by Naver

**Solution**: Use Korean VPS (Vultr Seoul, Oracle Cloud Korea)

**Verification**:
```bash
# Check your server IP location
curl ipinfo.io

# Should show: "country": "KR"
```

### Symptom: Publish Button Not Found

**Error Log**:
```
Playwright timeout: locator.click: Timeout 30000ms exceeded
Element not found: button[class*="publish_btn"]
```

**Causes & Solutions**:

1. **Window size mismatch**
   ```python
   # Ensure in auto_post.py
   viewport={"width": 1920, "height": 1080}
   ```

2. **Naver UI changed**
   - Add debug screenshot before click:
   ```python
   await page.screenshot(path="logs/publish_button_debug.png")
   ```
   - Inspect screenshot for new button class
   - Update selectors in `auto_post.py`

3. **Element hidden by popup**
   ```python
   # Close any overlays first
   await self._check_and_handle_popup()
   ```

### Symptom: Post Left in "작성중" (Draft) State

**Check**:
```bash
# View temp posts
python scripts/check-temp-posts.py
```

**Cause**: Final confirmation button not clicked

**Solution**: Add more selector fallbacks:
```python
FINAL_PUBLISH_SELECTORS = [
    'button:has-text("발행")',
    'button:has-text("확인")',
    'button[class*="confirm"]',
    # Add new selectors found in screenshot
]
```

## Session Issues

### Symptom: Session Expired

**Error**: `SessionExpiredError: Session expired or invalid`

**Solution**:
```bash
# 1. Re-login locally (with GUI)
python manual_login_clipboard.py

# 2. Transfer to server
scp data/sessions/*.encrypted root@SERVER:/root/naver-blog-bot/data/sessions/
scp secrets/encryption.key root@SERVER:/root/naver-blog-bot/secrets/

# 3. Restart container
docker restart naver-blog-bot
```

### Symptom: Session Decryption Failed

**Error**: `cryptography.fernet.InvalidToken`

**Cause**: Encryption key mismatch

**Solution**:
```bash
# Ensure same encryption key on local and server
md5sum secrets/encryption.key  # Run on both machines
# Hashes must match!

# If different, copy from local to server
scp secrets/encryption.key root@SERVER:/root/naver-blog-bot/secrets/
```

## API Errors

### Claude API

**Error**: `anthropic.RateLimitError: 429 Too Many Requests`

**Solution**:
```python
# Implement exponential backoff (already in code)
# Or reduce posting frequency

MAX_DAILY_POSTS = 10  # Down from 12
MIN_POST_INTERVAL_HOURS = 2  # Up from 1
```

**Error**: `anthropic.AuthenticationError: 401 Unauthorized`

**Solution**:
```bash
# Verify API key
grep ANTHROPIC_API_KEY .env

# Test key manually
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-haiku-20241022","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### Perplexity API

**Error**: `openai.RateLimitError: Rate limit reached`

**Solution**:
```python
# Check daily usage
python scripts/check-api-usage.py

# Reduce research frequency
# Or upgrade to Pro plan ($20/month)
```

### Gemini Image API

**Error**: `'Models' object has no attribute 'generate_images'`

**Cause**: Using old Imagen API instead of Gemini 3 Pro

**Solution**: Already fixed in `utils/gemini_image.py`:
```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",  # Not imagen
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE']
    )
)
```

**Error**: `400 Bad Request: media_resolution not supported`

**Cause**: Using Vertex AI parameters with Google AI API

**Solution**: Remove unsupported parameters:
```python
# ❌ Don't use these in Google AI
image_config=types.ImageConfig(
    aspect_ratio="16:9",  # Not supported
    image_size="1K"       # Not supported
)

# ✅ Use simple config
config=types.GenerateContentConfig(
    response_modalities=['IMAGE']
)
```

## Docker Issues

### Container Exits Immediately

**Check logs**:
```bash
docker logs naver-blog-bot

# Common errors:
# - Missing .env file
# - Invalid Python syntax
# - Missing dependencies
```

**Solution**:
```bash
# Rebuild with no cache
docker build --no-cache -t naver-blog-bot:latest .

# Check .env exists
ls -la .env

# Verify all API keys set
grep -E "API_KEY|NAVER" .env
```

### Out of Memory (OOM) Killed

**Symptom**: Container restarts unexpectedly

**Check**:
```bash
docker inspect naver-blog-bot | grep OOMKilled
# If "true", memory limit too low
```

**Solution**:
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1200M  # Increase from 900M
```

### Cannot Access Session Files

**Error**: `PermissionError: [Errno 13] Permission denied: 'data/sessions/...'`

**Solution**:
```bash
# Fix ownership
chown -R 1000:1000 data/ logs/ secrets/

# Or run container as root (less secure)
docker run --user root ...
```

## Browser Automation Issues

### CDP Connection Timeout

**Error**: `TimeoutError: Waiting for CDP endpoint timeout`

**Solution**: Set in `.env`:
```bash
USE_CDP=False
CDP_TIMEOUT=3
```

### Element Not Interactable

**Error**: `playwright._impl._api_types.Error: Element is not visible`

**Debug Steps**:
1. Take screenshot before interaction
2. Check if element hidden by overlay
3. Scroll element into view
4. Add wait for visibility

```python
# Ensure visible and interactable
element = page.locator(selector)
await element.scroll_into_view_if_needed()
await element.wait_for(state="visible", timeout=30000)
await element.wait_for(state="attached", timeout=30000)
await element.click()
```

### Strikethrough Format Applied Unexpectedly

**Symptom**: Blog text has strikethrough lines

**Solution**: Already handled in `auto_post.py`:
```python
async def _disable_all_formatting_buttons(self):
    """Force disable strikethrough before typing"""
    btn = self.page.locator('button.se-strikethrough-toolbar-button')
    if await btn.is_visible() and 'se-is-selected' in await btn.get_attribute('class'):
        await btn.click()
        logger.success("Strikethrough disabled")
```

## System Resource Issues

### High CPU Usage

**Symptom**: `docker stats` shows 95%+ CPU

**Causes**:
- Image generation (Gemini) - normal, temporary
- Multiple Chromium instances - check for leaks

**Solution**:
```bash
# Check for orphan Chromium processes
docker exec naver-blog-bot ps aux | grep chromium

# Kill if needed
docker exec naver-blog-bot pkill chromium

# Restart container
docker restart naver-blog-bot
```

### High Memory Usage

**Symptom**: Container using >90% of limit

**Solution**:
```bash
# Increase shm_size
docker run --shm-size=4gb ...  # Up from 2gb

# Or reduce concurrent operations
# Generate images one at a time (already implemented)
```

### Disk Space Full

**Symptom**: `No space left on device`

**Solution**:
```bash
# Clean Docker
docker system prune -a

# Remove old logs
find logs/ -name "*.log" -mtime +7 -delete

# Remove old images
find generated_images/ -name "*.png" -mtime +14 -delete

# Check database size
du -sh data/*.db
# If large, vacuum it
sqlite3 data/blog_bot.db "VACUUM;"
```

## Debugging Workflow

### Enable Debug Mode

```bash
# In .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Take Screenshots at Every Step

```python
# Add to critical steps
await page.screenshot(path=f"logs/debug_{step_name}.png")
```

### Log Page HTML

```python
# Debug element not found
html = await page.content()
with open("logs/page_source.html", "w") as f:
    f.write(html)
```

### Test in Non-Headless Mode Locally

```bash
# Run locally with visible browser
HEADLESS=False python auto_post.py wncksdid0750 "Test" "Content"
```

### Use Playwright Inspector

```bash
# Interactive debugging
PWDEBUG=1 python auto_post.py ...

# Opens inspector UI
# Step through actions
# Inspect selectors
```

## Recovery Procedures

### Complete System Reset

```bash
# 1. Stop container
docker stop naver-blog-bot
docker rm naver-blog-bot

# 2. Clean data (BACKUP FIRST!)
mv data data.backup
mkdir -p data/sessions

# 3. Re-login and transfer session
python manual_login_clipboard.py  # On local machine
scp data/sessions/*.encrypted root@SERVER:/root/naver-blog-bot/data/sessions/

# 4. Rebuild and restart
docker build -t naver-blog-bot:latest .
docker-compose up -d

# 5. Monitor logs
docker logs naver-blog-bot -f
```

### Session Corruption Recovery

```bash
# Delete corrupted session
rm data/sessions/wncksdid0750_clipboard.session.encrypted

# Re-login locally
python manual_login_clipboard.py

# Transfer new session
scp data/sessions/*.encrypted root@SERVER:/root/naver-blog-bot/data/sessions/
```

### Database Corruption Recovery

```bash
# Backup first
cp data/blog_bot.db data/blog_bot.db.backup

# Check integrity
sqlite3 data/blog_bot.db "PRAGMA integrity_check;"

# If corrupted, restore from backup or recreate
rm data/blog_bot.db
python -c "from models.database import init_database; init_database()"
```

## Monitoring and Alerts

### Set Up Telegram Alerts

```bash
# In .env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Test
python utils/telegram_notifier.py test
```

### Log Monitoring with grep

```bash
# Watch for errors in real-time
docker logs naver-blog-bot -f | grep -i error

# Count failures today
docker logs naver-blog-bot --since "$(date +%Y-%m-%d)" | grep -c "ERROR"

# Find specific error
docker logs naver-blog-bot | grep "SessionExpiredError"
```

### Automated Health Checks

```bash
# Add to crontab
*/15 * * * * docker exec naver-blog-bot python monitoring/health_checker.py || echo "Health check failed" | mail -s "Blog Bot Alert" admin@example.com
```

## Getting Help

### Collect Diagnostic Information

```bash
# Run diagnostic script
bash scripts/collect-diagnostics.sh > diagnostics.txt

# Includes:
# - Docker version
# - Container status
# - Recent logs (last 500 lines)
# - System resources
# - Environment variables (sanitized)
# - Session status
```

### Report Issues

When reporting issues, include:
1. Error message (full traceback)
2. Relevant log snippet (before and after error)
3. Steps to reproduce
4. Environment (local/Docker, OS, Python version)
5. Diagnostics output

---

**End of Troubleshooting Guide**
