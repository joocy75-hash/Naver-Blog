"""
포스팅 + 텔레그램 알림 통합 테스트
- 마크다운 서식 (##소제목, **굵게**, >인용구)
- 취소선 해제 검증
- 이미지 첨부
- 텔레그램 알림 발송
"""

import asyncio
from auto_post import NaverBlogPoster
from utils.telegram_notifier import TelegramNotifier
from loguru import logger
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


async def test_post_with_telegram():
    """포스팅 + 텔레그램 알림 통합 테스트 (마크다운 서식 포함)"""

    # 설정
    naver_id = "wncksdid0750"

    # 테스트용 제목과 본문 (마크다운 서식 포함)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"[자동화 테스트] 마크다운 서식 + 이미지 ({timestamp})"

    # 마크다운 서식 테스트 본문
    content = f"""안녕하세요! 자동화 테스트 포스팅입니다.

## 테스트 항목

이 글은 다음 기능들을 테스트합니다:

1. **마크다운 서식** 자동 변환
2. 취소선 서식 자동 해제
3. 이미지 정상 첨부
4. 텔레그램 알림 발송

## 서식 테스트

**굵은 글씨**가 정상적으로 표시되는지 확인합니다.

> 이것은 인용구 테스트입니다. 인용구 스타일이 적용되어야 합니다.

### 소제목 테스트

위의 **소제목**과 **굵은 글씨**, **인용구**가 모두 정상적으로 보이면 테스트 성공입니다!

테스트 시간: {timestamp}"""

    # 이미지 경로 확인
    image_dir = Path("/Users/mr.joo/Desktop/네이버블로그봇/generated_images")
    images = list(image_dir.glob("*.png"))

    image_path = None
    if images:
        image_path = str(sorted(images, key=lambda x: x.stat().st_mtime, reverse=True)[0])
        logger.info(f"테스트 이미지: {image_path}")
    else:
        logger.warning("이미지 없음 - 텍스트만 테스트")

    # 텔레그램 노티파이어 초기화
    notifier = TelegramNotifier()

    # 시작 알림
    print("\n" + "=" * 60)
    print("포스팅 + 텔레그램 통합 테스트 시작")
    print("=" * 60)
    logger.info(f"계정: {naver_id}")
    logger.info(f"제목: {title}")
    logger.info(f"이미지: {image_path or '없음'}")
    logger.info(f"텔레그램: {'설정됨' if notifier.bot else '미설정'}")
    print("")

    # 포스팅 실행
    poster = NaverBlogPoster(naver_id)
    result = await poster.post(title, content, image_path)

    # 결과 처리 및 텔레그램 알림
    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ 포스팅 테스트 성공!")
        print(f"📝 URL: {result['url']}")

        # 텔레그램 성공 알림
        if notifier.bot:
            await notifier.send_post_success(
                title=title,
                url=result['url'],
                posts_today=1,
                daily_limit=10
            )
            print("📱 텔레그램 알림 전송 완료!")
        else:
            print("⚠️ 텔레그램 미설정 - 알림 스킵")

        print("\n확인사항:")
        print("  1. 소제목(##)이 제목 스타일로 표시되는지 확인")
        print("  2. 굵은 글씨(**)가 Bold로 표시되는지 확인")
        print("  3. 인용구(>)가 인용구 스타일로 표시되는지 확인")
        print("  4. 본문에 취소선이 없는지 확인")
        print("  5. 이미지가 정상적으로 표시되는지 확인")
        print("  6. 텔레그램으로 알림이 왔는지 확인")
    else:
        print("❌ 포스팅 테스트 실패!")
        print(f"에러: {result['error']}")

        # 텔레그램 실패 알림
        if notifier.bot:
            await notifier.send_post_failure(
                error=result.get('error', '알 수 없는 오류'),
                errors_count=1
            )
            print("📱 텔레그램 실패 알림 전송!")

    print("=" * 60)

    return result


if __name__ == "__main__":
    asyncio.run(test_post_with_telegram())
