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
- **v1.1.0** (2025-12-29): Linux image insertion fix, human simulation enhancement

---

## Change Log - 2025-12-29 오후 작업 인수인계 (최종 업데이트)

### 🎯 핵심 발견: 서버 IP 차단 확인

| 환경 | 발행 결과 | URL |
|------|----------|-----|
| **로컬 PC (macOS)** | ✅ 성공 | `https://blog.naver.com/PostView.naver?logNo=224126004629` |
| **원격 서버 (Vultr)** | ❌ 실패 | "페이지를 찾을 수 없습니다" |

**결론**: 네이버가 데이터센터 IP(Vultr 141.164.55.245)를 차단함. 코드 문제 아님.

### 현재 상태 요약

| 기능 | 상태 | 비고 |
|------|------|------|
| 콘텐츠 생성 (Perplexity + Claude) | ✅ 완료 | 정상 동작 |
| 이미지 생성 (Gemini 3 Pro Preview) | ✅ 완료 | 4개 이미지 생성 성공 |
| 브라우저 세션 로드 | ✅ 완료 | 로그인 상태 유지됨 |
| 제목 입력 | ✅ 완료 | 로컬에서 검증됨 |
| 본문 입력 + 마크다운 서식 | ✅ 완료 | 소제목, 굵게 등 적용 |
| 이미지 삽입 (Linux 호환) | ✅ 완료 | `set_input_files()` 방식 |
| playwright-stealth 적용 | ✅ 완료 | 봇 탐지 우회 활성화 |
| **발행 (로컬 PC)** | ✅ 성공 | 가정용 IP에서 정상 동작 |
| **발행 (서버)** | ❌ 실패 | 데이터센터 IP 차단됨 |

### 오늘 추가된 변경사항 (2025-12-29 06:00 UTC)

#### 1. playwright-stealth 활성화

**문제**: Docker 컨테이너에서 `pkg_resources` 모듈 없어서 임포트 실패

**해결**:
```bash
docker exec naver-blog-bot pip install setuptools
```

**코드 위치**: `auto_post.py:21-28`
```python
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
    logger.info("playwright-stealth 로드됨 - 봇 탐지 우회 활성화")
except ImportError:
    STEALTH_AVAILABLE = False
```

**적용 위치**: `auto_post.py:185-205` (start_browser 내)

#### 2. 로딩 오버레이 대기 로직 추가

**새 메서드**: `_wait_for_loading_complete()` (`auto_post.py:578-637`)

```python
async def _wait_for_loading_complete(self, max_wait: int = 30):
    """로딩 오버레이가 사라질 때까지 대기"""
    loading_selectors = [
        '[class*="dimmed"]',
        '[class*="loading"]',
        '.dimmed__S_MFG',
        '[class*="full_screen"]',
    ]
    # 30초 대기 후 강제 제거 시도
```

**특징**:
- 최대 30초 대기
- 30초 초과 시 JavaScript로 강제 숨김 처리
- `publish_post()` 시작 시 호출
- `_handle_publish_popup()` 시작 시 호출

### 해결된 문제

#### 1. 이미지 삽입 - osascript 문제

**문제**: macOS 전용 `osascript` 명령어가 Linux 서버에서 실행 불가

**해결**: `auto_post.py`에 플랫폼 감지 및 Linux 호환 코드 추가

```python
# auto_post.py:1860-1920
async def insert_image(self, image_path: str):
    """이미지 삽입 - 플랫폼에 따라 방식 선택"""
    is_linux = platform.system() == "Linux"
    is_headless = HEADLESS_MODE

    if is_linux or is_headless:
        return await self._insert_image_via_file_input(abs_path)  # Playwright set_input_files()
    else:
        return await self._insert_image_via_clipboard(abs_path)   # macOS 클립보드
```

**핵심 메서드**: `_insert_image_via_file_input()` (1921-2000줄)

#### 2. google-genai 패키지 설치

**문제**: Docker 컨테이너에 `google-genai` 패키지 미설치

**해결**:
```bash
docker exec naver-blog-bot pip install google-genai
```

**requirements.txt 업데이트**: `google-genai>=1.0.0`

### 미해결 문제: 발행 실패

#### 증상

발행 버튼 2단계 클릭 후 **"페이지를 찾을 수 없습니다"** 에러 발생

```
요청하신 페이지를 처리하는 도중 예기치 못한 에러가 발생했습니다.
잠시 후 다시 시도해주세요.
```

#### 발행 프로세스

