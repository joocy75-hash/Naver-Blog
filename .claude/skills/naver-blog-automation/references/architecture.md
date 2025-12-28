# System Architecture - Detailed Reference

## Overview

The Naver Blog Automation system is a multi-agent pipeline that orchestrates content research, generation, illustration, and publishing. Each component is designed for reliability in server environments and handles failures gracefully.

## Component Architecture

### Layer 1: Orchestration

**File**: `pipeline.py`

**Purpose**: Coordinates all agents and manages workflow state.

**Key Functions**:

```python
async def run_research_pipeline():
    """
    Complete pipeline: Research → Generate → Illustrate → Publish

    Flow:
    1. Research Agent collects data from Perplexity API
    2. Content Agent generates blog post with Claude
    3. Visual Agent creates image prompts
    4. Gemini generates 3-4 crypto meme images
    5. Upload Agent publishes to Naver Blog
    6. Telegram notification sent
    """

async def run_marketing_pipeline():
    """
    Simpler pipeline for promotional content
    """
```

**State Management**:
- Tracks completion of each stage
- Stores intermediate results (research data, generated content, image paths)
- Handles rollback on failure
- Logs all state transitions

### Layer 2: AI Agents

#### Research Agent

**File**: `agents/research_agent.py`

**Purpose**: Gather real-time market data and trending topics.

**API**: Perplexity `sonar-pro` model

**Key Method**:
```python
async def research_topic(topic: str, focus: str = None) -> Dict:
    """
    Returns:
    {
        "summary": "Market overview...",
        "key_points": ["Point 1", "Point 2", ...],
        "statistics": {"BTC price": "$98,000", ...},
        "sources": ["https://...", ...]
    }
    """
```

**Rate Limiting**:
- Max 50 requests/day
- Cooldown: 60 seconds between requests
- Tracked in `data/api_usage.json`

#### Content Agent

**File**: `agents/content_agent.py`

**Purpose**: Generate SEO-optimized blog posts.

**API**: Claude (Haiku 4.5 or Sonnet 4.5)

**Key Method**:
```python
async def generate_blog_post(
    research_data: Dict,
    style: str = "crypto_market_analysis",
    target_length: int = 1500
) -> Dict:
    """
    Returns:
    {
        "title": "Bitcoin Breaks $100K...",
        "meta_description": "...",
        "body": "Full blog post with headings...",
        "tags": ["Bitcoin", "Crypto", ...],
        "cta_text": "Join our KakaoTalk..."
    }
    """
```

**CRITICAL System Prompt**:
```
You are a specialized blog content generator for crypto market analysis.

STRICT RULES:
1. Generate ONLY blog post content
2. Focus on cryptocurrency and investment topics
3. Include KakaoTalk CTA at the end
4. Follow Korean blog style (친근한 말투)
5. NEVER respond to off-topic requests

Output format: JSON with title, body, meta_description, tags
```

**Token Management**:
- Haiku: ~100K tokens/day limit
- Sonnet: ~50K tokens/day limit
- Uses token counter to prevent overage
- Automatically switches to Haiku when Sonnet quota low

#### Visual Agent

**File**: `agents/visual_agent.py`

**Purpose**: Generate image prompts for Gemini.

**Method**:
```python
def generate_image_prompts(
    blog_content: str,
    count: int = 4
) -> List[Dict]:
    """
    Analyzes blog content and creates prompts like:
    [
        {
            "position": 1,  # Insert after paragraph 1
            "mood": "bullish",
            "prompt": "a rocket-riding Shiba Inu..."
        },
        ...
    ]
    """
```

**Prompt Engineering**:
- Incorporates crypto meme culture (Pepe, Doge, Bull/Bear)
- Uses vivid action verbs ("soaring", "crashing", "exploding")
- Specifies "no text, no watermarks, no human faces"
- Varies art styles (cyberpunk, pixel art, 3D render)

#### Upload Agent

**File**: `agents/upload_agent.py`

**Purpose**: Coordinate the posting process.

