"""
세션 자동 갱신 시스템
- Playwright 세션 유효성 검사
- 자동 세션 갱신
- 비상 재로그인 처리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.session_manager import SecureSessionManager


class SessionKeeper:
    """세션 자동 관리 클래스"""

    # 세션 체크 간격 (분)
    CHECK_INTERVAL_MINUTES = 30

    # 세션 갱신 임계값 (시간) - 이 시간 전에 갱신 시도
    REFRESH_THRESHOLD_HOURS = 6

    # 최대 갱신 시도 횟수
    MAX_REFRESH_ATTEMPTS = 3

    def __init__(
        self,
        naver_id: str,
        session_manager: Optional[SecureSessionManager] = None
    ):
        """
        Args:
            naver_id: 네이버 계정 ID
            session_manager: 세션 매니저 인스턴스 (None이면 자동 생성)
        """
        self.naver_id = naver_id
        self.session_manager = session_manager or SecureSessionManager()

        # 상태 추적
        self.last_check_time: Optional[datetime] = None
        self.last_refresh_time: Optional[datetime] = None
        self.refresh_attempts = 0
        self.is_session_valid = False

        logger.info(f"SessionKeeper 초기화: {naver_id}")

    async def check_session_valid(self, browser_context=None) -> bool:
        """
        세션 유효성 검사

        Args:
            browser_context: Playwright BrowserContext (없으면 저장된 세션 확인)

        Returns:
            세션 유효 여부
        """
        self.last_check_time = datetime.now()

        try:
            # 1. 저장된 세션 파일 확인
            session_name = f"naver_{self.naver_id}"
            if not self.session_manager.is_session_valid(session_name, max_age_days=7):
                logger.warning("저장된 세션이 만료되었거나 없습니다")
                self.is_session_valid = False
                return False

            # 2. 브라우저 컨텍스트가 있으면 실제 로그인 상태 확인
            if browser_context:
                is_logged_in = await self._verify_login_status(browser_context)
                self.is_session_valid = is_logged_in
                return is_logged_in

            # 3. 세션 파일만으로 판단
            self.is_session_valid = True
            logger.info("세션 유효성 확인 완료")
            return True

        except Exception as e:
            logger.error(f"세션 유효성 검사 실패: {e}")
            self.is_session_valid = False
            return False

    async def _verify_login_status(self, browser_context) -> bool:
        """실제 로그인 상태 확인"""
        try:
            page = await browser_context.new_page()

            # 네이버 블로그 접근
            await page.goto("https://blog.naver.com", wait_until="networkidle")

            # 로그인 상태 확인 (여러 셀렉터 시도)
            login_selectors = [
                ".gnb_login_link",  # 로그아웃 상태의 로그인 버튼
                "#gnb_login_button",
            ]

            for selector in login_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.warning("로그인이 필요한 상태입니다")
                    await page.close()
                    return False

            # 로그인된 상태 확인
            logged_in_selectors = [
                ".gnb_my",
                ".gnb_logout_link",
                "#gnb_my_name"
            ]

            for selector in logged_in_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.success("로그인 상태 확인됨")
                    await page.close()
                    return True

            await page.close()
            logger.warning("로그인 상태를 확인할 수 없습니다")
            return False

        except Exception as e:
            logger.error(f"로그인 상태 확인 중 오류: {e}")
            return False

    async def refresh_session(self, browser_context) -> bool:
        """
        세션 갱신 (페이지 새로고침으로 쿠키 갱신)

        Args:
            browser_context: Playwright BrowserContext

        Returns:
            갱신 성공 여부
        """
        self.refresh_attempts += 1
        logger.info(f"세션 갱신 시도 #{self.refresh_attempts}")

        try:
            page = await browser_context.new_page()

            # 네이버 메인 페이지 방문하여 쿠키 갱신
            await page.goto("https://www.naver.com", wait_until="networkidle")
            await asyncio.sleep(2)

            # 네이버 블로그 방문
            await page.goto("https://blog.naver.com", wait_until="networkidle")
            await asyncio.sleep(2)

            await page.close()

            # 새로운 세션 저장
            from security.session_manager import save_playwright_session
            session_name = f"naver_{self.naver_id}"

            success = await save_playwright_session(
                browser_context,
                self.session_manager,
                session_name,
                account_id=self.naver_id
            )

            if success:
                self.last_refresh_time = datetime.now()
                self.refresh_attempts = 0
                logger.success("세션 갱신 완료")
                return True
            else:
                logger.warning("세션 저장 실패")
                return False

        except Exception as e:
            logger.error(f"세션 갱신 중 오류: {e}")
            return False

    async def emergency_relogin(self) -> bool:
        """
        비상 재로그인 (수동 로그인 필요 알림)

        Returns:
            재로그인 필요 알림 성공 여부
        """
        logger.warning("=" * 50)
        logger.warning("비상 재로그인 필요!")
        logger.warning("세션이 만료되어 수동 로그인이 필요합니다.")
        logger.warning("manual_login.py를 실행하여 다시 로그인해주세요.")
        logger.warning("=" * 50)

        # 텔레그램 알림 전송
        try:
            from utils.telegram_notifier import send_notification

            await send_notification(
                f"🚨 긴급: 세션 만료!\n\n"
                f"계정: {self.naver_id}\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"수동 로그인이 필요합니다.\n"
                f"manual_login.py를 실행해주세요."
            )
            return True

        except Exception as e:
            logger.error(f"텔레그램 알림 실패: {e}")
            return False

    async def run_session_monitor(self, browser_context) -> None:
        """
        세션 모니터링 루프 (백그라운드 실행용)

        Args:
            browser_context: Playwright BrowserContext
        """
        logger.info("세션 모니터링 시작")

        while True:
            try:
                # 세션 유효성 검사
                is_valid = await self.check_session_valid(browser_context)

                if not is_valid:
                    # 세션 갱신 시도
                    if self.refresh_attempts < self.MAX_REFRESH_ATTEMPTS:
                        success = await self.refresh_session(browser_context)

                        if not success:
                            logger.warning(
                                f"세션 갱신 실패 "
                                f"({self.refresh_attempts}/{self.MAX_REFRESH_ATTEMPTS})"
                            )
                    else:
                        # 최대 시도 초과 - 비상 재로그인
                        await self.emergency_relogin()
                        break

                # 다음 체크까지 대기
                await asyncio.sleep(self.CHECK_INTERVAL_MINUTES * 60)

            except asyncio.CancelledError:
                logger.info("세션 모니터링 종료")
                break
            except Exception as e:
                logger.error(f"세션 모니터링 오류: {e}")
                await asyncio.sleep(60)  # 1분 후 재시도

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "naver_id": self.naver_id,
            "is_valid": self.is_session_valid,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_refresh": self.last_refresh_time.isoformat() if self.last_refresh_time else None,
            "refresh_attempts": self.refresh_attempts
        }


# ============================================
# 테스트 코드
# ============================================

async def test_session_keeper():
    """SessionKeeper 테스트"""
    print("\n=== SessionKeeper 테스트 ===\n")

    keeper = SessionKeeper(naver_id="test_user")

    # 상태 확인
    status = keeper.get_status()
    print(f"초기 상태: {status}")

    # 세션 유효성 확인 (브라우저 없이)
    is_valid = await keeper.check_session_valid()
    print(f"세션 유효: {is_valid}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_session_keeper())