1. **1단계**: 오른쪽 상단 "발행" 버튼 클릭 → 모달창 열림 ✅
2. **2단계**: 모달창 내 "발행" 버튼 클릭 → **에러 발생** ❌

#### 시도한 해결책 (모두 실패)

| 시도 | 결과 | 파일 위치 |
|------|------|-----------|
| 마우스 이동 시뮬레이션 추가 | 실패 | auto_post.py:1778-1793 |
| 대기 시간 대폭 증가 (SAFE_MODE 2배) | 실패 | config/human_timing.py:95-98 |
| 인간적인 스크롤/호버 동작 추가 | 실패 | auto_post.py:1765-1773 |
| `before_publish` 딜레이 추가 (2-4초) | 실패 | config/human_timing.py:46 |

#### 추정 원인

1. **세션 토큰 문제**: 세션은 유효하지만 발행에 필요한 CSRF 토큰이 만료/불일치
2. **Playwright 탐지**: 네이버가 Playwright 브라우저의 핑거프린트 감지
3. **IP 평판 문제**: 서버 IP가 네이버에 의해 제한됨

#### 다음 시도 권장사항

1. **세션 새로 생성** (가장 유력)
   ```bash
   # 로컬에서 수동 로그인하여 새 세션 생성
   python manual_login_clipboard.py
   # 또는
   python session_manager.py --create --id wncksdid0750

   # 서버에 업로드
   scp data/sessions/*.encrypted root@141.164.55.245:/root/naver-blog-bot/data/sessions/
   ```

2. **다른 계정 테스트**: 다른 네이버 계정으로 동일 테스트

3. **IP 변경**: 새 서버 또는 VPN 사용

4. **네이버 API 검토**: 발행 API가 있다면 직접 호출 시도

### 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `auto_post.py` | Linux 이미지 삽입 (`_insert_image_via_file_input`), 인간 시뮬레이션 강화 |
| `config/human_timing.py` | SAFE_MODE=True, SAFE_MODE_MULTIPLIER=2.0, 딜레이 대폭 증가 |
| `requirements.txt` | `google-genai>=1.0.0` 추가 |

### 주요 코드 위치

```
auto_post.py
├── HumanDelay 클래스: 24-100줄
├── insert_image(): 1860-1920줄 (플랫폼 분기)
├── _insert_image_via_file_input(): 1921-2000줄 (Linux용)
├── _insert_image_via_clipboard(): 2001-2100줄 (macOS용)
├── publish_post(): 1277-1540줄 (발행 로직)
└── _handle_publish_popup(): 1641-1840줄 (★ 문제 발생 지점)
```

### ~~서버 정보~~ (사용 중단 - IP 차단됨)

```
⚠️ 아래 서버는 네이버에 의해 IP 차단되어 발행 불가

호스트: 141.164.55.245 (Vultr Seoul) - 차단됨
SSH: root / [Br76r(6mMDr%?ia
상태: Docker 컨테이너 실행 중이나 발행 시 "페이지를 찾을 수 없습니다" 에러

# 서버는 유지되어 있으나 발행 기능 사용 불가
# 콘텐츠 생성, 이미지 생성은 정상 동작
# 발행만 차단됨
```

### 🖥️ 권장 배포 환경: 윈도우 PC (가정용 IP)

**이유**: 네이버가 데이터센터 IP를 차단하므로 가정용 IP 필요

```text
권장 환경:
- Windows 10/11 PC (24시간 가동 가능한 PC)
- Python 3.10+
- 가정용 인터넷 (KT, SKT, LG U+ 등)

필요 작업:
1. Python 환경 설정
2. 프로젝트 파일 복사
3. 세션 파일 복사
4. Windows 작업 스케줄러 설정 (24시간 자동 실행)
```

### 로컬 테스트 명령어 (현재 사용)

```bash
# 로컬 발행 테스트 (macOS/Windows)
cd /Users/mr.joo/Desktop/네이버블로그봇
python test_local_publish.py

# 수동 로그인으로 세션 생성
python manual_login_clipboard.py wncksdid0750

# 스케줄러 실행 (로컬)
python -m scheduler.auto_scheduler --naver-id wncksdid0750
```

### 스크린샷 증거

서버 `/app/logs/` 디렉토리:

| 파일 | 설명 |
|------|------|
| `publish_popup_before.png` | 발행 모달창 (정상 열림) |
| `publish_popup_after_click.png` | 발행 버튼 클릭 후 (에러 화면) |
| `publish_failed.png` | 최종 실패 시점 |

