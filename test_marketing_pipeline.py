"""
마케팅 콘텐츠 파이프라인 테스트 v2
- 콘텐츠 생성 (1500~2500자) → 이미지 생성 → 블로그 발행
"""

import asyncio
from pathlib import Path
from loguru import logger

from agents.marketing_content import MarketingContentGenerator
from utils.gemini_image import GeminiImageGenerator
from auto_post import NaverBlogPoster


async def test_full_pipeline(
    template_type: str = None,
    keyword: str = None,
    naver_id: str = "wncksdid0750",
    skip_image: bool = False,
    dry_run: bool = False
):
    """
    전체 마케팅 파이프라인 테스트

    Args:
        template_type: 템플릿 유형
            - "trading_mistake": 매매 실수/함정 (거래량 매매, 추격 매수 등)
            - "market_analysis": 시장 분석 (비트코인, 나스닥 등)
            - "investment_tip": 투자 팁 (손절, 분할매수 등)
            - "psychology": 투자 심리 (FOMO, 멘탈 등)
        keyword: 주제 키워드 (없으면 템플릿 내에서 랜덤)
        naver_id: 네이버 계정 ID
        skip_image: 이미지 생성 건너뛰기
        dry_run: True면 발행하지 않고 콘텐츠만 생성
    """

    print("\n" + "=" * 60)
    print("🚀 마케팅 콘텐츠 파이프라인 v2 시작")
    print("=" * 60)

    # 1. 콘텐츠 생성
    logger.info("1단계: 콘텐츠 생성 (1500~2500자)")
    content_generator = MarketingContentGenerator()

    if template_type:
        logger.info(f"템플릿: {template_type}")
    else:
        logger.info("템플릿: 랜덤 선택")

    if keyword:
        logger.info(f"키워드: {keyword}")

    content = content_generator.generate_content(
        template_type=template_type,
        keyword=keyword,
        min_length=1500,
        max_length=2500,
        model="sonnet"  # 긴 글은 sonnet 권장
    )

    print(f"\n📝 생성된 콘텐츠:")
    print(f"   제목: {content['title']}")
    print(f"   템플릿: {content['template']}")
    print(f"   키워드: {content['keyword']}")
    print(f"   글자 수: {len(content['content'])}자")
    print(f"   태그: {', '.join(content['tags'][:5])}...")
    print(f"\n   본문 미리보기:\n   {content['content'][:300]}...")

    # 2. 이미지 생성 (선택)
    image_path = None
    if not skip_image:
        logger.info("\n2단계: 이미지 생성")
        try:
            image_generator = GeminiImageGenerator()

            # 템플릿에 맞는 이미지 프롬프트
            template_prompts = {
                "trading_mistake": "Stock market warning concept, red alert signs, falling chart with caution symbols, professional financial illustration",
                "market_analysis": "Professional market analysis dashboard, financial charts and graphs, blue and green tones, modern fintech design",
                "investment_tip": "Investment success concept, golden coins stacking up, green upward arrows, wealth management illustration",
                "psychology": "Mental clarity and focus concept, brain with trading charts, calm blue colors, mindfulness in trading"
            }

            image_prompt = template_prompts.get(
                content['template'],
                "Professional investment and trading concept, modern financial illustration"
            )

            # generate_image는 동기 함수
            generated_path = image_generator.generate_image(
                prompt=image_prompt,
                style="digital-art"
            )

            if generated_path:
                image_path = generated_path
                logger.success(f"이미지 생성 완료: {image_path}")
            else:
                logger.warning("이미지 생성 실패")

        except Exception as e:
            logger.warning(f"이미지 생성 스킵: {e}")

    # 기존 이미지 사용 (이미지 생성 실패 또는 스킵 시)
    if not image_path:
        image_dir = Path("/Users/mr.joo/Desktop/네이버블로그봇/generated_images")
        existing_images = list(image_dir.glob("*.png"))
        if existing_images:
            image_path = str(sorted(existing_images, key=lambda x: x.stat().st_mtime, reverse=True)[0])
            logger.info(f"기존 이미지 사용: {image_path}")

    # 3. 블로그 발행
    if dry_run:
        logger.info("\n3단계: DRY RUN 모드 - 발행 스킵")
        print("\n" + "=" * 60)
        print("✅ DRY RUN 완료 - 콘텐츠 확인")
        print("=" * 60)
        print(f"\n제목: {content['title']}")
        print(f"템플릿: {content['template']}")
        print(f"키워드: {content['keyword']}")
        print(f"글자 수: {len(content['content'])}자")
        print(f"태그: {', '.join(content['tags'])}")
        print(f"이미지: {image_path or '없음'}")
        print(f"\n{'─' * 60}")
        print(content['content'])
        print(f"{'─' * 60}")
        return {
            "success": True,
            "dry_run": True,
            "content": content,
            "image_path": image_path
        }

    logger.info("\n3단계: 네이버 블로그 발행")
    poster = NaverBlogPoster(naver_id)

    result = await poster.post(
        title=content['title'],
        content=content['content'],
        image_path=image_path
    )

    # 결과 출력
    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ 마케팅 콘텐츠 발행 성공!")
        print(f"📝 제목: {content['title']}")
        print(f"🏷️ 템플릿: {content['template']}")
        print(f"🔑 키워드: {content['keyword']}")
        print(f"📊 글자 수: {len(content['content'])}자")
        print(f"🖼️ 이미지: {'포함' if image_path else '없음'}")
        print(f"🔗 URL: {result['url']}")
    else:
        print("❌ 발행 실패!")
        print(f"에러: {result['error']}")
    print("=" * 60)

    return {
        "success": result["success"],
        "content": content,
        "image_path": image_path,
        "url": result.get("url"),
        "error": result.get("error")
    }