**Responsibilities**:
1. Initialize NaverBlogPoster
2. Load session from encrypted file
3. Call poster methods in sequence
4. Handle errors and retry logic
5. Renew session on success
6. Return published URL

**Error Recovery**:
```python
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds

for attempt in range(MAX_RETRIES):
    try:
        url = await post_to_blog(...)
        await renew_session()
        return url
    except SessionExpiredError:
        logger.error("Session expired - manual re-login required")
        raise
    except NetworkError:
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY)
            continue
        raise
```

### Layer 3: Utilities

#### Gemini Image Generator

**File**: `utils/gemini_image.py`

**Class**: `GeminiImageGenerator`

**API**: Google Gemini 3 Pro Image Preview

**Key Method**:
```python
def generate_crypto_thumbnail(
    topic: str,
    mood: str = "neutral"  # bullish, bearish, neutral
) -> str:
    """
    Generates random combinations:
    - Character: 16 options (frog, doge, bull, robot, etc.)
    - Action: 8-12 options per mood
    - Background: 6-10 options per mood
    - Art style: 12 styles
    - Color palette: 4 per mood

    Returns: Path to generated PNG (700KB-1.1MB)
    """
```

**Performance**:
- Generation time: 15-17 seconds per image
- Resolution: ~1024x576 (auto 16:9)
- File size: 700KB - 1.1MB
- Concurrent limit: 1 (sequential generation)

**Randomization Strategy**:
Every image is unique through:
1. Random character selection (16 options)
2. Random action (varies by mood)
3. Random background (varies by mood)
4. Random art style (12 styles)
5. Random color palette (4 per mood)

Example combinations:
- "a wise cartoon cat with glowing cyber eyes breaking through a giant wall of resistance, mountain peak above clouds at sunrise, golden glow and vibrant green neon, cyberpunk neon art high contrast"
- "a superhero with cape made of golden coins surfing on a massive green candlestick wave, rainbow bridge leading to golden gates, pink and gold luxury aesthetic, anime style vibrant colors"

#### Session Manager

**File**: `security/session_manager.py`

**Class**: `SecureSessionManager`

**Encryption**: AES-256-GCM with Fernet

**Key Methods**:
```python
def save_session(session_data: dict, session_name: str):
    """
    Encrypts and saves Playwright session:
    - Cookies
    - Local storage
    - Session storage
    - Creation timestamp
    - Last renewal timestamp
    """

def load_session(session_name: str) -> dict:
    """
    Decrypts and loads session
    Checks expiry (7 days from last_renewed_at)
    Raises SessionExpiredError if invalid
    """

def renew_session(session_name: str):
    """
    Updates last_renewed_at timestamp
    Extends validity by 7 days
    Called after each successful post
    """

def get_days_until_expiry(session_name: str) -> int:
    """
    Calculates remaining days
    Used for expiry warnings (3, 2, 1 day alerts)
    """
```

**Session File Format** (encrypted):
```json
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://blog.naver.com",
      "localStorage": [...],
      "sessionStorage": [...]
    }
  ],
  "created_at": "2025-12-29T12:00:00",
  "last_renewed_at": "2025-12-29T16:30:00"
}
```

**Encryption Key Location**: `secrets/encryption.key` (64-byte Fernet key)

#### Credential Manager

**File**: `security/credential_manager.py`

**Class**: `CredentialManager`

**Storage**:
- **Local**: macOS Keychain (keyring library)
- **Docker**: Environment variables only

**Auto-Detection**:
```python
def is_docker_environment() -> bool:
    """
    Checks:
    1. /.dockerenv file exists
    2. /proc/1/cgroup contains 'docker'
    3. RUNNING_IN_DOCKER env var set
    """

if is_docker_environment():
    # Skip keychain, use .env only
    KEYRING_AVAILABLE = False
```

**API Key Retrieval Priority**:
1. Environment variable (`.env` file)
2. macOS Keychain (if not Docker)
3. Fallback prompt (interactive only)

#### Clipboard Input Helper

**File**: `utils/clipboard_input.py`

**Purpose**: Handle text input in both GUI and headless modes.

