"""
수동 로그인 헬퍼 스크립트
- 브라우저를 열어 수동으로 네이버 로그인
- 캡챠와 2FA를 사용자가 직접 처리
- 로그인 완료 후 세션을 저장
- 저장된 세션은 자동화 스크립트에서 재사용
"""

import asyncio
import os
import requests
from patchright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from loguru import logger
import sys

# CDP 설정
USE_CDP = os.environ.get("USE_CDP", "True").lower() == "true"
CDP_ENDPOINT = os.environ.get("CDP_ENDPOINT", "http://127.0.0.1:9222")


async def manual_login(naver_id: str):
    """
    수동 로그인 프로세스
    - CDP 모드: 영속 Chrome에 연결 → 로그인 → Chrome 프로필에 쿠키 자동 저장
    - 기존 모드: 새 브라우저 실행 → 로그인 → 세션 파일 암호화 저장
    """
    session_manager = SecureSessionManager()

    logger.info("=" * 60)
    logger.info("네이버 블로그 수동 로그인 도구")
    logger.info("=" * 60)
    logger.info(f"계정: {naver_id}")

    # CDP 연결 가능 여부 확인
    use_cdp = False
    if USE_CDP:
        try:
            resp = requests.get(f"{CDP_ENDPOINT}/json/version", timeout=3)
            if resp.status_code == 200:
                use_cdp = True
                logger.info(f"모드: CDP (영속 Chrome 연결)")
        except Exception:
            pass

    if not use_cdp:
        logger.info("모드: 독립 브라우저 (세션 파일 저장)")

    logger.info("")
    logger.info("사용 방법:")
    logger.info("1. 브라우저가 열리면 네이버에 로그인하세요")
    logger.info("2. 캡챠와 2차 인증을 완료하세요")
    logger.info("3. 로그인이 완료되면 자동으로 감지됩니다")
    logger.info("=" * 60)
    logger.info("")

    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        is_cdp = False

        if use_cdp:
            # CDP: 영속 Chrome에 연결
            try:
                browser = await asyncio.wait_for(
                    p.chromium.connect_over_cdp(CDP_ENDPOINT),
                    timeout=5,
                )
                is_cdp = True
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                    page = await context.new_page()
                else:
                    context = await browser.new_context()
                    page = await context.new_page()
                logger.success("Chrome CDP 연결 성공!")
            except Exception as e:
                logger.warning(f"CDP 연결 실패: {e}")
                logger.info("독립 브라우저로 대체합니다...")
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                browser = None
                is_cdp = False

        if not is_cdp:
            # 기존 방식: 새 브라우저 실행
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul'
            )
            page = await context.new_page()

        # 네이버 로그인 페이지로 이동
        logger.info("네이버 로그인 페이지로 이동 중...")
        await page.goto('https://nid.naver.com/nidlogin.login')
        await page.wait_for_load_state('networkidle')

        logger.info("")
        logger.info("브라우저에서 로그인을 진행해주세요!")
        logger.info("")
        logger.info("⏳ 로그인 완료를 대기 중... (최대 3분)")

        # 로그인 완료 자동 감지 (최대 3분 대기)
        login_detected = False
        for _ in range(180):
            await asyncio.sleep(1)
            current_url = page.url
            if 'nid.naver.com' not in current_url or 'nidlogin' not in current_url:
                login_detected = True
                logger.info(f"페이지 이동 감지: {current_url[:50]}...")
                break

        if not login_detected:
            logger.error("로그인 시간 초과 (3분)")
            if not is_cdp:
                await browser.close()
            return False

        await asyncio.sleep(2)

        # 블로그로 이동해서 확인
        logger.info("블로그 페이지로 이동 중...")
        await page.goto('https://blog.naver.com/')
        await page.wait_for_timeout(3000)

        try:
            await page.wait_for_selector('a[href*="PostList.naver"]', timeout=5000)
            logger.success("로그인 확인 완료!")
        except Exception:
            logger.warning("로그인 확인 불가 - 그래도 세션 저장 시도")

        if is_cdp:
            # CDP 모드: Chrome 프로필에 쿠키가 자동 저장됨
            # 추가로 세션 파일도 백업 저장
            logger.info("CDP 모드: Chrome 프로필에 쿠키 자동 저장됨")
            try:
                storage_state = await context.storage_state()
                session_manager.save_session(storage_state, f"{naver_id}_cdp")
                logger.info(f"세션 백업 저장: {naver_id}_cdp")
            except Exception:
                pass
            # 페이지만 닫고 Chrome은 유지
            await page.close()
        else:
            # 기존 모드: 세션 파일 저장
            logger.info("세션 저장 중...")
            storage_state = await context.storage_state()
            if session_manager.save_session(storage_state, f"{naver_id}_manual"):
                logger.success(f"세션 저장 완료: {naver_id}_manual")
            else:
                logger.error("세션 저장 실패")
                await browser.close()
                return False
            await browser.close()

        logger.info("")
        logger.info("=" * 60)
        if is_cdp:
            logger.info("CDP 모드: Chrome이 계속 실행 중이므로")
            logger.info("바로 auto_post.py를 실행하면 됩니다!")
        else:
            logger.info("이제 자동화 스크립트를 실행하면")
            logger.info("저장된 세션을 사용하여 로그인 없이 포스팅됩니다!")
        logger.info("=" * 60)
        return True


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python manual_login.py <네이버아이디>")
        print("예시: python manual_login.py wncksdid0750")
        sys.exit(1)

    naver_id = sys.argv[1]
    success = asyncio.run(manual_login(naver_id))

    if success:
        logger.success("\n수동 로그인 완료!")
        logger.info("\n다음 명령어로 자동 포스팅을 실행하세요:")
        logger.info(f"python auto_post.py --naver-id {naver_id}")
    else:
        logger.error("\n수동 로그인 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
