#!/usr/bin/env python3
"""
Simple Blog Posting Example
Minimal code to post a single blog entry
"""

import asyncio
from auto_post import NaverBlogPoster

async def simple_post_example():
    """Post a simple blog entry"""

    # Initialize poster
    poster = NaverBlogPoster(
        username="wncksdid0750",
        headless=True  # Set False for local testing
    )

    title = "비트코인 시장 분석 - 2025년 12월"
    content = """
## 비트코인 최근 동향

최근 비트코인 시장은 강세를 보이고 있습니다.

### 주요 포인트
- 기관 투자 증가
- ETF 승인 기대감
- 글로벌 경제 불확실성

**투자 시 주의사항**: 항상 분산 투자를 하세요.

📱 실시간 코인 분석방: [KakaoTalk 링크]
    """

    try:
        # Start browser and load session
        await poster.start_browser()

        # Verify logged in
        await poster.check_login_status()

        # Navigate to write page
        await poster.navigate_to_write_page()

        # Input content
        await poster.input_title(title)
        await poster.input_content(content)

        # Publish
        await poster.publish_post()

        print("✅ Post published successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await poster.close_browser()


if __name__ == "__main__":
    asyncio.run(simple_post_example())