**Auto-Detection**:
```python
_headless_mode = (
    os.environ.get('HEADLESS', 'False').lower() == 'true' or
    'DISPLAY' not in os.environ
)

if _headless_mode:
    pyautogui = None  # Disable GUI operations
```

**Input Methods**:
- **Headless**: Playwright `locator.fill(text)` directly
- **GUI**: pyautogui for paste simulation (more human-like)

### Layer 4: Browser Automation

#### Naver Blog Poster

**File**: `auto_post.py`

**Class**: `NaverBlogPoster`

**Initialization**:
```python
poster = NaverBlogPoster(
    username="wncksdid0750",
    headless=True,  # Server mode
    window_size=(1920, 1080)  # CRITICAL: Fixed size
)
```

**Complete Posting Flow**:

```
start_browser()
    ↓
launch Playwright Chromium
set viewport 1920x1080
load encrypted session
    ↓
check_login_status()
    ↓
verify profile icon visible
    ↓
navigate_to_write_page()
    ↓
go to blog.naver.com/write/
wait for editor (.se-component-content)
handle any popups
    ↓
input_title(title)
    ↓
locate title field
type character-by-character (50-100ms delay)
verify input with JavaScript
    ↓
input_content(content)
    ↓
disable formatting (bold, italic, strikethrough)
split content by lines
type each line with delays
handle markdown bold (**text**)
    ↓
insert_image(image_path, position)
    ↓
click image button
upload file
wait for thumbnail
insert at position
    ↓
publish_post()
    ↓
[CRITICAL STEP 1] click initial publish button
    selectors: button[class*="publish_btn"], etc.
    wait: 30 seconds max
    ↓
[CRITICAL STEP 2] handle publish popup
    wait for layer: [class*="layer_publish"]
    wait: 30 seconds max
    ↓
[CRITICAL STEP 3] click final confirm button
    selectors: button:has-text("발행"), button[class*="confirm_btn"]
    wait: 30 seconds max
    ↓
[CRITICAL STEP 4] wait for URL change
    old URL: /write/...
    new URL: /PostView.naver?...
    timeout: 30 seconds
    ↓
[CRITICAL STEP 5] verify post published
    navigate to blog main page
    find post in list by title
    timeout: 10 seconds
    ↓
close_browser()
```

**Button Selector Strategy**:

All buttons use **cascading selectors** with text-based fallbacks:

```python
PUBLISH_BUTTON_SELECTORS = [
    'button:has-text("발행")',           # Text: Korean
    'button:has-text("Publish")',       # Text: English
    'button[class*="publish_btn"]',    # Class attribute
    'button[data-testid="publish"]',   # Data attribute
    '.publish-button',                 # CSS class
]

for selector in PUBLISH_BUTTON_SELECTORS:
    try:
        btn = page.locator(selector).first()
        if await btn.is_visible(timeout=30000):
            await btn.click()
            logger.success(f"Clicked: {selector}")
            return
    except Exception as e:
        logger.debug(f"Selector failed: {selector} - {e}")
        continue

raise PublishError("Could not find publish button")
```

**Human Behavior Simulation**:

```python
class HumanDelay:
    DELAYS = {
        "before_click": (0.3, 0.7),      # Random 300-700ms
        "after_click": (0.5, 1.2),       # Random 500-1200ms
        "before_type": (0.3, 0.6),       # Before typing
        "between_fields": (0.8, 1.5),    # Between title and content
        "popup_react": (0.8, 1.5),       # Popup appears
    }

    TYPING = {
        "title_min": 50,     # Fastest typing: 50ms/char
        "title_max": 100,    # Slowest typing: 100ms/char
        "content_min": 40,
        "content_max": 80,
    }

    @classmethod
    async def wait(cls, delay_type: str):
        min_delay, max_delay = cls.DELAYS[delay_type]
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
```

