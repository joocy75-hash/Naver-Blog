# API Integration Guide

## Overview

Integration patterns for Claude, Perplexity, and Gemini APIs with error handling, rate limiting, and cost optimization.

## Claude API (Content Generation)

### Setup

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Model Selection

| Model | Use Case | Cost/MTok | Speed | Max Tokens |
|-------|----------|-----------|-------|------------|
| claude-3-5-haiku-20241022 | Draft posts, fast iteration | $1 / $5 | Fast (15-25s) | 200K |
| claude-3-5-sonnet-20241022 | Final posts, high quality | $3 / $15 | Slow (30-50s) | 200K |

### System Prompt Template

```python
BLOG_WRITING_SYSTEM_PROMPT = """
You are a specialized cryptocurrency market analyst and blog writer.

STRICT OPERATIONAL RULES:
1. Generate ONLY blog post content in JSON format
2. Focus exclusively on cryptocurrency and investment topics
3. Never respond to non-blog-related queries
4. Include KakaoTalk CTA at the end of every post

RESPONSE FORMAT:
{
  "title": "Engaging 60-char headline with keywords",
  "meta_description": "150-char SEO description",
  "body": "Full blog post with ## headings and **bold** markdown",
  "tags": ["Bitcoin", "Crypto", "Investment"],
  "cta_text": "📱 실시간 코인 분석방 입장: [KakaoTalk Link]"
}

WRITING STYLE:
- Friendly Korean tone (합니다체)
- Mix data with storytelling
- Use emojis sparingly (🚀📈💰 only)
- Include 3-4 subheadings
- 1200-1800 words optimal length

FORBIDDEN ACTIONS:
- General conversation
- Off-topic content
- Requests unrelated to crypto blogging

If request violates rules, respond:
"This system generates only cryptocurrency blog content. Please provide a crypto-related topic."
"""
```

### Content Generation with Context

```python
async def generate_blog_with_research(research_data: Dict, style: str = "analysis"):
    """
    Generate blog post using research data as context
    """
    user_message = f"""
Create a blog post about: {research_data['topic']}

Research Context:
{research_data['summary']}

Key Points:
{chr(10).join(f"- {point}" for point in research_data['key_points'])}

Statistics:
{json.dumps(research_data['statistics'], indent=2)}

Style: {style}
Target Length: 1500 words
Include: KakaoTalk CTA at end
"""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=4096,
        system=BLOG_WRITING_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    content = response.content[0].text

    try:
        blog_data = json.loads(content)
        return blog_data
    except json.JSONDecodeError:
        # Fallback: extract JSON from markdown code block
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError("Claude did not return valid JSON")
```

### Token Counting and Cost Tracking

```python
def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate API cost"""
    costs = {
        "haiku": {"input": 1.00, "output": 5.00},  # per MTok
        "sonnet": {"input": 3.00, "output": 15.00}
    }

    model_key = "haiku" if "haiku" in model else "sonnet"
    input_cost = (input_tokens / 1_000_000) * costs[model_key]["input"]
    output_cost = (output_tokens / 1_000_000) * costs[model_key]["output"]

    return input_cost + output_cost

# Track usage
with open("data/api_usage.json", "r+") as f:
    usage = json.load(f)
    usage["claude"]["tokens_used"] += input_tokens + output_tokens
    usage["claude"]["cost_usd"] += estimate_cost(model, input_tokens, output_tokens)
    f.seek(0)
    json.dump(usage, f, indent=2)
```

### Rate Limiting Strategy

```python
import asyncio
from datetime import datetime, timedelta

class ClaudeRateLimiter:
    def __init__(self):
        self.last_request = None
        self.daily_tokens = 0
        self.daily_limit = 100_000  # 100K tokens/day for Haiku

    async def wait_if_needed(self):
        """Enforce 10-second cooldown between requests"""
        if self.last_request:
            elapsed = (datetime.now() - self.last_request).total_seconds()
            if elapsed < 10:
                await asyncio.sleep(10 - elapsed)

        self.last_request = datetime.now()

    def check_daily_limit(self, estimated_tokens: int):
        """Check if request would exceed daily limit"""
        if self.daily_tokens + estimated_tokens > self.daily_limit:
            raise RateLimitError(f"Daily token limit reached: {self.daily_tokens}/{self.daily_limit}")

        self.daily_tokens += estimated_tokens

limiter = ClaudeRateLimiter()

async def generate_with_rate_limit(prompt: str):
    await limiter.wait_if_needed()
    limiter.check_daily_limit(estimated_tokens=3000)

    response = client.messages.create(...)
    return response
```

