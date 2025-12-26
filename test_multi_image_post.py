"""
다중 이미지 포스팅 테스트 스크립트
- 이미지 4개 생성
- 본문 중간중간에 이미지 삽입
- 발행까지 테스트
"""

import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from auto_post import NaverBlogPoster
from utils.gemini_image import GeminiImageGenerator


async def test_multi_image_post():
    """다중 이미지 포스팅 테스트"""

    naver_id = "wncksdid0750"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    title = f"[다중 이미지 테스트] 본문 중간 이미지 삽입 테스트 ({timestamp})"

    # 여러 문단으로 구성된 본문
    content = """안녕하세요! 오늘은 다중 이미지 삽입 테스트를 진행합니다.

## 첫 번째 섹션
이 섹션은 첫 번째 내용입니다. 여기에는 다양한 정보가 담겨 있습니다.
테스트 문단의 길이를 조금 늘려보겠습니다.

## 두 번째 섹션
두 번째 섹션에서는 또 다른 중요한 내용을 다룹니다.
이미지가 이 문단 뒤에 삽입될 수 있습니다.

## 세 번째 섹션
세 번째 섹션입니다. 여기까지 오셨군요!
계속해서 내용을 추가해봅니다.

## 네 번째 섹션
네 번째 섹션에서는 핵심 포인트를 다룹니다.
중요한 정보를 전달하는 부분입니다.

## 다섯 번째 섹션
다섯 번째 섹션은 추가 설명을 담고 있습니다.
이미지와 함께 더 풍부한 콘텐츠가 됩니다.

## 마무리
테스트 포스팅이 완료되었습니다.
Python + Playwright 자동화 테스트입니다.

테스트 시간: """ + timestamp

    # 이미지 생성
    logger.info("=" * 60)
    logger.info("다중 이미지 포스팅 테스트 시작")
    logger.info("=" * 60)

    logger.info("1️⃣ 이미지 4개 생성 중...")

    image_generator = GeminiImageGenerator()
    images = []

    prompts = [
        "Professional cryptocurrency trading concept, digital finance visualization, blue gradient, modern design, no text",
        "Investment success and wealth growth, golden coins with upward arrows, professional financial art, no text",
        "AI technology and automation concept, futuristic digital art, circuit patterns, blue and purple colors, no text",
        "Data analysis dashboard, financial charts and graphs, modern fintech design, clean interface, no text"
    ]

    for i, prompt in enumerate(prompts):
        try:
            timestamp_img = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_multi_{timestamp_img}_{i+1}.png"
            path = image_generator.generate_image(
                prompt=prompt,
                filename=filename,
                style="digital-art"
            )
            if path:
                images.append(path)
                logger.success(f"   이미지 {i+1}/4 생성 완료: {path}")
            else:
                logger.warning(f"   이미지 {i+1}/4 생성 실패")
        except Exception as e:
            logger.error(f"   이미지 {i+1}/4 생성 오류: {e}")

    logger.info(f"   총 {len(images)}개 이미지 생성됨")

    if not images:
        logger.error("이미지 생성 실패, 테스트 중단")
        return

    # 포스팅 실행
    logger.info("")
    logger.info("2️⃣ 포스팅 시작...")
    logger.info(f"   계정: {naver_id}")
    logger.info(f"   제목: {title}")
    logger.info(f"   이미지: {len(images)}개")
    logger.info("")

    poster = NaverBlogPoster(naver_id)
    result = await poster.post(title, content, images=images)

    # 결과 출력
    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ 다중 이미지 포스팅 테스트 성공!")
        print(f"📝 URL: {result['url']}")
        print(f"📷 삽입된 이미지: {len(images)}개")
        print("\n확인사항:")
        print("  1. 본문 중간에 이미지 4개가 균등하게 배치되었는지 확인")
        print("  2. 취소선 없이 정상적으로 표시되는지 확인")
        print("  3. 각 이미지가 올바르게 표시되는지 확인")
    else:
        print("❌ 다중 이미지 포스팅 테스트 실패!")
        print(f"에러: {result['error']}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(test_multi_image_post())
