"""
수동 로그인 헬퍼 스크립트
- 브라우저를 열어 수동으로 네이버 로그인
- 캡챠와 2FA를 사용자가 직접 처리
- 로그인 완료 후 세션을 저장
- 저장된 세션은 자동화 스크립트에서 재사용
"""

import asyncio
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from loguru import logger
import sys


async def manual_login(naver_id: str):
    """
    수동 로그인 프로세스
    1. 브라우저 열기 (헤드리스 아님)
    2. 네이버 로그인 페이지로 이동
    3. 사용자가 수동으로 로그인 (캡챠, 2FA 포함)
    4. 로그인 완료 확인
    5. 세션 저장
    """
    session_manager = SecureSessionManager()

    logger.info("=" * 60)
    logger.info("네이버 블로그 수동 로그인 도구")
    logger.info("=" * 60)
    logger.info(f"계정: {naver_id}")
    logger.info("")
    logger.info("사용 방법:")
    logger.info("1. 브라우저가 열리면 네이버에 로그인하세요")
    logger.info("2. 캡챠와 2차 인증을 완료하세요")
    logger.info("3. 블로그 메인 페이지가 보이면 Enter를 누르세요")
    logger.info("=" * 60)
    logger.info("")

    async with async_playwright() as p:
        # 브라우저 시작 (헤드리스 아님 - 사용자가 볼 수 있게)
        browser = await p.chromium.launch(
            headless=False,  # 브라우저 창 표시
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # 컨텍스트 생성
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )

        # 봇 탐지 우회 스크립트
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()

        # 네이버 로그인 페이지로 이동
        logger.info("네이버 로그인 페이지로 이동 중...")
        await page.goto('https://nid.naver.com/nidlogin.login')
        await page.wait_for_load_state('networkidle')

        logger.info("")
        logger.info("✋ 브라우저에서 로그인을 진행해주세요!")
        logger.info("")
        logger.info("단계:")
        logger.info("1. 아이디/비밀번호 입력")
        logger.info("2. 캡챠 해결")
        logger.info("3. 2차 인증 완료 (필요시)")
        logger.info("4. 로그인이 완료되면 자동으로 감지됩니다")
        logger.info("")
        logger.info("⏳ 로그인 완료를 대기 중... (최대 3분)")

        # 로그인 완료 자동 감지 (최대 3분 대기)
        login_detected = False
        for _ in range(180):  # 180초 = 3분
            await asyncio.sleep(1)
            current_url = page.url

            # 로그인 페이지를 벗어났는지 확인
            if 'nid.naver.com' not in current_url or 'nidlogin' not in current_url:
                login_detected = True
                logger.info(f"✓ 페이지 이동 감지: {current_url[:50]}...")
                break

        if not login_detected:
            logger.error("❌ 로그인 시간 초과 (3분)")
            await browser.close()
            return False

        # 잠시 대기 (리다이렉트 완료)
        await asyncio.sleep(2)

        # 블로그로 이동해서 확인
        logger.info("블로그 페이지로 이동 중...")
        await page.goto('https://blog.naver.com/')
        await page.wait_for_timeout(3000)

        # 로그인 상태 확인 (프로필 아이콘 등)
        try:
            # 로그인된 사용자의 프로필 영역이 있는지 확인
            await page.wait_for_selector('a[href*="PostList.naver"]', timeout=5000)
            logger.success("✅ 로그인 확인 완료!")
        except:
            logger.warning("⚠️ 로그인 확인 불가 - 그래도 세션 저장 시도")

        # 세션 저장
        logger.info("세션 저장 중...")
        storage_state = await context.storage_state()

        if session_manager.save_session(storage_state, f"{naver_id}_manual"):
            logger.success(f"✅ 세션 저장 완료: {naver_id}_manual")
            logger.info("")
            logger.info("=" * 60)
            logger.info("이제 자동화 스크립트를 실행하면")
            logger.info("저장된 세션을 사용하여 로그인 없이 포스팅됩니다!")
            logger.info("=" * 60)

            # 브라우저 종료
            await browser.close()
            return True
        else:
            logger.error("❌ 세션 저장 실패")
            await browser.close()
            return False


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python manual_login.py <네이버아이디>")
        print("예시: python manual_login.py wncksdid0750")
        sys.exit(1)

    naver_id = sys.argv[1]

    # 비동기 실행
    success = asyncio.run(manual_login(naver_id))

    if success:
        logger.success("\n✅ 수동 로그인 완료!")
        logger.info("\n다음 명령어로 자동 포스팅을 실행하세요:")
        logger.info(f"python main.py --naver-id {naver_id} --use-saved-session")
    else:
        logger.error("\n❌ 수동 로그인 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
