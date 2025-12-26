"""
클립보드 방식 수동 로그인 헬퍼 스크립트
- 기존 manual_login.py의 세션 저장 방식과 연동
- pyperclip + pyautogui를 사용한 자연스러운 입력
- fill() 함수 오작동 시 대안
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from utils.clipboard_input import ClipboardInputHelper
from loguru import logger


async def manual_login_with_clipboard(
    naver_id: str,
    naver_pw: str = None,
    auto_input: bool = False
):
    """
    클립보드 방식 수동 로그인

    Args:
        naver_id: 네이버 아이디
        naver_pw: 네이버 비밀번호 (auto_input=True일 때 필요)
        auto_input: 자동 입력 여부 (False면 수동 입력)
    """
    session_manager = SecureSessionManager()
    clipboard_helper = ClipboardInputHelper()

    logger.info("=" * 60)
    logger.info("네이버 블로그 수동 로그인 (클립보드 방식)")
    logger.info("=" * 60)
    logger.info(f"계정: {naver_id}")
    logger.info(f"자동 입력: {'활성화' if auto_input else '비활성화'}")
    logger.info("")

    if auto_input and not naver_pw:
        logger.error("자동 입력 모드에는 비밀번호가 필요합니다")
        return False

    async with async_playwright() as p:
        # 브라우저 시작
        browser = await p.chromium.launch(
            headless=False,
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

        if auto_input:
            logger.info("")
            logger.info("🔐 클립보드 방식으로 자격 증명 입력 중...")
            logger.info("※ 입력 중에는 마우스/키보드를 사용하지 마세요")
            logger.info("")

            await asyncio.sleep(1)

            # 클립보드 방식으로 아이디/비밀번호 입력
            try:
                await clipboard_helper.type_credentials(
                    page,
                    id_selector='#id',
                    pw_selector='#pw',
                    naver_id=naver_id,
                    naver_pw=naver_pw
                )

                logger.success("✅ 자격 증명 입력 완료")

                # 로그인 버튼 클릭
                await asyncio.sleep(0.5)
                await page.click('#log\\.login')
                logger.info("로그인 버튼 클릭 완료")
                logger.info("")
                logger.info("⚠️ 캡챠가 나타나면 직접 해결하세요")

            except Exception as e:
                logger.error(f"자동 입력 실패: {e}")
                logger.info("수동으로 입력해주세요")

        else:
            logger.info("")
            logger.info("✋ 브라우저에서 로그인을 진행해주세요!")
            logger.info("")
            logger.info("단계:")
            logger.info("1. 아이디/비밀번호 입력")
            logger.info("2. 캡챠 해결")
            logger.info("3. 2차 인증 완료 (필요시)")
            logger.info("")

        logger.info("⏳ 로그인 완료를 대기 중... (최대 3분)")

        # 로그인 완료 자동 감지
        login_detected = False
        for _ in range(180):
            await asyncio.sleep(1)
            current_url = page.url

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

        # 로그인 상태 확인
        try:
            await page.wait_for_selector('a[href*="PostList.naver"]', timeout=5000)
            logger.success("✅ 로그인 확인 완료!")
        except:
            logger.warning("⚠️ 로그인 확인 불가 - 그래도 세션 저장 시도")

        # 세션 저장
        logger.info("세션 저장 중...")
        storage_state = await context.storage_state()

        session_name = f"{naver_id}_clipboard"
        if session_manager.save_session(
            storage_state,
            session_name,
            metadata={"method": "clipboard", "account_id": naver_id}
        ):
            logger.success(f"✅ 세션 저장 완료: {session_name}")
            logger.info("")
            logger.info("=" * 60)
            logger.info("저장된 세션을 사용하려면:")
            logger.info(f"python main.py --naver-id {naver_id} --session-name {session_name}")
            logger.info("=" * 60)

            await browser.close()
            return True
        else:
            logger.error("❌ 세션 저장 실패")
            await browser.close()
            return False


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='클립보드 방식 네이버 로그인 도구'
    )
    parser.add_argument(
        'naver_id',
        help='네이버 아이디'
    )
    parser.add_argument(
        '--password', '-p',
        help='네이버 비밀번호 (자동 입력 시 필요)',
        default=None
    )
    parser.add_argument(
        '--auto-input', '-a',
        action='store_true',
        help='클립보드 방식으로 자동 입력'
    )

    args = parser.parse_args()

    # 비밀번호 입력 (자동 입력 모드일 때)
    naver_pw = args.password
    if args.auto_input and not naver_pw:
        import getpass
        naver_pw = getpass.getpass("네이버 비밀번호: ")

    # 비동기 실행
    success = asyncio.run(
        manual_login_with_clipboard(
            naver_id=args.naver_id,
            naver_pw=naver_pw,
            auto_input=args.auto_input
        )
    )

    if success:
        logger.success("\n✅ 로그인 및 세션 저장 완료!")
    else:
        logger.error("\n❌ 로그인 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