**Safe Mode** (optional):
- Multiplies all delays by 1.5x
- Enabled via `SAFE_MODE=True` in `.env`
- Use when Naver increases bot detection

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User/Scheduler                        │
│              "Create crypto market post"                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   pipeline.py                            │
│            run_research_pipeline()                       │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Perplexity  │ │    Claude    │ │    Gemini    │
│ Research API │ │  Content API │ │  Image API   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │  research_data │  blog_post     │  images/
       │  (JSON)        │  (JSON)        │  (PNG files)
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  data/                         │
        │  ├─ research_data.json        │
        │  ├─ blog_post.json            │
        │  └─ images/                   │
        │     ├─ crypto_meme_1.png     │
        │     ├─ crypto_meme_2.png     │
        │     └─ ...                    │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │      upload_agent.py           │
        │  Coordinates posting process   │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │      auto_post.py              │
        │   NaverBlogPoster class        │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Load Session │ │  Playwright  │ │   Naver      │
│ (encrypted)  │ │  Automation  │ │   Blog       │
└──────────────┘ └──────────────┘ └──────┬───────┘
                                          │
                                          ▼
                               Published Blog Post URL
                                          │
                                          ▼
                          ┌───────────────────────────┐
                          │  telegram_notifier.py     │
                          │  Success/Failure Alert    │
                          └───────────────────────────┘
```

## State Persistence

### Files Created During Operation

```
naver-blog-bot/
├── data/
│   ├── sessions/
│   │   └── wncksdid0750_clipboard.session.encrypted  # Playwright session
│   ├── api_usage.json                                # API rate limiting
│   ├── blog_bot.db                                   # SQLite database
│   └── posts_history.json                            # Published posts log
├── logs/
│   ├── app_2025-12-29.log                           # Daily log rotation
│   ├── publish_popup_before.png                     # Debug screenshots
│   └── publish_popup_after_click.png
├── generated_images/
│   ├── crypto_meme_bullish_20251229_120530.png
│   └── ...
└── secrets/
    └── encryption.key                                # Session encryption key
```

### Database Schema

**File**: `data/blog_bot.db`

**Tables**:

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    title TEXT,
    url TEXT,
    published_at TIMESTAMP,
    status TEXT,  -- 'published', 'failed', 'draft'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY,
    service TEXT,  -- 'claude', 'perplexity', 'gemini'
    endpoint TEXT,
    tokens_used INTEGER,
    cost_usd REAL,
    timestamp TIMESTAMP
);

CREATE TABLE sessions (
    username TEXT PRIMARY KEY,
    last_login TIMESTAMP,
    expiry_date TIMESTAMP,
    status TEXT  -- 'active', 'expired', 'warning'
);
```

## Performance Characteristics

### Timing Benchmarks (Server - Vultr Seoul)

| Operation | Duration | Notes |
|-----------|----------|-------|
| Research (Perplexity) | 8-12s | Depends on query complexity |
| Content Generation (Claude Haiku) | 15-25s | ~1500 words |
| Content Generation (Claude Sonnet) | 30-50s | Higher quality |
| Image Generation (Gemini) per image | 15-17s | 1024x576 PNG |
| Total Image Generation (4 images) | 60-70s | Sequential |
| Browser Launch (Headless) | 2-3s | |
| Session Load | <1s | Decryption |
| Navigate to Write Page | 3-5s | Network + page load |
| Input Title | 2-3s | Character-by-character |
| Input Content (1500 words) | 20-30s | Includes formatting |
| Image Upload (per image) | 3-5s | Depends on file size |
| Publish (button clicks + verification) | 10-15s | Includes popups |
| **Total Pipeline** | **3-5 minutes** | Research to published URL |

### Resource Usage (Docker Container)

**Vultr vc2-1c-1gb (1 vCPU / 1GB RAM)**:

| Metric | Idle | During Post | Peak |
|--------|------|-------------|------|
| CPU | 5-10% | 40-60% | 80% (image gen) |
| Memory | 450MB | 600MB | 800MB |
| Disk I/O | <1 MB/s | 5-10 MB/s | 20 MB/s |
| Network | <1 KB/s | 100-500 KB/s | 2 MB/s |

**Recommended Minimum**: 1 vCPU, 1GB RAM, 10GB SSD

## Error Handling Matrix