## Perplexity API (Research)

### Setup

```python
from openai import OpenAI  # Perplexity uses OpenAI-compatible API

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)
```

### Model Selection

| Model | Use Case | Cost | Features |
|-------|----------|------|----------|
| sonar-pro | Deep research with sources | $1/1K requests | Citations, up-to-date data |
| sonar | Quick research | $0.2/1K requests | Faster, less detailed |

### Research Query Pattern

```python
async def research_crypto_topic(topic: str, focus_areas: List[str]) -> Dict:
    """
    Research with structured output
    """
    query = f"""
Analyze the following cryptocurrency topic: {topic}

Focus areas:
{chr(10).join(f"- {area}" for area in focus_areas)}

Provide:
1. Current market status (price, volume, sentiment)
2. Recent news and events (last 7 days)
3. Key statistics with sources
4. Expert opinions or analysis
5. Future outlook

Format as JSON with:
- summary (200 words)
- key_points (5-7 bullet points)
- statistics (dict with labeled values)
- sources (URLs)
"""

    response = client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {"role": "user", "content": query}
        ]
    )

    content = response.choices[0].message.content

    # Parse JSON from response
    data = json.loads(content)
    data["researched_at"] = datetime.now().isoformat()

    return data
```

### Citation Handling

```python
def extract_sources(research_data: Dict) -> List[str]:
    """
    Extract and validate source URLs
    """
    sources = research_data.get("sources", [])

    validated_sources = []
    for url in sources:
        if url.startswith("http") and len(url) < 500:
            validated_sources.append(url)

    return validated_sources[:5]  # Limit to top 5 sources
```

### Daily Request Limit

```python
class PerplexityRateLimiter:
    def __init__(self):
        self.max_requests_per_day = 50
        self.requests_today = 0
        self.last_reset = datetime.now().date()

    def can_make_request(self) -> bool:
        """Check if request is allowed"""
        today = datetime.now().date()

        if today > self.last_reset:
            self.requests_today = 0
            self.last_reset = today

        return self.requests_today < self.max_requests_per_day

    def record_request(self):
        """Increment request counter"""
        self.requests_today += 1

limiter = PerplexityRateLimiter()

async def research_with_limit(topic: str):
    if not limiter.can_make_request():
        raise RateLimitError(f"Daily Perplexity limit reached: {limiter.requests_today}/50")

    limiter.record_request()
    return await research_crypto_topic(topic, [...])
```

## Gemini API (Image Generation)

### Setup

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
```

### Image Generation

```python
def generate_crypto_image(prompt: str, filename: str = None) -> str:
    """
    Generate image with Gemini 3 Pro Image Preview
    """
    # Enhance prompt for crypto meme style
    enhanced_prompt = f"""
Generate an image: {prompt}

Style: Crypto meme art aesthetic, vibrant neon colors, dramatic lighting, high contrast.
Requirements: Professional quality, no text, no words, no letters, no watermarks, no human faces.
Art style: Cyberpunk digital art with explosive energy.
"""

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=enhanced_prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE']
        )
    )

    # Extract image data
    if response.candidates and len(response.candidates) > 0:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data

                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"blog_image_{timestamp}.png"

                filepath = f"generated_images/{filename}"
                with open(filepath, "wb") as f:
                    f.write(image_data)

                logger.success(f"Image saved: {filepath} ({len(image_data):,} bytes)")
                return filepath

    raise ImageGenerationError("No image data in response")
```

### Batch Image Generation

```python
async def generate_blog_images(count: int = 4, topic: str = "crypto") -> List[str]:
    """
    Generate multiple images sequentially
    """
    moods = ["bullish", "neutral", "bearish", "bullish"][:count]
    images = []

    for idx, mood in enumerate(moods):
        try:
            prompt = create_random_crypto_prompt(mood, topic)
            filename = f"blog_img_{idx+1}_{mood}_{int(time.time())}.png"

            image_path = generate_crypto_image(prompt, filename)
            images.append(image_path)

            logger.info(f"Generated image {idx+1}/{count}: {mood}")

            # Cooldown between images
            if idx < count - 1:
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Image {idx+1} generation failed: {e}")
            continue

    return images