### 주의사항

1. **코드 중복 방지**: `_insert_image_via_file_input()`과 `_insert_image_via_clipboard()`는 각각 Linux/macOS용이므로 둘 다 유지 필요

2. **SAFE_MODE 설정**: 현재 `True`로 설정됨 - 모든 딜레이 2배 적용 중. 테스트 시 시간이 오래 걸릴 수 있음

3. **세션 파일**: 암호화되어 있음 (`*.session.encrypted`). 복호화에는 `/app/secrets/encryption.key` 필요

4. **발행 버튼 셀렉터**: 네이버 에디터 업데이트 시 변경될 수 있음
   ```python
   # 1단계 버튼
   'button[class*="publish_btn"]'
   # 2단계 버튼 (모달 내)
   'button[class*="confirm_btn"]'
   ```

### 결론 (2025-12-29 최종)

**✅ 완료된 작업**:

- 전체 파이프라인 (리서치 → 콘텐츠 → 이미지 → 입력) 정상 동작
- Linux 서버 호환성 확보 (이미지 삽입)
- 인간 시뮬레이션 강화
- playwright-stealth 적용 (봇 탐지 우회)
- 로딩 오버레이 대기 및 강제 제거 로직 추가
- **로컬 PC에서 발행 성공 확인** (2025-12-29 15:32 KST)
- VNC 서버 설정 완료 (141.164.55.245:5900)

**🔍 확인된 원인**:

- **서버 IP 차단**: 네이버가 데이터센터 IP(Vultr)를 차단
- 로컬 PC(가정용 IP)에서는 동일 코드로 발행 성공
- 서버에서는 "페이지를 찾을 수 없습니다" 에러 발생
- GUI/헤드리스 모드, 새 세션 모두 무관 → **IP 문제 확정**

**🎯 해결 방향**:

1. **윈도우 PC 24시간 가동** (권장) - 가정용 IP 사용, 무료
2. **Residential Proxy** - 월 $10-30, 서버 유지 가능
3. **클라우드 서버 변경** - AWS/GCP/Azure도 데이터센터 IP라 같은 문제 예상

### 빠른 테스트 가이드 (다음 작업자용)

서버에 테스트 스크립트가 준비되어 있습니다:

```bash
# 1. 서버 접속
sshpass -p '[Br76r(6mMDr%?ia' ssh root@141.164.55.245

# 2. 간단한 발행 테스트 실행 (약 5분 소요)
docker exec naver-blog-bot python /app/test_post.py

# 3. 최신 스크린샷 확인
docker cp naver-blog-bot:/app/logs/publish_popup_before.png /tmp/
docker cp naver-blog-bot:/app/logs/publish_failed.png /tmp/

# 4. 로그 확인
docker logs naver-blog-bot --tail 200
```

**테스트 스크립트 위치**: `/app/test_post.py`

```python
# test_post.py 내용
import asyncio
from auto_post import NaverBlogPoster

async def test():
    poster = NaverBlogPoster(naver_id="wncksdid0750")
    result = await poster.post(
        "테스트 제목",
        "<p>테스트 본문입니다.</p>"
    )
    print(f"결과: {result}")

asyncio.run(test())
```

*마지막 업데이트: 2025-12-29 06:40 UTC (15:40 KST)*

---

## 🖥️ Windows PC 배포 가이드 (완전 인수인계)

### 📋 배포 전 필수 확인사항

| 항목 | 요구사항 | 비고 |
|------|----------|------|
| **OS** | Windows 10/11 (64bit) | WSL 불필요 |
| **인터넷** | 가정용 IP 필수 | 데이터센터 IP 차단됨 |
| **24시간 가동** | PC 절전모드 해제 필요 | 또는 Wake-on-LAN |
| **저장공간** | 최소 5GB | Chromium + 로그 |

### 🚫 서버 배포가 불가능한 이유

```
⚠️ 네이버가 데이터센터 IP를 차단합니다!

테스트 결과:
- Vultr 서버 IP: ❌ 차단됨
- AWS/GCP/Azure: ❌ 동일하게 차단 예상
- Bright Data ISP Proxy: ❌ 데이터센터 IP로 인식되어 차단
- Bright Data Residential Proxy: ❌ Playwright와 호환 안됨 (HTTPS 터널링 실패)

유일한 해결책: 가정용 IP를 가진 PC에서 실행
```

---

### 🔧 방법 1: Docker Desktop 사용 (권장)

