#!/usr/bin/env python3
"""
Full Pipeline Example
Research → Generate → Illustrate → Publish
"""

import asyncio
import os
from pathlib import Path

# Set headless mode
os.environ["HEADLESS"] = "True"

from agents.research_agent import PerplexityResearchAgent
from agents.content_agent import ClaudeContentAgent
from utils.gemini_image import GeminiImageGenerator
from auto_post import NaverBlogPoster


async def full_pipeline_example():
    """Complete workflow from research to publish"""

    print("=" * 60)
    print("NAVER BLOG AUTOMATION - FULL PIPELINE")
    print("=" * 60)

    # ====================
    # STEP 1: RESEARCH
    # ====================
    print("\n🔍 STEP 1: Researching topic...")

    research_agent = PerplexityResearchAgent()
    research_data = await research_agent.research_topic(
        topic="Bitcoin December 2025 market trends",
        focus="price analysis, institutional adoption, regulatory updates"
    )

    print(f"✅ Research complete: {len(research_data['key_points'])} key points")

    # ====================
    # STEP 2: GENERATE CONTENT
    # ====================
    print("\n✍️  STEP 2: Generating blog post...")

    content_agent = ClaudeContentAgent(model="haiku")
    blog_post = await content_agent.generate_blog_post(
        research_data=research_data,
        style="market_analysis",
        target_length=1500
    )

    print(f"✅ Content generated: {blog_post['title']}")

    # ====================
    # STEP 3: GENERATE IMAGES
    # ====================
    print("\n🎨 STEP 3: Generating crypto meme images...")

    image_generator = GeminiImageGenerator()
    images = []

    moods = ["bullish", "neutral", "bearish", "bullish"]
    for idx, mood in enumerate(moods):
        print(f"  Generating image {idx + 1}/4 ({mood})...")
        image_path = image_generator.generate_crypto_thumbnail(
            topic=blog_post['title'],
            mood=mood
        )
        if image_path:
            images.append(image_path)
            print(f"  ✅ {Path(image_path).name}")

    print(f"✅ Generated {len(images)} images")

    # ====================
    # STEP 4: PUBLISH
    # ====================
    print("\n📤 STEP 4: Publishing to Naver Blog...")

    poster = NaverBlogPoster(
        username="wncksdid0750",
        headless=True
    )

    try:
        await poster.start_browser()
        await poster.check_login_status()
        await poster.navigate_to_write_page()
        await poster.input_title(blog_post['title'])

        # Insert content with images
        # Split content into paragraphs
        paragraphs = blog_post['body'].split('\n\n')
        content_with_images = ""

        for idx, para in enumerate(paragraphs):
            content_with_images += para + "\n\n"

            # Insert image every 3 paragraphs
            if (idx + 1) % 3 == 0 and images:
                img_idx = min(idx // 3, len(images) - 1)
                # Note: Image insertion handled separately in actual implementation
                # This is a simplified example

        await poster.input_content(content_with_images)

        # Upload images (simplified)
        for img_path in images:
            try:
                await poster.insert_image(img_path)
            except Exception as e:
                print(f"  ⚠️  Image upload failed: {e}")

        # Publish
        await poster.publish_post()

        print("✅ Post published successfully!")

    except Exception as e:
        print(f"❌ Publishing failed: {e}")
        raise
    finally:
        await poster.close_browser()

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(full_pipeline_example())
