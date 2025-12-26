"""
Upload Orchestrator Agent
- Playwright 기반 브라우저 자동화
- Human-like 행동 패턴 시뮬레이션
- 스마트에디터 ONE 자동 제어
- 에러 복구 및 재시도 로직
"""

import asyncio
import random
from typing import Dict, Any, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger

from security.credential_manager import CredentialManager
from security.session_manager import SecureSessionManager, save_playwright_session, load_playwright_session


class HumanBehavior:
    """인간 행동 시뮬레이션 헬퍼 클래스 (임시)"""

    async def random_delay(self, min_sec: float, max_sec: float):
        """랜덤 딜레이"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def human_type(self, page: Page, selector: str, text: str):
        """인간처럼 타이핑"""
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def human_click(self, page: Page, selector: str):
        """인간처럼 클릭"""
        await page.click(selector)
        await self.random_delay(0.1, 0.3)


class UploadAgent:
    """브라우저 자동화 및 블로그 업로드 에이전트"""

    NAVER_BLOG_URL = "https://blog.naver.com"
    NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
    WRITE_URL = "https://blog.naver.com/PostWriteForm.naver"

    # 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # 초

    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        session_manager: Optional[SecureSessionManager] = None,
        headless: bool = False
    ):
        """
        Args:
            credential_manager: 자격증명 관리자
            session_manager: 세션 관리자
            headless: 헤드리스 모드 여부
        """
        self.cred_manager = credential_manager or CredentialManager()
        self.session_manager = session_manager or SecureSessionManager()
        self.headless = headless
        self.human_behavior = HumanBehavior()

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def upload_post(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: List[str],
        naver_id: str,
        category: str = "암호화폐"
    ) -> Dict[str, Any]:
        """
        블로그 포스트 업로드

        Args:
            title: 제목
            content: 본문 (HTML)
            images: 이미지 경로 리스트
            tags: 태그 리스트
            naver_id: 네이버 ID
            category: 카테고리

        Returns:
            {
                "success": bool,
                "post_url": str,
                "error": str,
                "attempts": int
            }
        """
        logger.info(f"블로그 포스트 업로드 시작: {title}")

        # 세션 로드용 ID 저장
        self.current_naver_id = naver_id

        result = {
            "success": False,
            "post_url": "",
            "error": "",
            "attempts": 0
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            result["attempts"] = attempt
            logger.info(f"업로드 시도 {attempt}/{self.MAX_RETRIES}")

            try:
                # 브라우저 시작
                await self._start_browser()

                # 로그인
                login_success = await self._login(naver_id)
                if not login_success:
                    raise Exception("로그인 실패")

                # 글쓰기 페이지로 이동
                await self._navigate_to_write_page()

                # 제목 입력
                await self._input_title(title)

                # 본문 입력
                await self._input_content(content)

                # 이미지 업로드
                if images:
                    await self._upload_images(images)

                # 태그 입력
                await self._input_tags(tags)

                # 카테고리 설정
                await self._set_category(category)

                # 발행
                post_url = await self._publish_post()

                # 성공!
                result["success"] = True
                result["post_url"] = post_url
                logger.success(f"포스트 업로드 성공: {post_url}")

                # 세션 저장
                await save_playwright_session(
                    self.context,
                    self.session_manager,
                    session_name="default",
                    account_id=naver_id
                )

                break  # 성공하면 루프 종료

            except Exception as e:
                logger.error(f"업로드 시도 {attempt} 실패: {e}")
                result["error"] = str(e)

                if attempt < self.MAX_RETRIES:
                    logger.info(f"{self.RETRY_DELAY}초 후 재시도...")
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    logger.error("모든 재시도 실패")

            finally:
                # 브라우저 종료
                await self._close_browser()

        return result

    async def _start_browser(self):
        """브라우저 시작 - Comet 브라우저 CDP 연결 우선"""

        self._playwright = await async_playwright().start()

        # 1. Comet 브라우저 CDP 연결 시도 (포트 9222)
        try:
            logger.info("Comet 브라우저 연결 시도 중... (CDP 포트 9222)")
            self.browser = await self._playwright.chromium.connect_over_cdp(
                "http://127.0.0.1:9222"
            )
            # 기존 컨텍스트 사용 (로그인 상태 유지)
            self._is_cdp = True  # CDP 연결 표시
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.success("✅ Comet 브라우저 연결 성공! (기존 로그인 상태 사용)")

                # 기존 페이지 사용 또는 새 페이지 생성
                pages = self.context.pages
                if pages:
                    self.page = pages[0]
                    logger.info(f"기존 페이지 사용: {self.page.url}")
                else:
                    self.page = await self.context.new_page()
                    logger.info("새 페이지 생성")
                return
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                logger.info("Comet 연결됨, 새 컨텍스트 생성")
                return

        except Exception as e:
            logger.warning(f"Comet 연결 실패: {e}")
            logger.info("일반 브라우저로 대체...")

        # 2. Comet 연결 실패 시 일반 브라우저 실행
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # 세션 복구 시도 (수동 로그인 세션 우선)
        self.context = await load_playwright_session(
            self.browser,
            self.session_manager,
            session_name=f"{self.current_naver_id}_manual" if hasattr(self, 'current_naver_id') else "default"
        )

        # 기본 세션 시도
        if not self.context:
            self.context = await load_playwright_session(
                self.browser,
                self.session_manager,
                session_name="default"
            )

        if not self.context:
            # 새 컨텍스트 생성
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul'
            )

            # navigator.webdriver 제거 (봇 탐지 우회)
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

        self.page = await self.context.new_page()
        logger.info("브라우저 시작 완료")

    async def _close_browser(self):
        """브라우저 종료 - Comet 연결 시 브라우저는 유지"""
        # CDP로 연결된 경우 (Comet) 브라우저는 닫지 않음
        is_cdp_connection = hasattr(self, '_is_cdp') and self._is_cdp

        if self.page and not is_cdp_connection:
            try:
                await self.page.close()
            except Exception:
                pass

        if self.context and not is_cdp_connection:
            try:
                await self.context.close()
            except Exception:
                pass

        if self.browser and not is_cdp_connection:
            try:
                await self.browser.close()
            except Exception:
                pass

        if hasattr(self, '_playwright') and self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass

        logger.info("브라우저 연결 정리 완료")

    async def _login(self, naver_id: str) -> bool:
        """네이버 로그인 - 저장된 세션 사용 시 로그인 건너뛰기"""

        # 블로그 페이지로 이동하여 로그인 상태 확인
        try:
            logger.info("로그인 상태 확인 중...")
            await self.page.goto(self.NAVER_BLOG_URL, wait_until='networkidle')
            await asyncio.sleep(3)

            # 여러 방법으로 로그인 상태 확인
            page_content = await self.page.content()

            # 로그인 상태 확인 (여러 조건)
            is_logged_in = False

            # 1. 내 블로그 링크 확인
            my_blog_link = await self.page.locator(f'a[href*="{naver_id}"]').count()
            if my_blog_link > 0:
                is_logged_in = True
                logger.info("✓ 내 블로그 링크 발견")

            # 2. 글쓰기 버튼 확인
            write_button = await self.page.locator('a[href*="PostWriteForm"], button:has-text("글쓰기")').count()
            if write_button > 0:
                is_logged_in = True
                logger.info("✓ 글쓰기 버튼 발견")

            # 3. 로그인 버튼이 없는지 확인
            login_button = await self.page.locator('a[href*="nidlogin"], button:has-text("로그인")').count()
            if login_button == 0 and ("로그인" not in page_content[:500]):
                is_logged_in = True
                logger.info("✓ 로그인 버튼 없음")

            if is_logged_in:
                logger.success("✅ 세션 유효, 로그인 건너뛰기!")
                return True
            else:
                logger.warning("세션이 만료되었거나 로그인되지 않음")

        except Exception as e:
            logger.warning(f"세션 확인 실패: {e}")

        # 세션이 유효하지 않으면 수동 로그인 필요
        logger.error("❌ 세션이 유효하지 않습니다!")
        logger.error("다음 명령어로 수동 로그인을 다시 진행하세요:")
        logger.error(f"  python manual_login.py {naver_id}")
        logger.error("")
        logger.error("수동 로그인 후 다시 자동 포스팅을 실행하세요.")

        # 자동 로그인 시도하지 않음 (캡챠/2FA 문제 방지)
        return False

    async def _navigate_to_write_page(self):
        """글쓰기 페이지로 이동"""
        await self.page.goto(self.WRITE_URL, wait_until='networkidle')
        await self.human_behavior.random_delay(2, 3)
        logger.info("글쓰기 페이지 이동 완료")

    async def _input_title(self, title: str):
        """제목 입력"""
        logger.info("제목 입력 중...")

        title_selector = 'input.se-input, textarea.textarea_input, input[placeholder*="제목"]'

        await self.page.wait_for_selector(title_selector, timeout=10000)
        await self.human_behavior.human_click(self.page, title_selector)
        await self.human_behavior.random_delay(0.3, 0.6)

        await self.human_behavior.human_type(self.page, title_selector, title)
        await self.human_behavior.random_delay(0.5, 1)

        logger.success("제목 입력 완료")

    async def _input_content(self, content: str):
        """본문 입력 (안전한 방법 사용)"""
        logger.info("본문 입력 중...")

        editor_selector = '.se-component-content, [contenteditable="true"]'

        await self.page.wait_for_selector(editor_selector, timeout=10000)
        await self.human_behavior.human_click(self.page, editor_selector)
        await self.human_behavior.random_delay(0.5, 1)

        # 안전한 방법: Playwright의 fill 또는 type 사용
        # HTML 콘텐츠를 텍스트로 타이핑 (에디터가 자동 파싱)
        await self.page.keyboard.type(content)

        await self.human_behavior.random_delay(1, 2)
        logger.success("본문 입력 완료")

    async def _upload_images(self, image_paths: List[str]):
        """이미지 업로드"""
        logger.info(f"이미지 {len(image_paths)}개 업로드 중...")

        for i, image_path in enumerate(image_paths, 1):
            try:
                image_button_selector = 'button[aria-label*="사진"], button[title*="사진"]'

                await self.human_behavior.human_click(self.page, image_button_selector)
                await self.human_behavior.random_delay(0.5, 1)

                file_input = await self.page.locator('input[type="file"]').first
                await file_input.set_input_files(image_path)

                await asyncio.sleep(3)

                logger.info(f"이미지 {i}/{len(image_paths)} 업로드 완료")

            except Exception as e:
                logger.error(f"이미지 업로드 실패 ({image_path}): {e}")

    async def _input_tags(self, tags: List[str]):
        """태그 입력"""
        logger.info(f"태그 {len(tags)}개 입력 중...")

        try:
            tag_selector = 'input[placeholder*="태그"], input.tag_input'

            await self.page.wait_for_selector(tag_selector, timeout=5000)

            for tag in tags:
                await self.human_behavior.human_type(self.page, tag_selector, tag)
                await self.page.keyboard.press('Enter')
                await self.human_behavior.random_delay(0.3, 0.6)

            logger.success("태그 입력 완료")

        except Exception as e:
            logger.warning(f"태그 입력 실패 (선택 기능): {e}")

    async def _set_category(self, category: str):
        """카테고리 설정"""
        logger.info(f"카테고리 설정: {category}")

        try:
            category_button_selector = 'button[aria-label*="카테고리"]'
            await self.human_behavior.human_click(self.page, category_button_selector)
            await self.human_behavior.random_delay(0.5, 1)

            category_option = f'text="{category}"'
            await self.page.click(category_option)
            await self.human_behavior.random_delay(0.3, 0.6)

            logger.success("카테고리 설정 완료")

        except Exception as e:
            logger.warning(f"카테고리 설정 실패 (선택 기능): {e}")

    async def _publish_post(self) -> str:
        """포스트 발행 - 2단계 클릭 (상단 버튼 → 설정 레이어 내 최종 발행)"""
        logger.info("포스트 발행 중...")

        # 1단계: 상단 발행 버튼 클릭
        publish_button_selectors = [
            'button[class*="publish_btn"]',
            'button.publish_btn__m9KHH',
            'button.se-publish-button',
            'button:has-text("발행"):not(:has-text("예약"))',
            'button[aria-label*="발행"]',
        ]

        clicked = False
        for selector in publish_button_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=3000):
                    await self.human_behavior.human_click(self.page, selector)
                    logger.info(f"1단계 - 상단 발행 버튼 클릭: {selector}")
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            logger.warning("상단 발행 버튼을 찾지 못함")

        # 설정 레이어 나타날 때까지 대기
        await asyncio.sleep(2)

        # 2단계: 발행 설정 레이어 내 최종 발행 버튼 클릭
        await self._click_final_publish_button()

        # 발행 완료 대기
        await self.page.wait_for_load_state('networkidle', timeout=15000)
        await asyncio.sleep(2)

        post_url = self.page.url
        logger.success(f"포스트 발행 완료: {post_url}")
        return post_url

    async def _click_final_publish_button(self):
        """설정 레이어 내 최종 발행 버튼 클릭"""
        logger.info("발행 설정 레이어에서 최종 발행 버튼 검색 중...")

        # 설정 레이어 대기
        layer_selectors = [
            '[class*="publish_layer"]',
            '[class*="PublishLayer"]',
            '[class*="publish_popup"]',
            '[role="dialog"]',
        ]

        for selector in layer_selectors:
            try:
                layer = self.page.locator(selector).first
                await layer.wait_for(state='visible', timeout=5000)
                logger.info(f"발행 설정 레이어 발견: {selector}")
                break
            except:
                continue

        await asyncio.sleep(1)

        # 최종 발행 버튼 셀렉터
        final_publish_selectors = [
            '[class*="publish_layer"] button[class*="confirm"]',
            '[class*="publish_layer"] button[class*="publish"]',
            '[role="dialog"] button:has-text("발행")',
            '[class*="layer"] button:has-text("발행")',
            '[class*="footer"] button:has-text("발행")',
            'button[class*="confirm_btn"]',
            'button[class*="btn_publish"]',
        ]

        for selector in final_publish_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    await btn.click()
                    logger.info(f"2단계 - 최종 발행 버튼 클릭: {selector}")
                    await asyncio.sleep(2)
                    return
            except:
                continue

        # 폴백: 모든 "발행" 버튼 중 마지막 보이는 버튼
        logger.info("최종 발행 버튼 폴백 검색 중...")
        try:
            all_btns = self.page.locator('button:has-text("발행")')
            count = await all_btns.count()
            visible_btns = []

            for i in range(count):
                btn = all_btns.nth(i)
                if await btn.is_visible():
                    visible_btns.append(btn)

            if len(visible_btns) >= 2:
                final_btn = visible_btns[-1]
                await final_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await final_btn.click()
                logger.info("2단계 - 최종 발행 버튼 클릭 (폴백 - 마지막 버튼)")
                await asyncio.sleep(2)
            elif len(visible_btns) == 1:
                await visible_btns[0].click()
                logger.info("2단계 - 발행 버튼 재클릭")
                await asyncio.sleep(2)

        except Exception as e:
            logger.warning(f"폴백 발행 버튼 검색 실패: {e}")


# ============================================
# 테스트 코드
# ============================================

async def test_upload_agent():
    """Upload Agent 테스트"""
    print("\n=== Upload Agent 테스트 ===\n")
    print("실제 네이버 계정으로 테스트하므로 주의!")
    print("테스트를 위해서는 코드에서 YOUR_NAVER_ID를 실제 ID로 변경하세요.")


if __name__ == "__main__":
    asyncio.run(test_upload_agent())