**장점**: 환경 설정 간단, 의존성 충돌 없음

#### Step 1: Docker Desktop 설치

1. https://www.docker.com/products/docker-desktop/ 접속
2. "Download for Windows" 클릭
3. 설치 후 재부팅
4. Docker Desktop 실행하여 정상 작동 확인

```powershell
# 설치 확인
docker --version
docker-compose --version
```

#### Step 2: 프로젝트 파일 복사

**macOS에서 Windows로 복사할 파일들:**

```
naver-blog-bot/
├── .env                          # ⚠️ 필수: API 키 포함
├── docker-compose.yml            # Docker 설정
├── docker-compose.windows.yml    # Windows 전용 설정 (아래에서 생성)
├── Dockerfile                    # Docker 이미지 설정
├── requirements.txt              # Python 패키지
├── auto_post.py                  # 메인 발행 코드
├── main.py                       # 진입점
├── data/
│   └── sessions/
│       └── wncksdid0750_clipboard.session.encrypted  # ⚠️ 필수: 로그인 세션
├── secrets/
│   └── encryption.key            # ⚠️ 필수: 암호화 키
├── agents/                       # AI 에이전트들
├── utils/                        # 유틸리티
├── security/                     # 보안 모듈
├── scheduler/                    # 스케줄러
└── config/                       # 설정 파일
```

**복사 방법:**
- USB 드라이브 사용
- 클라우드 스토리지 (Google Drive, Dropbox)
- Git 저장소 (민감한 파일 제외)

#### Step 3: Windows용 docker-compose 파일 생성

`docker-compose.windows.yml` 파일을 프로젝트 루트에 생성:

```yaml
version: '3.8'

services:
  naver-blog-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: naver-blog-bot
    restart: unless-stopped

    environment:
      - TZ=Asia/Seoul
      - HEADLESS=True
      - DISPLAY=:99
      # 프록시 비활성화 (가정용 IP 사용)
      - PROXY_ENABLED=False

    volumes:
      # Windows 경로 형식
      - ./data:/app/data
      - ./logs:/app/logs
      - ./secrets:/app/secrets:ro
      - ./.env:/app/.env:ro

    # 헬스체크
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

    # 리소스 제한 (Windows용)
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

#### Step 4: .env 파일 수정

Windows PC에서는 프록시가 필요 없으므로 `.env` 파일 수정:

```env
# .env 파일에서 프록시 비활성화
PROXY_ENABLED=False

# 나머지 설정은 그대로 유지
HEADLESS=True
# ... (API 키들)
```

#### Step 5: Docker 실행

```powershell
# 프로젝트 폴더로 이동
cd C:\naver-blog-bot

# Docker 이미지 빌드 및 실행
docker-compose -f docker-compose.windows.yml up -d --build

# 로그 확인
docker logs -f naver-blog-bot

# 상태 확인
docker ps
```

#### Step 6: 테스트 발행

```powershell
# 테스트 포스트 발행
docker exec naver-blog-bot python -c "
import asyncio
from auto_post import NaverBlogPoster

async def test():
    poster = NaverBlogPoster(naver_id='wncksdid0750')
    result = await poster.post(
        'Windows PC 테스트',
        '<p>Docker에서 실행된 테스트입니다.</p>'
    )
    print(f'결과: {result}')

asyncio.run(test())
"
```

---

### 🔧 방법 2: Python 직접 설치

**장점**: 디버깅 쉬움, 용량 작음

#### Step 1: Python 설치

1. https://www.python.org/downloads/ 접속
2. Python 3.10 이상 다운로드 (3.11 권장)
3. 설치 시 **"Add Python to PATH"** 체크 필수!

```powershell
# 설치 확인
python --version  # Python 3.11.x
pip --version
```

#### Step 2: 프로젝트 설정

```powershell
# 프로젝트 폴더로 이동
cd C:\naver-blog-bot

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

#### Step 3: 환경 변수 설정

`.env` 파일이 제대로 복사되었는지 확인:

```powershell
# .env 파일 확인
type .env | findstr "ANTHROPIC_API_KEY"
```

프록시 비활성화 확인:
```env
PROXY_ENABLED=False
```

#### Step 4: 테스트 실행

```powershell
# 가상환경 활성화 상태에서
python test_local_publish.py
```

#### Step 5: 자동 실행 설정 (Windows 작업 스케줄러)

