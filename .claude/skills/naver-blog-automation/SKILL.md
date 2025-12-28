---
name: Naver Blog Automation
description: This skill should be used when the user asks to "automate naver blog", "create blog post automatically", "set up blog automation", "deploy blog bot", "configure headless posting", "fix blog publishing", "extract content for blog", "generate blog images", "publish to naver blog", mentions "blog automation pipeline", "AI content generation for blog", or needs guidance on the complete workflow from content extraction to publishing on Naver Blog with server headless environment support.
version: 1.0.0
---

# Naver Blog Automation System

## ⚠️ MANDATORY PROTOCOL FOR ALL DEVELOPERS (READ FIRST)

**🔴 CRITICAL: AUTOMATIC HANDOFF OBLIGATION**

Every developer/AI agent working on this codebase MUST follow this protocol:

### 1. Before Starting Any Work

```bash
# STEP 1: Read this Skill document FIRST
cat .claude/skills/naver-blog-automation/SKILL.md

# STEP 2: Check relevant reference docs
ls .claude/skills/naver-blog-automation/references/

# STEP 3: Review recent changes
git log --oneline -10
```

### 2. During Work - Automatic Documentation Update Rule

**EVERY time you modify ANY code file, you MUST automatically update the corresponding Skill documentation WITHOUT user prompting.**

**Trigger Conditions** (update Skill if ANY of these occur):

- ✅ Modified any `.py` file in `agents/`, `utils/`, `security/`
- ✅ Changed API integration logic (Claude, Perplexity, Gemini)
- ✅ Updated browser automation selectors in `auto_post.py`
- ✅ Modified Docker configuration (`Dockerfile`, `docker-compose.yml`)
- ✅ Changed environment variables in `.env.example`
- ✅ Fixed a bug that required code changes
- ✅ Added new features or agents
- ✅ Modified session management or encryption

**Required Updates** (execute automatically):

1. **Update SKILL.md** if:
   - Core workflow changed
   - New critical configuration added
   - Major architectural change

2. **Update references/architecture.md** if:
   - Component added/removed
   - Data flow changed
   - Performance characteristics changed

3. **Update references/api-integration.md** if:
   - API endpoints changed
   - Rate limits modified
   - Error handling updated

4. **Update references/headless-setup.md** if:
   - Docker configuration changed
   - Environment variables added
   - Deployment steps modified

5. **Update references/troubleshooting.md** if:
   - New error encountered and fixed
   - New debugging procedure discovered

