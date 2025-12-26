"""
완벽한 포스팅 테스트 스크립트
- 취소선 해제 검증
- 이미지 첨부
- 전체 발행 프로세스
"""

import asyncio
from auto_post import NaverBlogPoster
from loguru import logger
from pathlib import Path
from datetime import datetime


async def test_complete_post():
    """이미지 포함 완벽한 포스팅 테스트"""

    # 설정
    naver_id = "wncksdid0750"

    # 테스트용 제목과 본문
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"[자동화 테스트] 취소선 해제 + 이미지 첨부 테스트 ({timestamp})"

    content = """안녕하세요! 자동화 테스트 포스팅입니다.

이 글은 다음 기능들을 테스트합니다:

1. 취소선 서식이 자동으로 해제되는지 확인
2. 이미지가 정상적으로 첨부되는지 확인
3. 본문이 정상적인 텍스트로 표시되는지 확인

위 텍스트가 취소선 없이 정상적으로 보이면 테스트 성공입니다!

Python + Playwright 자동화 테스트
테스트 시간: """ + timestamp

    # 이미지 경로 확인
    image_dir = Path("/Users/mr.joo/Desktop/네이버블로그봇/generated_images")
    images = list(image_dir.glob("*.png"))

    image_path = None
    if images:
        # 가장 최근 이미지 사용
        image_path = str(sorted(images, key=lambda x: x.stat().st_mtime, reverse=True)[0])
        logger.info(f"테스트 이미지: {image_path}")
    else:
        logger.warning("이미지 없음 - 텍스트만 테스트")

    # 포스팅 실행
    logger.info("=" * 60)
    logger.info("완벽한 포스팅 테스트 시작")
    logger.info("=" * 60)
    logger.info(f"계정: {naver_id}")
    logger.info(f"제목: {title}")
    logger.info(f"이미지: {image_path or '없음'}")
    logger.info("")

    poster = NaverBlogPoster(naver_id)
    result = await poster.post(title, content, image_path)

    # 결과 출력
    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ 포스팅 테스트 성공!")
        print(f"📝 URL: {result['url']}")
        print("\n확인사항:")
        print("  1. 본문에 취소선이 없는지 확인")
        print("  2. 이미지가 정상적으로 표시되는지 확인")
        print("  3. 텍스트가 정상적으로 표시되는지 확인")
    else:
        print("❌ 포스팅 테스트 실패!")
        print(f"에러: {result['error']}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(test_complete_post())