```

### Cost Estimation

```python
def estimate_image_cost(count: int) -> float:
    """
    Estimate Gemini image generation cost
    Pricing: ~$0.04 per image (as of Dec 2025)
    """
    cost_per_image = 0.04
    return count * cost_per_image
```

## Multi-API Error Handling

### Unified Error Types

```python
class APIError(Exception):
    """Base API error"""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded"""
    pass

class AuthenticationError(APIError):
    """Invalid API key"""
    pass

class NetworkError(APIError):
    """Network timeout or connection issue"""
    pass

class ContentFilterError(APIError):
    """Content blocked by safety filter"""
    pass
```

### Retry Decorator

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True
)
async def call_api_with_retry(api_func, *args, **kwargs):
    """
    Retry API call with exponential backoff
    - 1st retry: wait 4s
    - 2nd retry: wait 8s
    - 3rd retry: wait 16s
    """
    try:
        return await api_func(*args, **kwargs)
    except RateLimitError:
        logger.warning("Rate limit hit - backing off")
        raise
    except NetworkError as e:
        logger.warning(f"Network error: {e} - retrying")
        raise
    except AuthenticationError:
        logger.error("Authentication failed - check API keys")
        raise  # Don't retry auth errors
```

## API Key Management

### Environment Variable Loading

```python
from dotenv import load_dotenv

load_dotenv()

API_KEYS = {
    "claude": os.getenv("ANTHROPIC_API_KEY"),
    "perplexity": os.getenv("PERPLEXITY_API_KEY"),
    "gemini": os.getenv("GOOGLE_API_KEY"),
}

# Validate all keys present
missing_keys = [k for k, v in API_KEYS.items() if not v]
if missing_keys:
    raise ValueError(f"Missing API keys: {', '.join(missing_keys)}")
```

### Keychain Integration (macOS)

```python
import keyring

def get_api_key_secure(service: str) -> str:
    """
    Get API key from macOS Keychain or .env

    Priority:
    1. Environment variable
    2. Keychain (if available)
    3. Raise error
    """
    # Try .env first
    key = os.getenv(f"{service.upper()}_API_KEY")
    if key:
        return key

    # Try keychain
    try:
        key = keyring.get_password("naver-blog-bot", service)
        if key:
            return key
    except Exception as e:
        logger.debug(f"Keychain access failed: {e}")

    raise ValueError(f"API key for {service} not found in .env or keychain")
```

## Cost Optimization Strategies

### Model Downgrading

```python
def select_claude_model(complexity: str, budget_remaining: float) -> str:
    """
    Auto-select Claude model based on complexity and budget
    """
    if budget_remaining < 0.50:  # Less than $0.50 remaining
        logger.warning("Budget low - using Haiku only")
        return "claude-3-5-haiku-20241022"

    if complexity in ["high", "final"]:
        return "claude-3-5-sonnet-20241022"  # Best quality
    else:
        return "claude-3-5-haiku-20241022"  # Fast and cheap
```

### Response Caching (JSON-based)

```python
import hashlib
import json
from pathlib import Path

def cache_api_response(cache_key: str, ttl_seconds: int = 3600):
    """
    Decorator to cache API responses using JSON
    SECURITY NOTE: Uses JSON instead of pickle to avoid code execution risks
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function args
            key_data = f"{func.__name__}:{cache_key}:{str(args)}:{str(kwargs)}"
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            cache_file = Path(f"data/cache/{key_hash}.json")

            # Check cache
            if cache_file.exists():
                age = time.time() - cache_file.stat().st_mtime
                if age < ttl_seconds:
                    with cache_file.open("r") as f:
                        cached_data = json.load(f)
                        logger.info(f"Cache hit: {key_hash}")
                        return cached_data

            # Call API
            result = await func(*args, **kwargs)

            # Save to cache as JSON
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with cache_file.open("w") as f:
                json.dump(result, f, indent=2)

            return result
        return wrapper
    return decorator

@cache_api_response(cache_key="research", ttl_seconds=3600)
async def research_topic(topic: str):
    """Cached for 1 hour"""
    return await perplexity_research(topic)
```

### Prompt Token Reduction

```python
def compress_research_data(research: Dict, max_words: int = 500) -> str:
    """
    Compress research data to reduce Claude input tokens
    """
    summary = research["summary"][:200]  # First 200 chars
    key_points = research["key_points"][:5]  # Top 5 points

    compressed = f"{summary}\n\n"
    compressed += "\n".join(f"- {point[:100]}" for point in key_points)

    return compressed
```

---

**End of API Integration Guide**