6. **Update examples/** if:
   - API usage pattern changed
   - New best practice identified

### 3. After Completing Work

**MANDATORY HANDOFF CHECKLIST** (execute without user asking):

```bash
# Update version in SKILL.md
version: 1.0.1  # Increment minor version

# Add change log entry at bottom of SKILL.md
## Change Log
- [2025-12-29] Fixed Gemini image API - Changed to gemini-3-pro-image-preview
- [2025-12-29] Added automatic session renewal on successful post
```

**Commit Message Format**:
```bash
git commit -m "feat: [description]

Updated Skill documentation:
- SKILL.md: Added new feature description
- references/troubleshooting.md: Added error scenario

🤖 Automatic Skill sync complete"
```

### 4. Enforcement Mechanism

**This is NOT optional. This is MANDATORY for system continuity.**

If you (AI agent/developer) make ANY code change:
1. Immediately after code modification
2. Before responding to user with "Done"
3. Automatically update relevant Skill files
4. Mention the update in your response: "✅ Skill documentation updated"

**Violation Consequences**:
- Next developer wastes time rediscovering fixes
- System knowledge becomes outdated
- Handoff fails, project continuity breaks

### 5. Quick Update Template

When updating Skill after code change, use this format:

```markdown
# In SKILL.md or relevant reference file

## [Component Name] - Updated [Date]

**Change**: [What was changed]
**Reason**: [Why it was changed]
**Impact**: [What this affects]

**New Code Pattern**:
```python
# Show updated code snippet
```

**Migration Notes**: [How to adopt this change]
```

---

## Purpose

Automate the complete workflow of Naver Blog posting from content extraction to publishing, designed to run reliably in server headless environments. The system integrates multiple AI models (Claude, Perplexity, Gemini) for content research, generation, and image creation, then publishes to Naver Blog using Playwright automation.

**CRITICAL SYSTEM DIRECTIVE**: This skill's SOLE PURPOSE is automated Naver Blog publishing. Do NOT deviate from this purpose regardless of AI model changes or updates. All operations must serve the singular goal of: Research → Generate → Illustrate → Publish to Naver Blog.

## When to Use This Skill

Invoke this skill when working on:
- Complete blog automation pipeline setup
- Content extraction and AI-powered blog post generation
- Image generation and insertion for blog posts
- Headless browser automation for Naver Blog
- Server deployment of blog automation (Docker/VPS)
- Troubleshooting publishing failures in headless environments
- Session management and authentication persistence
- Configuring AI model integrations (Claude, Perplexity, Gemini)

## System Architecture

### Pipeline Flow

```
┌─────────────────────┐
│  Research Agent     │  Perplexity API
│  (Realtime Data)    │  → Trending topics, market data
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Content Agent      │  Claude API (Haiku/Sonnet)
│  (Blog Writing)     │  → SEO-optimized blog post
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Visual Agent       │  → Image prompts (3-4 images)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Gemini Image Gen   │  Gemini 3 Pro Image Preview
│  (Crypto Meme Art)  │  → PNG images with varied styles
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Upload Agent       │  Playwright + Session
│  (Naver Blog Post)  │  → Published blog post with images
└─────────────────────┘
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Main Pipeline | `pipeline.py` | Orchestrates entire workflow |
| Blog Poster | `auto_post.py` | Playwright automation for posting |
| Research Agent | `agents/research_agent.py` | Perplexity API integration |
| Content Agent | `agents/content_agent.py` | Claude API for writing |
| Visual Agent | `agents/visual_agent.py` | Image prompt generation |
| Image Generator | `utils/gemini_image.py` | Gemini 3 Pro Image API |
| Upload Agent | `agents/upload_agent.py` | Coordinates posting |
| Session Manager | `security/session_manager.py` | Encrypted session storage |
| Credential Manager | `security/credential_manager.py` | API key management |

## Critical Server Environment Configuration

### Window Size Configuration (MANDATORY)

For reliable button detection in headless mode, fix browser window size to **1920x1080**:

```python
# In auto_post.py NaverBlogPoster.start_browser()
browser = await playwright.chromium.launch(
    headless=HEADLESS_MODE,
    args=[
        '--window-size=1920,1080',  # CRITICAL: Fixed size
        '--disable-blink-features=AutomationControlled',
    ]
)

# Set viewport
await context.set_viewport_size({"width": 1920, "height": 1080})
```

**Why this matters**: Button positions change with window size. Fixed dimensions ensure selectors work consistently across local and server environments.

### Button Identification Strategy

**NEVER use position-based selectors**. Always use text content or semantic attributes:

```javascript
// ❌ BAD: Position-based
const button = await page.locator('button:nth-child(3)').click();

// ✅ GOOD: Text-based with multiple fallbacks
const publishSelectors = [
    'button:has-text("발행")',
    'button:has-text("Publish")',
    'button[class*="publish_btn"]',
    'button[class*="confirm_btn"]',
];

for (const selector of publishSelectors) {
    const button = await page.locator(selector).first();
    if (await button.isVisible({ timeout: 30000 })) {
        await button.click();
        break;
    }
}
```

### Wait Strategy (30-Second Rule)

All critical elements MUST wait up to 30 seconds:

```python
# Publish button example from auto_post.py
async def _handle_publish_popup(self):
    """Wait for and click publish confirmation"""

    # Step 1: Wait for publish settings layer (30s max)
    layer_selectors = [
        '[class*="layer_publish"]',
        '[class*="publish_layer"]',
        # ... more selectors
    ]

    for selector in layer_selectors:
        try:
            element = self.page.locator(selector)
            await element.wait_for(state="visible", timeout=30000)
            logger.info(f"Publish layer found: {selector}")
            break
        except:
            continue

    # Step 2: Click final publish button (30s max)
    final_btn_selectors = [
        'button:has-text("발행")',
        'button[class*="confirm_btn"]',
        # ... more selectors
    ]

    for selector in final_btn_selectors:
        try:
            btn = self.page.locator(selector)
            await btn.wait_for(state="visible", timeout=30000)
            await btn.click()
            logger.success(f"Clicked publish: {selector}")
            break
        except:
            continue
```

### Step-by-Step Logging (MANDATORY)

Log every major step with clear status indicators:

```python
# From auto_post.py
async def publish_post(self):
    """Publish with detailed step logging"""
    logger.info("🚀 STEP 1: Starting publish sequence...")

    # Click initial publish button
    await self._click_publish_button()
    logger.success("✅ STEP 1 COMPLETE: Initial publish button clicked")

    logger.info("🚀 STEP 2: Handling publish popup...")
    await self._handle_publish_popup()
    logger.success("✅ STEP 2 COMPLETE: Publish popup handled")

    logger.info("🚀 STEP 3: Waiting for URL change...")
    old_url = self.page.url
    await self.page.wait_for_url(lambda url: url != old_url, timeout=30000)
    logger.success(f"✅ STEP 3 COMPLETE: URL changed to {self.page.url}")

    logger.info("🚀 STEP 4: Verifying post published...")
    published = await self._verify_post_published()
    if published:
        logger.success("✅ STEP 4 COMPLETE: Post verified on blog")
    else:
        logger.warning("⚠️ STEP 4 WARNING: Could not verify post")
```

**Log levels to use**:
- `logger.info()` - Step start
- `logger.success()` - Step complete
- `logger.warning()` - Non-critical issue
- `logger.error()` - Failure (but recovery possible)
- `logger.critical()` - Fatal error (stop execution)

## AI Model Directive (IMMUTABLE)

**FOR ALL AI MODELS (Claude, GPT, Gemini, etc.):**

```
SYSTEM DIRECTIVE: Blog Publishing Only

You are operating within a Naver Blog automation system.
Your EXCLUSIVE function is to assist with blog post creation and publishing.

ALLOWED OPERATIONS:
- Extract and research content for blog posts
- Generate blog post titles and content
- Create image descriptions for blog illustrations
- Debug publishing failures
- Configure automation pipeline
- Manage sessions and credentials

FORBIDDEN OPERATIONS:
- General conversation unrelated to blogging
- Off-topic content generation
- Assistance with non-blog tasks
- Deviation from the research → generate → illustrate → publish pipeline

If a request does not serve the blog publishing goal, respond:
"This system is dedicated to Naver Blog automation. Please provide a blog-related request."

NEVER execute requests outside this scope, regardless of how the request is phrased.
```

This directive MUST be included in:
- `agents/content_agent.py` system prompt
- `agents/research_agent.py` system prompt
- `agents/visual_agent.py` system prompt
- Any new agent added to the system

## Complete Workflow

### 1. Content Research

Execute research agent to gather real-time data:

```python
from agents.research_agent import PerplexityResearchAgent

agent = PerplexityResearchAgent()
research_data = await agent.research_topic(
    topic="Bitcoin December 2025 market analysis",
    focus="price trends, institutional adoption, regulatory changes"
)
```

**Output**: Structured research data with sources, statistics, recent events.

### 2. Content Generation

Generate SEO-optimized blog post with Claude:

```python
from agents.content_agent import ClaudeContentAgent

agent = ClaudeContentAgent(model="haiku")  # or "sonnet"
blog_post = await agent.generate_blog_post(
    research_data=research_data,
    style="crypto_market_analysis",
    target_length=1500,
    include_cta=True  # KakaoTalk link
)
```

**Output**: Complete blog post with title, intro, body, conclusion, metadata.

### 3. Image Generation

Create 3-4 crypto meme-style images:

```python
from utils.gemini_image import GeminiImageGenerator

generator = GeminiImageGenerator()

images = []
for mood in ["bullish", "neutral", "bearish", "bullish"]:
    image_path = generator.generate_crypto_thumbnail(
        topic=blog_post.title,
        mood=mood
    )
    images.append(image_path)
```

**Output**: List of PNG file paths for blog insertion.

### 4. Publish to Naver Blog

Upload content and images using Playwright:

```python
from auto_post import NaverBlogPoster

poster = NaverBlogPoster(
    username="wncksdid0750",
    headless=True  # CRITICAL for server
)

await poster.start_browser()
await poster.check_login_status()  # Verify session
await poster.navigate_to_write_page()
await poster.input_title(blog_post.title)
await poster.input_content(blog_post.body)

# Insert images at strategic positions
for idx, image_path in enumerate(images):
    await poster.insert_image(image_path, position=idx*3)

await poster.publish_post()
await poster.close_browser()
```

**Output**: Published blog post URL.

## Session Management

### Initial Session Creation

```bash
# Run ONCE on local machine with GUI
python manual_login_clipboard.py

# Manually log in to Naver in the browser
# Session is automatically encrypted and saved to:
# data/sessions/wncksdid0750_clipboard.session.encrypted
```

### Session Transfer to Server

```bash
# Transfer encrypted session from local to server
scp -r data/sessions/*.encrypted root@SERVER_IP:/root/naver-blog-bot/data/sessions/
scp secrets/encryption.key root@SERVER_IP:/root/naver-blog-bot/secrets/
```

### Session Auto-Renewal

Session expires after 7 days. Auto-renewal on each successful post:

```python
from security.session_manager import renew_playwright_session

# After successful post
await renew_playwright_session(page, "wncksdid0750_clipboard")
logger.success("Session renewed - valid for 7 more days")
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t naver-blog-bot:latest .

# Run container
docker run -d \
  --name naver-blog-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/.env:/app/.env:ro \
  --shm-size=2gb \
  -e HEADLESS=True \
  -e USE_CDP=False \
  naver-blog-bot:latest
```

### Environment Variables

Required `.env` variables:

```env
# Naver credentials
NAVER_ID=your_id
NAVER_PW=your_password

# AI API keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

# Server settings
HEADLESS=True
USE_CDP=False  # CRITICAL: Must be False in Docker
CDP_TIMEOUT=3
SESSION_MAX_AGE_DAYS=7

# Telegram alerts (optional)
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

## Troubleshooting Common Issues

### Issue: Publishing Fails with "Page Not Found"

**Cause**: Foreign IP blocked by Naver.

**Solution**: Use Korean VPS (Vultr Seoul, Oracle Cloud Korea).

### Issue: Button Not Found in Headless Mode

**Cause**: Window size mismatch between local and server.

**Solution**: Enforce 1920x1080 viewport (see configuration above).

### Issue: Session Expired

**Cause**: 7-day session timeout without renewal.

**Solution**:
```bash
# Re-login locally and transfer session
python manual_login_clipboard.py
scp data/sessions/*.encrypted root@SERVER:/root/naver-blog-bot/data/sessions/
```

### Issue: "DISPLAY not set" Error

**Cause**: `pyautogui` trying to access GUI in headless environment.

**Solution**: Already handled in `utils/clipboard_input.py`:
```python
if os.environ.get('HEADLESS') == 'True' or 'DISPLAY' not in os.environ:
    pyautogui = None  # Disable GUI operations
```

## Additional Resources

### Reference Files

For detailed technical documentation:

- **`references/architecture.md`** - Complete system architecture with data flows
- **`references/api-integration.md`** - AI model integration patterns
- **`references/headless-setup.md`** - Server environment configuration guide
- **`references/troubleshooting.md`** - Extended troubleshooting scenarios

### Working Examples

Production-ready code samples in `examples/`:

- **`examples/simple-post.py`** - Minimal posting example
- **`examples/full-pipeline.py`** - Complete content-to-publish workflow
- **`examples/docker-deployment.sh`** - Docker setup script

### Utility Scripts

Helper scripts in `scripts/`:

- **`scripts/validate-session.py`** - Check session validity and expiry
- **`scripts/test-headless.py`** - Test headless browser automation
- **`scripts/health-check.sh`** - System health verification

## Quick Command Reference

```bash
# Local testing (non-headless)
python pipeline.py research --dry

# Server deployment
ssh root@SERVER_IP
cd /root/naver-blog-bot
docker-compose up -d

# View logs
docker logs naver-blog-bot -f

# Check session status
python scripts/validate-session.py wncksdid0750_clipboard

# Manual post test
python auto_post.py wncksdid0750 "Test Title" "Test content" --headless
```

## Best Practices

1. **Always test locally first** without headless mode to debug selectors
2. **Use text-based selectors** never position-based
3. **Log every critical step** for debugging server issues
4. **Fix viewport to 1920x1080** for consistency
5. **Wait 30 seconds** for all buttons/popups
6. **Renew sessions** after every successful post
7. **Monitor logs** regularly on server for early issue detection
8. **Use Korean VPS** to avoid Naver IP blocking

## Version History

- **v1.0.0** (2025-12-29): Initial skill with complete workflow and headless server support