async def test_content_only():
    """콘텐츠 생성만 테스트 (발행 안 함)"""

    print("\n" + "=" * 60)
    print("📝 콘텐츠 생성 테스트 (모든 템플릿)")
    print("=" * 60)

    generator = MarketingContentGenerator()

    for template_type in generator.get_available_templates():
        keywords = generator.get_keywords_for_template(template_type)
        keyword = keywords[0] if keywords else None

        print(f"\n--- {template_type} ---")
        content = generator.generate_content(
            template_type=template_type,
            keyword=keyword,
            model="sonnet"
        )

        print(f"제목: {content['title']}")
        print(f"키워드: {content['keyword']}")
        print(f"글자 수: {len(content['content'])}자")
        print(f"태그: {', '.join(content['tags'][:3])}...")

        # 분량 체크
        if len(content['content']) < 1500:
            print(f"⚠️ 경고: 1500자 미만!")
        elif len(content['content']) > 2500:
            print(f"⚠️ 경고: 2500자 초과!")
        else:
            print(f"✅ 글자 수 OK")


def show_help():
    """도움말 표시"""
    print("""
마케팅 콘텐츠 파이프라인 v2

사용법:
  python test_marketing_pipeline.py [옵션] [템플릿] [키워드]

템플릿 유형:
  trading_mistake  - 매매 실수/함정 (거래량 매매, 추격 매수, 물타기 등)
  market_analysis  - 시장 분석/전망 (비트코인, 이더리움, 나스닥 등)
  investment_tip   - 투자 팁/노하우 (손절, 분할매수, 차트분석 등)
  psychology       - 투자 심리/멘탈 (FOMO, 손실회피, 확증편향 등)

옵션:
  --dry           발행 없이 콘텐츠 미리보기
  --content       모든 템플릿 콘텐츠 테스트
  --help          도움말 표시

예시:
  python test_marketing_pipeline.py                           # 랜덤 템플릿/키워드로 전체 실행
  python test_marketing_pipeline.py trading_mistake           # 매매실수 템플릿으로 실행
  python test_marketing_pipeline.py trading_mistake 거래량    # 거래량 매매 주제로 실행
  python test_marketing_pipeline.py --dry psychology FOMO     # FOMO 주제 미리보기
  python test_marketing_pipeline.py --content                 # 모든 템플릿 테스트
""")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if not args:
        # 기본: 랜덤 템플릿/키워드로 전체 실행
        asyncio.run(test_full_pipeline())

    elif args[0] == "--help":
        show_help()

    elif args[0] == "--content":
        asyncio.run(test_content_only())

    elif args[0] == "--dry":
        # 발행 없이 테스트
        template_type = args[1] if len(args) > 1 else None
        keyword = args[2] if len(args) > 2 else None
        asyncio.run(test_full_pipeline(
            template_type=template_type,
            keyword=keyword,
            dry_run=True
        ))

    elif args[0] in ["trading_mistake", "market_analysis", "investment_tip", "psychology"]:
        # 특정 템플릿으로 실행
        template_type = args[0]
        keyword = args[1] if len(args) > 1 else None
        asyncio.run(test_full_pipeline(
            template_type=template_type,
            keyword=keyword
        ))

    else:
        print(f"알 수 없는 옵션: {args[0]}")
        show_help()