1. `Win + R` → `taskschd.msc` 입력
2. "작업 만들기" 클릭
3. 설정:
   - **이름**: NaverBlogBot
   - **트리거**: 매일 원하는 시간 (예: 오전 9시, 오후 3시, 오후 9시)
   - **동작**: 프로그램 시작
     - 프로그램: `C:\naver-blog-bot\venv\Scripts\python.exe`
     - 인수: `-m scheduler.auto_scheduler --naver-id wncksdid0750`
     - 시작 위치: `C:\naver-blog-bot`
   - **조건**: "컴퓨터의 AC 전원이 켜져 있는 경우에만" 체크 해제
   - **설정**: "예약된 시작 시간을 놓친 경우 가능한 빨리 작업 실행" 체크

---

### 📁 필수 복사 파일 체크리스트

```
✅ 반드시 복사해야 할 파일들:

1. data/sessions/wncksdid0750_clipboard.session.encrypted
   - 네이버 로그인 세션 (없으면 로그인 필요)

2. secrets/encryption.key
   - 세션 암호화 키 (없으면 세션 복호화 불가)

3. .env
   - API 키들 (ANTHROPIC, GOOGLE, PERPLEXITY)
   - 설정값들

❌ 복사하지 않아도 되는 파일들:

- logs/ (자동 생성됨)
- __pycache__/ (자동 생성됨)
- .git/ (선택사항)
- venv/ (Windows에서 새로 생성)
```

---

### 🔐 새 PC에서 세션 재생성이 필요한 경우

세션 파일을 복사하지 못했거나 만료된 경우:

```powershell
# 수동 로그인으로 새 세션 생성
python manual_login_clipboard.py wncksdid0750

# 브라우저가 열리면:
# 1. 네이버 아이디/비밀번호 입력
# 2. 캡챠 해결
# 3. 2차 인증 완료 (필요시)
# 4. 자동으로 세션 저장됨
```

---

### 🐛 문제 해결 가이드

#### 문제 1: "playwright install" 실패

```powershell
# 관리자 권한으로 PowerShell 실행 후
playwright install chromium --with-deps
```

#### 문제 2: 세션 로드 실패

```
ERROR: 세션 복호화 실패
```

**해결**: `secrets/encryption.key` 파일이 원본과 동일한지 확인

#### 문제 3: API 키 오류

```
ERROR: ANTHROPIC_API_KEY not found
```

**해결**: `.env` 파일이 프로젝트 루트에 있는지 확인

#### 문제 4: 발행 시 "페이지를 찾을 수 없습니다"

```
⚠️ 이 오류가 발생하면 IP 문제입니다!
```

**확인 방법**:
```powershell
# 현재 IP 확인
curl ipinfo.io/ip
```

**해결**:
- VPN 사용 중이면 해제
- 프록시 설정 확인 (PROXY_ENABLED=False)
- 회사/학교 네트워크라면 가정용 네트워크로 변경

#### 문제 5: Docker 메모리 부족

```
ERROR: Container killed (OOM)
```

**해결**: Docker Desktop → Settings → Resources → Memory를 4GB 이상으로 설정

---

### 📊 운영 모니터링

#### Docker 사용 시

```powershell
# 실시간 로그
docker logs -f naver-blog-bot

# 최근 로그 100줄
docker logs --tail 100 naver-blog-bot

# 컨테이너 상태
docker stats naver-blog-bot
```

#### Python 직접 실행 시

```powershell
# 로그 파일 위치
type logs\blog_automation_*.log
```

---

### 📞 긴급 연락처 및 참고 정보

| 항목 | 값 |
|------|-----|
| **macOS 원본 위치** | `/Users/mr.joo/Desktop/네이버블로그봇` |
| **네이버 계정** | `wncksdid0750` |
| **세션 이름** | `wncksdid0750_clipboard` |
| **Telegram 알림** | Bot Token: `8500784416:AAFGOGuF8LUesut6O1ebW6Ir220o2IcxBsI` |
| **Telegram Chat ID** | `7980845952` |

---

### ✅ 배포 완료 체크리스트

```
□ Docker Desktop 또는 Python 설치 완료
□ 프로젝트 파일 복사 완료
□ data/sessions/ 폴더 복사 완료
□ secrets/encryption.key 복사 완료
□ .env 파일 복사 및 PROXY_ENABLED=False 설정
□ 테스트 발행 성공
□ 자동 실행 스케줄러 설정 완료
□ PC 절전모드 해제 완료
```

*마지막 업데이트: 2025-12-29 09:00 UTC (18:00 KST)*