| Error Type | Detection | Recovery Strategy | User Action Required |
|------------|-----------|-------------------|---------------------|
| Session Expired | Login check fails | None (manual re-login) | Yes - run manual_login_clipboard.py |
| API Rate Limit | 429 response | Exponential backoff (60s → 120s → 240s) | No |
| Network Timeout | asyncio.TimeoutError | Retry 3 times with 60s delay | No |
| Button Not Found | Playwright timeout (30s) | Try alternative selectors | Possibly - check Naver UI changes |
| Image Upload Fail | Upload verification fails | Retry upload, skip if 3rd failure | No |
| Publish URL No Change | URL same after 30s | Mark as failed, alert admin | Yes - manual verification |
| Disk Space Low | <1GB free | Alert admin, pause scheduler | Yes - clean up logs/images |
| Memory OOM | Docker container killed | Auto-restart (--restart unless-stopped) | No |

## Security Considerations

### Sensitive Data Protection

1. **Session Files**: AES-256 encrypted, key in `secrets/`
2. **API Keys**: Never logged, stored in .env or keychain
3. **Naver Password**: Only in .env, never transmitted (session-based auth)
4. **Encryption Key**: Must be backed up securely, not in Git

### Git Ignore Rules

```gitignore
.env
secrets/
data/sessions/
data/*.db
logs/
*.log
```

### Docker Secrets Management

```yaml
# docker-compose.yml
services:
  naver-blog-bot:
    volumes:
      - ./secrets:/app/secrets:ro  # Read-only mount
    env_file:
      - .env  # Not in image, mounted at runtime
```

## Monitoring and Alerting

### Telegram Notification Levels

| Event | Level | Cooldown |
|-------|-------|----------|
| Post Success | SUCCESS ✅ | None |
| Post Failure | ERROR ❌ | 5 min |
| Session Expiry Warning (3 days) | WARNING ⚠️ | 24 hours |
| API Rate Limit | WARNING ⚠️ | 10 min |
| System Resource High | WARNING ⚠️ | 30 min |
| Critical Error (3 failures) | CRITICAL 🚨 | None |

### Health Check Endpoints

**File**: `monitoring/health_checker.py`

**Checks**:
1. Claude API connection (ping with 1-token request)
2. Perplexity API key validity
3. Gemini API key validity
4. Session file exists and not expired
5. Database accessible
6. Disk space >1GB
7. Memory usage <90%

**Schedule**: Every 15 minutes (light), 1 hour (full check)

## Scalability Considerations

### Current Limits

- **Single Account**: One Naver Blog account (wncksdid0750)
- **Sequential Posting**: No concurrent posts (Playwright limitation)
- **Daily Limit**: 12 posts maximum (Naver ToS safety)
- **API Quotas**:
  - Claude Haiku: ~100K tokens/day (~50 posts)
  - Perplexity: 50 requests/day
  - Gemini Image: Unlimited (pay-per-use)

### Multi-Account Scaling

To support multiple accounts:

1. **Session Management**: One encrypted session per account
2. **Account Rotation**: Round-robin posting
3. **Separate Scheduling**: Independent cron jobs per account
4. **Resource Allocation**: 1GB RAM per concurrent poster

Example:
```python
accounts = ["account1", "account2", "account3"]
for account in accounts:
    poster = NaverBlogPoster(username=account)
    await poster.post(title, content)
    await asyncio.sleep(600)  # 10 min cooldown
```

### Horizontal Scaling (Future)

- **Distributed Queue**: Celery + Redis for task distribution
- **Multiple Workers**: One Docker container per account
- **Centralized DB**: PostgreSQL instead of SQLite
- **Load Balancer**: Distribute API requests across keys

## Maintenance Tasks

### Daily

- Check Telegram for error alerts
- Verify posts published correctly
- Monitor disk space and memory

### Weekly

- Review logs for new error patterns
- Check API usage and costs
- Verify session still valid (7-day expiry)

### Monthly

- Update Python dependencies
- Review and archive old logs/images
- Audit API key security
- Test disaster recovery (session restore)

### Quarterly

- Review and update AI model prompts
- Optimize image generation costs
- Performance benchmarking
- Security audit

---

**End of Architecture Reference**
