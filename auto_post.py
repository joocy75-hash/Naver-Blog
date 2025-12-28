"""
네이버 블로그 자동 포스팅 스크립트
- 저장된 세션 사용
- 글쓰기 페이지 이동
- 팝업 처리
- 제목/본문 입력
- 발행까지 완전 자동화
- 인간 행동 패턴 시뮬레이션 (봇 탐지 회피)
"""

import asyncio
import os
import platform
import random
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from utils.clipboard_input import ClipboardInputHelper
from loguru import logger

# 환경 변수에서 HEADLESS 설정 읽기 (기본값: 서버에서는 True)
HEADLESS_MODE = os.environ.get("HEADLESS", "True").lower() == "true"


class HumanDelay:
    """
    인간 행동 패턴을 시뮬레이션하는 딜레이 헬퍼
    - 네이버 봇 탐지 회피를 위한 자연스러운 타이밍
    - config/human_timing.py에서 설정 로드
    - 모든 딜레이에 랜덤 변동폭 적용
    """

    # 설정 파일에서 로드 (없으면 기본값 사용)
    try:
        from config.human_timing import (
            DELAYS,
            TYPING,
            TIMEOUTS,
            SAFE_MODE,
            SAFE_MODE_MULTIPLIER,
        )
    except ImportError:
        # 기본 딜레이 프리셋
        DELAYS = {
            "page_load": (1.5, 2.5),
            "element_appear": (0.5, 1.0),
            "before_click": (0.3, 0.7),
            "after_click": (0.5, 1.2),
            "before_type": (0.3, 0.6),
            "between_fields": (0.8, 1.5),
            "popup_react": (0.8, 1.5),
            "popup_close": (0.3, 0.6),
            "publish_wait": (1.0, 2.0),
            "layer_appear": (0.8, 1.2),
            "micro": (0.1, 0.3),
            "short": (0.3, 0.6),
        }
        TYPING = {
            "title_min": 50,
            "title_max": 100,
            "content_min": 40,
            "content_max": 80,
            "line_pause_min": 0.1,
            "line_pause_max": 0.25,
        }
        TIMEOUTS = {
            "element_visible": 800,
            "popup_visible": 800,
            "layer_visible": 3000,
            "button_visible": 500,
            "quick_check": 300,
            "normal_check": 500,
        }
        SAFE_MODE = False
        SAFE_MODE_MULTIPLIER = 1.5

    @classmethod
    async def wait(cls, delay_type: str = "short", multiplier: float = 1.0):
        """
        지정된 타입의 랜덤 딜레이 적용

        Args:
            delay_type: DELAYS에 정의된 딜레이 타입
            multiplier: 딜레이 배수 (1.0 = 기본)
        """
        min_delay, max_delay = cls.DELAYS.get(delay_type, cls.DELAYS["short"])

        # 안전 모드 시 딜레이 증가
        if cls.SAFE_MODE:
            multiplier *= cls.SAFE_MODE_MULTIPLIER

        delay = random.uniform(min_delay, max_delay) * multiplier
        await asyncio.sleep(delay)

    @classmethod
    async def random_wait(cls, min_sec: float, max_sec: float):
        """커스텀 범위의 랜덤 딜레이"""
        multiplier = cls.SAFE_MODE_MULTIPLIER if cls.SAFE_MODE else 1.0
        delay = random.uniform(min_sec, max_sec) * multiplier
        await asyncio.sleep(delay)

    @classmethod
    def get_typing_delay(cls, field_type: str = "content") -> int:
        """타이핑 딜레이 반환 (ms)"""
        if field_type == "title":
            return random.randint(cls.TYPING["title_min"], cls.TYPING["title_max"])
        return random.randint(cls.TYPING["content_min"], cls.TYPING["content_max"])

    @classmethod
    def get_timeout(cls, timeout_type: str = "normal_check") -> int:
        """타임아웃 값 반환 (ms)"""
        return cls.TIMEOUTS.get(timeout_type, 500)


class NaverBlogPoster:
    """네이버 블로그 자동 포스팅 클래스"""

    BLOG_URL = "https://blog.naver.com"
    WRITE_URL_TEMPLATE = "https://blog.naver.com/{naver_id}/postwrite"

    def __init__(self, naver_id: str, session_name: str = None):
        """
        Args:
            naver_id: 네이버 아이디
            session_name: 세션 이름 (기본값: {naver_id}_clipboard)
        """
        self.naver_id = naver_id
        self.session_name = session_name or f"{naver_id}_clipboard"
        self.session_manager = SecureSessionManager()
        self.clipboard_helper = ClipboardInputHelper()

        self.browser = None
        self.context = None
        self.page = None

        # 플랫폼 감지 (Linux/macOS 키보드 단축키 구분용)
        self.is_linux = platform.system() == "Linux"
        self.select_all_key = "Control+A" if self.is_linux else "Meta+A"
        logger.info(f"플랫폼: {platform.system()}, 전체선택 키: {self.select_all_key}")

    async def start_browser(self):
        """브라우저 시작 및 세션 로드"""
        logger.info("브라우저 시작 중...")

        # 세션 로드
        storage_state = self.session_manager.load_session(self.session_name)
        if not storage_state:
            raise Exception(f"세션을 찾을 수 없습니다: {self.session_name}")

        self._playwright = await async_playwright().start()

        logger.info(f"Headless 모드: {HEADLESS_MODE}")
        self.browser = await self._playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-setuid-sandbox",
            ],
        )

        # 저장된 세션으로 컨텍스트 생성
        self.context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )

        # 봇 탐지 우회
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self.page = await self.context.new_page()
        logger.success("브라우저 시작 완료 (세션 로드됨)")

    async def close_browser(self):
        """브라우저 종료"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("브라우저 종료")

    async def check_login_status(self) -> bool:
        """로그인 상태 확인"""
        logger.info("로그인 상태 확인 중...")

        await self.page.goto(self.BLOG_URL)
        await asyncio.sleep(3)

        # 로그인 상태 확인 (여러 방법)
        try:
            # 1. 내 블로그 링크 확인
            my_blog = await self.page.locator(f'a[href*="{self.naver_id}"]').count()
            if my_blog > 0:
                logger.success("✅ 로그인 상태 확인됨 (내 블로그 링크)")
                return True

            # 2. 프로필 영역 확인
            profile = await self.page.locator(".MyView, .profile_area, .gnb_my").count()
            if profile > 0:
                logger.success("✅ 로그인 상태 확인됨 (프로필)")
                return True

            # 3. 글쓰기 버튼 확인
            write_btn = await self.page.locator(
                'a[href*="postwrite"], button:has-text("글쓰기")'
            ).count()
            if write_btn > 0:
                logger.success("✅ 로그인 상태 확인됨 (글쓰기 버튼)")
                return True

            # 4. 로그인 버튼이 없으면 로그인된 상태
            login_btn = await self.page.locator(
                'a:has-text("로그인"), button:has-text("로그인")'
            ).count()
            if login_btn == 0:
                logger.success("✅ 로그인 상태 확인됨 (로그인 버튼 없음)")
                return True

        except Exception as e:
            logger.warning(f"로그인 확인 중 오류: {e}")

        logger.warning("로그인되지 않은 상태")
        return False

    async def navigate_to_write_page(self):
        """글쓰기 페이지로 이동"""
        logger.info("글쓰기 페이지로 이동 중...")

        write_url = self.WRITE_URL_TEMPLATE.format(naver_id=self.naver_id)
        await self.page.goto(write_url, wait_until="domcontentloaded")
        await HumanDelay.wait("page_load")

        # 에디터 로드 대기 (팝업보다 먼저!)
        await self._wait_for_editor()

        # ★ 중요: 팝업은 에디터 로드 후에 나타남 - 여기서 처리
        await asyncio.sleep(2)  # 팝업이 나타날 시간 확보

        # 팝업이 있는지 확인
        has_popup = await self._check_and_handle_popup()

        if has_popup:
            # ★★★ 핵심 수정: 팝업 처리 후 페이지 새로고침
            # "취소" 클릭 후 에디터가 리셋되므로, 새로고침해서 깨끗한 상태로 시작
            logger.info("팝업 처리 후 페이지 새로고침...")
            await asyncio.sleep(1)
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # 새로고침 후 다시 팝업 확인 (보통 없음)
            await self._check_and_handle_popup()
            await asyncio.sleep(2)

        # ★ 에디터 상태 확인 및 강제 활성화
        await self._ensure_editor_active()

        # 제목 영역이 정상적으로 렌더링되었는지 확인
        is_ready = await self._verify_editor_ready()
        if not is_ready:
            logger.warning("에디터가 준비되지 않음, 재시도...")
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(3)
            await self._ensure_editor_active()

        logger.success("글쓰기 페이지 준비 완료")

    async def _check_and_handle_popup(self) -> bool:
        """팝업 확인 및 처리, 팝업이 있었으면 True 반환"""
        try:
            result = await self.page.evaluate("""
                () => {
                    // 취소 버튼 찾기
                    const cancelBtn = document.querySelector('.se-popup-button-cancel') ||
                        Array.from(document.querySelectorAll('button')).find(b => 
                            b.textContent && b.textContent.includes('취소')
                        );
                    
                    if (cancelBtn && cancelBtn.offsetParent !== null) {
                        cancelBtn.click();
                        return { found: true, action: 'cancel_clicked' };
                    }
                    
                    // 오버레이만 있는 경우 숨김
                    const overlay = document.querySelector('.se-popup-dim, .se-popup-dim-white');
                    if (overlay && overlay.offsetParent !== null) {
                        overlay.style.display = 'none';
                        return { found: true, action: 'overlay_hidden' };
                    }
                    
                    return { found: false };
                }
            """)

            if result.get("found"):
                logger.info(f"팝업 처리됨: {result.get('action')}")
                return True
            else:
                logger.info("팝업 없음")
                return False

        except Exception as e:
            logger.debug(f"팝업 확인 중 오류: {e}")
            return False

    async def _verify_editor_ready(self) -> bool:
        """에디터가 정상적으로 렌더링되었는지 확인"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const titleP = document.querySelector('.se-section-documentTitle p');
                    if (!titleP) return { ready: false, reason: 'no_element' };
                    
                    const rect = titleP.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) {
                        return { ready: false, reason: 'zero_size', rect: rect };
                    }
                    
                    if (titleP.offsetParent === null) {
                        return { ready: false, reason: 'no_offset_parent' };
                    }
                    
                    return { ready: true, rect: { w: rect.width, h: rect.height } };
                }
            """)

            if result.get("ready"):
                logger.info(f"에디터 준비 완료: {result.get('rect')}")
                return True
            else:
                logger.warning(f"에디터 준비 안됨: {result.get('reason')}")
                return False

        except Exception as e:
            logger.warning(f"에디터 확인 중 오류: {e}")
            return False

    async def _handle_popups(self):
        """팝업창 처리 - JavaScript 직접 조작 방식 (가장 안정적)"""
        logger.info("팝업 확인 및 처리 중...")

        # ═══════════════════════════════════════════════════════════════════
        # 핵심 전략: Playwright의 is_visible()보다 JavaScript 직접 조작이 더 안정적
        # 팝업 오버레이가 클릭을 가로채는 문제를 JavaScript로 우회
        # ═══════════════════════════════════════════════════════════════════

        # 최대 10초 동안 팝업 처리 시도 (5회 x 2초)
        for attempt in range(5):
            try:
                # JavaScript로 팝업 상태 확인 및 처리
                result = await self.page.evaluate("""
                    () => {
                        const result = {
                            overlayFound: false,
                            popupText: '',
                            buttonClicked: false,
                            buttonType: '',
                            overlayHidden: false
                        };

                        // 1. 팝업 오버레이 확인
                        const overlay = document.querySelector('.se-popup-dim, .se-popup-dim-white');
                        if (!overlay) {
                            return result;
                        }

                        // offsetParent로 실제 표시 여부 확인
                        if (overlay.offsetParent === null && getComputedStyle(overlay).display === 'none') {
                            return result;
                        }

                        result.overlayFound = true;

                        // 2. 팝업 내용 확인
                        const popup = document.querySelector('.se-popup-content, .se-popup');
                        result.popupText = popup ? popup.innerText.substring(0, 100) : '';

                        // 3. 버튼 찾기 (우선순위: 취소 > 닫기 > 확인)
                        const buttons = Array.from(document.querySelectorAll('button'));

                        // 취소 버튼 우선 (작성 중인 글 팝업)
                        let cancelBtn = document.querySelector('.se-popup-button-cancel');
                        if (!cancelBtn) {
                            cancelBtn = buttons.find(b => {
                                const text = b.textContent || '';
                                return text.includes('취소');
                            });
                        }

                        if (cancelBtn) {
                            cancelBtn.click();
                            result.buttonClicked = true;
                            result.buttonType = 'cancel';
                            return result;
                        }

                        // 닫기 버튼
                        const closeBtn = buttons.find(b => {
                            const text = b.textContent || '';
                            return text.includes('닫기');
                        });

                        if (closeBtn) {
                            closeBtn.click();
                            result.buttonClicked = true;
                            result.buttonType = 'close';
                            return result;
                        }

                        // 버튼을 못 찾으면 오버레이 강제 숨김
                        overlay.style.display = 'none';
                        result.overlayHidden = true;

                        // 팝업 전체도 숨김
                        const popupEl = overlay.closest('.se-popup');
                        if (popupEl) {
                            popupEl.style.display = 'none';
                        }

                        return result;
                    }
                """)

                if result.get("buttonClicked"):
                    logger.success(
                        f"✅ 팝업 처리 완료 (버튼: {result.get('buttonType')}, 시도 {attempt + 1}/5)"
                    )
                    logger.debug(f"   팝업 내용: {result.get('popupText', '')[:50]}")
                    await asyncio.sleep(1)  # 팝업 닫힘 애니메이션 대기
                    continue  # 추가 팝업 확인을 위해 계속

                if result.get("overlayHidden"):
                    logger.warning(f"⚠️ 팝업 오버레이 강제 숨김 (시도 {attempt + 1}/5)")
                    await asyncio.sleep(0.5)
                    continue

                if not result.get("overlayFound"):
                    # 팝업 없음 - 성공
                    if attempt == 0:
                        logger.info("팝업 없음")
                    break

            except Exception as e:
                logger.debug(f"팝업 처리 중 오류 (시도 {attempt + 1}/5): {e}")

            await asyncio.sleep(0.5)

        # ═══════════════════════════════════════════════════════════════════
        # 추가: 도움말 패널 및 기타 팝업 처리
        # ═══════════════════════════════════════════════════════════════════
        try:
            help_closed = await self.page.evaluate("""
                () => {
                    let closed = 0;

                    // 도움말 패널 닫기 버튼 (여러 셀렉터 시도)
                    const helpCloseSelectors = [
                        'button.se-help-panel-close-button',
                        '.se-help-panel-close-button',
                        '[class*="help"] button[class*="close"]',
                        '.container__HW_tc button',
                        '[class*="container__HW"] button'
                    ];

                    for (const selector of helpCloseSelectors) {
                        const btn = document.querySelector(selector);
                        if (btn && btn.offsetParent !== null) {
                            btn.click();
                            closed++;
                            break;
                        }
                    }

                    // 도움말 컨테이너 강제 숨김
                    const helpContainers = document.querySelectorAll('[class*="container__HW"], .se-help-panel, [class*="help-panel"]');
                    helpContainers.forEach(el => {
                        if (el.offsetParent !== null) {
                            el.style.display = 'none';
                            closed++;
                        }
                    });

                    // 남은 팝업 버튼들 처리
                    const popupButtons = document.querySelectorAll('.se-popup-button-cancel, .se-popup-close');
                    popupButtons.forEach(btn => {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            closed++;
                        }
                    });

                    return closed;
                }
            """)

            if help_closed > 0:
                logger.info(f"도움말/팝업 {help_closed}개 닫음")

        except:
            pass

        # ═══════════════════════════════════════════════════════════════════
        # 최종 확인: 남은 오버레이 강제 제거
        # ═══════════════════════════════════════════════════════════════════
        try:
            cleanup_result = await self.page.evaluate("""
                () => {
                    let cleaned = 0;
                    const overlays = document.querySelectorAll('.se-popup-dim, .se-popup-dim-white');
                    overlays.forEach(overlay => {
                        if (overlay.offsetParent !== null || getComputedStyle(overlay).display !== 'none') {
                            overlay.style.display = 'none';
                            cleaned++;
                        }
                    });

                    // se-popup 전체 숨기기
                    const popups = document.querySelectorAll('.se-popup');
                    popups.forEach(popup => {
                        const display = getComputedStyle(popup).display;
                        if (display !== 'none') {
                            popup.style.display = 'none';
                            cleaned++;
                        }
                    });

                    return cleaned;
                }
            """)

            if cleanup_result > 0:
                logger.warning(f"⚠️ 남은 팝업 {cleanup_result}개 강제 숨김")

        except:
            pass

        logger.info("팝업 처리 완료")

    async def _wait_for_editor(self):
        """에디터 로드 대기"""
        logger.info("에디터 로드 대기 중...")

        editor_selectors = [
            ".se-component-content",
            '[contenteditable="true"]',
            ".se-text-paragraph",
            'iframe[id*="editor"]',
        ]

        for selector in editor_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=10000)
                logger.info(f"에디터 발견: {selector}")
                return
            except:
                continue

        logger.warning("에디터를 찾지 못했지만 계속 진행")

    async def _ensure_editor_active(self):
        """에디터가 활성화되었는지 확인하고 강제 활성화"""
        try:
            # 모든 부모 요소의 display/visibility 강제 설정
            await self.page.evaluate("""
                () => {
                    // 제목 영역 부모 체인 모두 표시
                    const titleSection = document.querySelector('.se-section-documentTitle');
                    if (titleSection) {
                        let current = titleSection;
                        while (current && current !== document.body) {
                            current.style.display = '';
                            current.style.visibility = 'visible';
                            current.style.opacity = '1';
                            current.style.pointerEvents = 'auto';
                            current = current.parentElement;
                        }
                    }
                    
                    // 에디터 컨테이너 활성화
                    const editor = document.querySelector('.se-component-content');
                    if (editor) {
                        editor.style.pointerEvents = 'auto';
                    }
                    
                    // 남은 오버레이 완전 제거
                    const overlays = document.querySelectorAll('.se-popup-dim, .se-popup-dim-white, .se-popup');
                    overlays.forEach(el => {
                        el.style.display = 'none';
                        el.remove();  // DOM에서 완전 제거
                    });
                }
            """)
            logger.info("에디터 강제 활성화 완료")
        except Exception as e:
            logger.debug(f"에디터 활성화 중 오류: {e}")

    async def input_title(self, title: str):
        """
        제목 입력 - 클릭 + 키보드 타이핑 방식 (가장 안정적)

        네이버 에디터는 단순한 DOM 조작(textContent)으로는 내부 상태를 업데이트하지 않음.
        반드시 실제 클릭 + 키보드 입력이 필요함.
        """
        logger.info(f"제목 입력 중: {title[:30]}...")

        # ★★★ 방법 1: bounding_box 클릭 후 키보드 타이핑 (기본) ★★★
        try:
            title_section = await self.page.query_selector(".se-section-documentTitle")
            if title_section:
                box = await title_section.bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    click_x = box["x"] + box["width"] / 2
                    click_y = box["y"] + box["height"] / 2

                    logger.info(f"제목 영역 클릭: ({click_x:.0f}, {click_y:.0f})")
                    await self.page.mouse.click(click_x, click_y)
                    await asyncio.sleep(0.5)

                    # 기존 내용 삭제 후 타이핑
                    await self.page.keyboard.press(self.select_all_key)
                    await asyncio.sleep(0.1)
                    await self.page.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)

                    # 제목 타이핑
                    await self.page.keyboard.type(
                        title, delay=HumanDelay.get_typing_delay("title")
                    )
                    await asyncio.sleep(0.3)

                    # 입력 확인
                    if await self._verify_title_input(title):
                        logger.success(f"✅ 제목 입력 완료: {title[:30]}...")
                        return
                    else:
                        logger.warning("제목 입력 확인 실패, 다른 방법 시도")
        except Exception as e:
            logger.warning(f"bounding_box 클릭 실패: {e}")

        # ★★★ 방법 2: force click + 타이핑 ★★★
        logger.info("방법 2: force click 시도")
        try:
            title_el = self.page.locator(".se-section-documentTitle p").first
            await title_el.click(force=True, timeout=3000)
            await asyncio.sleep(0.5)

            await self.page.keyboard.press(self.select_all_key)
            await asyncio.sleep(0.1)
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)

            await self.page.keyboard.type(
                title, delay=HumanDelay.get_typing_delay("title")
            )
            await asyncio.sleep(0.3)

            if await self._verify_title_input(title):
                logger.success(f"✅ 제목 입력 완료 (force click): {title[:30]}...")
                return
            else:
                logger.warning("force click 후 제목 확인 실패")
        except Exception as e:
            logger.warning(f"force click 실패: {e}")

        # ★★★ 방법 3: JavaScript focus + dispatchEvent + 타이핑 ★★★
        logger.info("방법 3: JavaScript focus 시도")
        try:
            # JavaScript로 포커스 강제 설정
            await self.page.evaluate("""
                () => {
                    const el = document.querySelector('.se-section-documentTitle p') ||
                               document.querySelector('.se-section-documentTitle .se-text-paragraph');
                    if (el) {
                        el.focus();
                        el.click();
                        // Selection을 끝으로 이동
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        range.collapse(false);
                        const sel = window.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                }
            """)
            await asyncio.sleep(0.3)

            # 전체 선택 후 삭제
            await self.page.keyboard.press(self.select_all_key)
            await asyncio.sleep(0.1)
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)

            # 타이핑
            await self.page.keyboard.type(
                title, delay=HumanDelay.get_typing_delay("title")
            )
            await asyncio.sleep(0.3)

            if await self._verify_title_input(title):
                logger.success(f"✅ 제목 입력 완료 (JS focus): {title[:30]}...")
                return
        except Exception as e:
            logger.warning(f"JS focus 실패: {e}")

        # ★★★ 방법 4: Tab 키로 이동 후 타이핑 ★★★
        logger.info("방법 4: Tab 키 이동 시도")
        try:
            # 페이지 시작으로 이동
            await self.page.keyboard.press("Home")
            await asyncio.sleep(0.2)

            # Tab으로 제목 영역으로 이동
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.3)

            await self.page.keyboard.type(
                title, delay=HumanDelay.get_typing_delay("title")
            )
            await asyncio.sleep(0.3)

            if await self._verify_title_input(title):
                logger.success(f"✅ 제목 입력 완료 (Tab): {title[:30]}...")
                return
        except Exception as e:
            logger.warning(f"Tab 방식 실패: {e}")

        # 최종 검증
        if await self._verify_title_input(title):
            logger.success(f"✅ 제목 입력 완료: {title[:30]}...")
        else:
            logger.error("❌ 제목 입력 실패: 모든 방법 시도 완료")

    async def _verify_title_input(self, expected_title: str) -> bool:
        """제목이 실제로 입력되었는지 확인"""
        try:
            actual_title = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('.se-section-documentTitle p') ||
                               document.querySelector('.se-section-documentTitle .se-text-paragraph');
                    if (!el) return '';
                    return el.textContent || el.innerText || '';
                }
            """)

            if not actual_title:
                logger.debug("제목 요소에서 텍스트를 찾을 수 없음")
                return False

            actual_title = actual_title.strip()

            # 기본 플레이스홀더 "제목" 체크
            if actual_title == "제목" or actual_title == "":
                logger.debug(f"제목이 입력되지 않음 (현재: '{actual_title}')")
                return False

            # 입력한 제목의 일부가 포함되어 있는지 확인
            if expected_title[:10] in actual_title:
                logger.debug(f"제목 입력 확인됨: {actual_title[:30]}...")
                return True

            logger.debug(f"제목 불일치 - 기대: {expected_title[:20]}, 실제: {actual_title[:20]}")
            return False

        except Exception as e:
            logger.debug(f"제목 확인 중 오류: {e}")
            return False

    async def _clear_text_formatting(self):
        """텍스트 서식 완전 초기화 (취소선, 굵게, 기울임 등 모두 해제)"""
        logger.info("🔧 텍스트 서식 초기화 시작...")

        try:
            # ★★★ 방법 0: 정확한 셀렉터로 취소선 버튼 직접 찾아서 강제 해제 (2025-12-26 업데이트) ★★★
            # 네이버 스마트에디터 ONE 취소선 버튼 구조:
            # <button class="se-strikethrough-toolbar-button se-property-toolbar-toggle-button __se-sentry"
            #         data-name="strikethrough" data-type="toggle" ...>
            strikethrough_cleared = await self.page.evaluate("""
                () => {
                    // 정확한 셀렉터로 취소선 버튼 찾기 (우선순위 순)
                    const selectors = [
                        'button.se-strikethrough-toolbar-button',
                        'button[data-name="strikethrough"]',
                        '.se-strikethrough-toolbar-button'
                    ];

                    let strikeBtn = null;
                    for (const sel of selectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            strikeBtn = btn;
                            break;
                        }
                    }

                    if (strikeBtn) {
                        // ★★★ 핵심: 'se-is-selected' 클래스로 활성화 상태 확인 ★★★
                        const isActive = strikeBtn.classList.contains('se-is-selected');

                        if (isActive) {
                            console.log('[_clear_text_formatting] 취소선 버튼 해제 (se-is-selected)');
                            strikeBtn.click();
                            return true;
                        }
                    }

                    // 폴백: se-is-selected 클래스가 있는 모든 서식 버튼 해제
                    const toolbar = document.querySelector('.se-toolbar, .se-header-inbox');
                    if (!toolbar) return false;

                    const activeButtons = toolbar.querySelectorAll('button.se-is-selected');
                    activeButtons.forEach(btn => {
                        console.log('활성 서식 버튼 해제 (se-is-selected):', btn.getAttribute('data-name'));
                        btn.click();
                    });

                    return activeButtons.length > 0;
                }
            """)

            if strikethrough_cleared:
                logger.info("✅ 취소선/서식 버튼 강제 해제됨")
                await asyncio.sleep(0.3)

            # 방법 1: Escape 키로 현재 선택/서식 모드 해제
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.2)

            # 방법 3: JavaScript로 모든 서식 버튼 상태 확인 및 해제
            formatting_cleared = await self.page.evaluate("""
                () => {
                    let clearedCount = 0;
                    const toolbar = document.querySelector('.se-toolbar');
                    if (!toolbar) {
                        console.log('툴바를 찾을 수 없음');
                        return clearedCount;
                    }

                    // 해제할 서식 버튼들 (취소선, 굵게, 기울임, 밑줄 등)
                    const formattingButtons = [
                        'strikethrough', 'strike',  // 취소선
                        'bold', 'strong',            // 굵게
                        'italic', 'em',              // 기울임
                        'underline',                 // 밑줄
                    ];

                    const allButtons = toolbar.querySelectorAll('button');

                    allButtons.forEach(btn => {
                        const classList = (btn.className || '').toLowerCase();
                        const dataName = (btn.getAttribute('data-name') || '').toLowerCase();
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        const title = (btn.getAttribute('title') || '').toLowerCase();
                        const ariaPressed = btn.getAttribute('aria-pressed');

                        // 서식 버튼인지 확인
                        let isFormattingButton = formattingButtons.some(fmt =>
                            dataName.includes(fmt) ||
                            classList.includes(fmt) ||
                            ariaLabel.includes(fmt) ||
                            title.includes(fmt) ||
                            ariaLabel.includes('취소선') ||
                            title.includes('취소선')
                        );

                        if (!isFormattingButton) return;

                        // 활성화 상태 확인 (여러 방법)
                        let isActive = false;

                        // 1. aria-pressed 확인
                        if (ariaPressed === 'true') isActive = true;

                        // 2. 클래스에 active 포함
                        if (classList.includes('active')) isActive = true;
                        if (classList.includes('pressed')) isActive = true;
                        if (classList.includes('selected')) isActive = true;
                        if (classList.includes('on')) isActive = true;

                        // 3. 부모 요소가 active 상태인지
                        const parent = btn.closest('[class*="active"], [class*="pressed"], [class*="selected"]');
                        if (parent) isActive = true;

                        // 4. SVG 아이콘의 fill 색상으로 확인 (네이버 에디터 특성)
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            const fill = window.getComputedStyle(svg).fill;
                            // 활성화 시 보통 파란색 계열
                            if (fill && (fill.includes('rgb(0, 199, 60)') || fill.includes('rgb(0, 168, 255)'))) {
                                isActive = true;
                            }
                        }

                        // 5. data-log-action 등 네이버 특수 속성 확인
                        const btnState = btn.getAttribute('data-log-state') || btn.getAttribute('data-state');
                        if (btnState === 'active' || btnState === 'on') isActive = true;

                        // 활성화된 서식 버튼 클릭하여 해제
                        if (isActive) {
                            console.log('서식 버튼 해제:', dataName || ariaLabel || title, btn);
                            btn.click();
                            clearedCount++;
                        }
                    });

                    return clearedCount;
                }
            """)

            if formatting_cleared > 0:
                logger.info(f"✅ {formatting_cleared}개의 서식 버튼 해제됨")
                await asyncio.sleep(0.5)

            # 방법 4: 특정 취소선 버튼 직접 검색 (정확한 셀렉터 2025-12-26 업데이트)
            strikethrough_selectors = [
                "button.se-strikethrough-toolbar-button",  # 가장 정확한 클래스
                'button[data-name="strikethrough"]',
                ".se-strikethrough-toolbar-button",
                'button[data-name="strike"]',
                'button[aria-label*="취소선"]',
                'button[title*="취소선"]',
            ]

            for selector in strikethrough_selectors:
                try:
                    # 버튼 또는 버튼 부모 찾기
                    if "svg" in selector:
                        el = self.page.locator(selector).first
                        if await el.is_visible(timeout=300):
                            btn = await el.evaluate('el => el.closest("button")')
                            if btn:
                                # 상태 확인 후 클릭
                                is_active = await self.page.evaluate(
                                    """
                                    btn => {
                                        if (!btn) return false;
                                        const cls = btn.className || '';
                                        const pressed = btn.getAttribute('aria-pressed');
                                        return cls.includes('active') || pressed === 'true';
                                    }
                                """,
                                    btn,
                                )
                                if is_active:
                                    await self.page.evaluate("btn => btn.click()", btn)
                                    logger.info(f"✅ 취소선 버튼 직접 해제: {selector}")
                    else:
                        btn = self.page.locator(selector).first
                        if await btn.is_visible(timeout=300):
                            is_active = await btn.evaluate("""
                                btn => {
                                    const cls = btn.className || '';
                                    const pressed = btn.getAttribute('aria-pressed');
                                    return cls.includes('active') || pressed === 'true';
                                }
                            """)
                            if is_active:
                                await btn.click()
                                logger.info(f"✅ 취소선 버튼 직접 해제: {selector}")
                                await asyncio.sleep(0.3)
                except:
                    continue

            # 방법 5: 에디터 영역의 <s>, <strike>, <del> 태그 직접 제거
            await self.page.evaluate("""
                () => {
                    const editor = document.querySelector('.se-component-content[contenteditable="true"]') ||
                                   document.querySelector('[contenteditable="true"]');
                    if (!editor) return;

                    // 취소선 태그들을 텍스트로 변환
                    const strikeTags = editor.querySelectorAll('s, strike, del, span[style*="line-through"]');
                    strikeTags.forEach(tag => {
                        const text = document.createTextNode(tag.textContent);
                        tag.parentNode.replaceChild(text, tag);
                    });
                }
            """)

            logger.success("🔧 텍스트 서식 초기화 완료")

        except Exception as e:
            logger.warning(f"서식 초기화 중 오류 (계속 진행): {e}")

    # ========== 마크다운 서식 적용 헬퍼 메서드들 ==========

    async def _apply_heading_format(self, text: str, level: int = 2):
        """
        소제목(H2/H3) 서식 적용

        Args:
            text: 소제목 텍스트 (## 마커 제거된 상태)
            level: 제목 레벨 (2=H2, 3=H3)
        """
        try:
            # 1. 텍스트 입력
            await self.page.keyboard.type(
                text.strip(), delay=HumanDelay.get_typing_delay("content")
            )
            await asyncio.sleep(0.2)

            # 2. 방금 입력한 텍스트 전체 선택 (Shift+Home)
            await self.page.keyboard.press("Shift+Home")
            await asyncio.sleep(0.2)

            # 3. 제목 서식 버튼 클릭 (text-format 드롭다운)
            heading_applied = await self.page.evaluate(f"""
                () => {{
                    // 제목 서식 드롭다운 버튼 찾기
                    const formatBtn = document.querySelector('button[data-name="text-format"]') ||
                                     document.querySelector('.se-text-format-toolbar-button');
                    if (!formatBtn) {{
                        console.log('제목 서식 버튼을 찾을 수 없음');
                        return false;
                    }}

                    // 드롭다운 열기
                    formatBtn.click();
                    return true;
                }}
            """)

            if heading_applied:
                await asyncio.sleep(0.3)

                # 4. 드롭다운에서 제목2 또는 제목3 선택
                level_text = "제목2" if level == 2 else "제목3"
                await self.page.evaluate(f'''
                    () => {{
                        // 드롭다운 메뉴에서 제목 옵션 찾기
                        const options = document.querySelectorAll('.se-text-format-layer button, .se-popup-layer button');
                        for (const opt of options) {{
                            if (opt.textContent.includes("{level_text}") ||
                                opt.getAttribute('data-value') === 'heading{level}') {{
                                opt.click();
                                console.log('제목 서식 적용: {level_text}');
                                return true;
                            }}
                        }}
                        // 폴백: Escape로 드롭다운 닫기
                        document.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Escape'}}));
                        return false;
                    }}
                ''')
                await asyncio.sleep(0.2)

            # 5. 커서를 줄 끝으로 이동
            await self.page.keyboard.press("End")
            await asyncio.sleep(0.1)

            logger.debug(f"소제목 서식 적용: {text[:20]}...")

        except Exception as e:
            logger.warning(f"소제목 서식 적용 실패 (일반 텍스트로 처리): {e}")
            # 실패 시 일반 텍스트로 입력
            await self.page.keyboard.type(
                text.strip(), delay=HumanDelay.get_typing_delay("content")
            )

    async def _apply_bold_format(self, text: str):
        """
        굵게 (Bold) 서식 적용

        Args:
            text: **굵게** 형식의 텍스트
        """
        import re

        # **텍스트** 패턴 파싱
        pattern = r"\*\*(.+?)\*\*"
        parts = re.split(pattern, text)

        for i, part in enumerate(parts):
            if not part:
                continue

            if i % 2 == 1:  # 홀수 인덱스 = 굵게 처리할 부분
                # Bold 시작
                await self.page.keyboard.press("Meta+KeyB")  # Cmd+B
                await asyncio.sleep(0.1)

                await self.page.keyboard.type(
                    part, delay=HumanDelay.get_typing_delay("content")
                )

                # Bold 종료
                await self.page.keyboard.press("Meta+KeyB")
                await asyncio.sleep(0.1)
            else:  # 일반 텍스트
                await self.page.keyboard.type(
                    part, delay=HumanDelay.get_typing_delay("content")
                )

        logger.debug(f"굵게 서식 적용: {text[:30]}...")

    async def _apply_quote_format(self, text: str):
        """
        인용구 서식 적용

        Args:
            text: 인용구 텍스트 (> 마커 제거된 상태)
        """
        try:
            # 1. 인용구 버튼 클릭
            quote_applied = await self.page.evaluate("""
                () => {
                    const quoteBtn = document.querySelector('button[data-name="quotation"]') ||
                                    document.querySelector('.se-quotation-toolbar-button');
                    if (quoteBtn) {
                        quoteBtn.click();
                        console.log('인용구 버튼 클릭');
                        return true;
                    }
                    return false;
                }
            """)

            await asyncio.sleep(0.2)

            # 2. 텍스트 입력
            await self.page.keyboard.type(
                text.strip(), delay=HumanDelay.get_typing_delay("content")
            )
            await asyncio.sleep(0.2)

            # 3. 인용구 모드 해제 (Enter 2번 또는 인용구 버튼 다시 클릭)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.1)

            # 인용구 버튼 다시 클릭하여 해제
            await self.page.evaluate("""
                () => {
                    const quoteBtn = document.querySelector('button[data-name="quotation"]') ||
                                    document.querySelector('.se-quotation-toolbar-button');
                    if (quoteBtn && quoteBtn.classList.contains('se-is-selected')) {
                        quoteBtn.click();
                        console.log('인용구 모드 해제');
                    }
                }
            """)

            logger.debug(f"인용구 서식 적용: {text[:30]}...")

        except Exception as e:
            logger.warning(f"인용구 서식 적용 실패 (일반 텍스트로 처리): {e}")
            await self.page.keyboard.type(
                text.strip(), delay=HumanDelay.get_typing_delay("content")
            )

    async def _process_markdown_line(self, line: str) -> bool:
        """
        마크다운 서식이 포함된 줄 처리

        Returns:
            True if markdown was processed, False if plain text
        """
        import re

        line_stripped = line.strip()

        # 1. 소제목 (## 또는 ###)
        if line_stripped.startswith("### "):
            await self._apply_heading_format(line_stripped[4:], level=3)
            return True
        elif line_stripped.startswith("## "):
            await self._apply_heading_format(line_stripped[3:], level=2)
            return True

        # 2. 인용구 (>)
        if line_stripped.startswith("> "):
            await self._apply_quote_format(line_stripped[2:])
            return True

        # 3. 굵게 (**텍스트**)
        if "**" in line_stripped:
            await self._apply_bold_format(line_stripped)
            return True

        return False

    # ========== 본문 입력 메서드 (마크다운 서식 지원) ==========

    async def input_content(self, content: str):
        """본문 입력 - 직접 타이핑 방식 (취소선 버튼 해제 후)"""
        logger.info("본문 입력 중...")

        # 본문 영역 클릭
        content_selectors = [
            ".se-section-text p",
            ".se-section-text .se-text-paragraph",
            ".se-component:not(.se-documentTitle) .se-text-paragraph",
        ]

        clicked = False
        for selector in content_selectors:
            try:
                content_el = self.page.locator(selector).first
                if await content_el.is_visible(timeout=2000):
                    await HumanDelay.wait("between_fields")
                    await content_el.click()
                    clicked = True
                    logger.info(f"본문 영역 클릭: {selector}")
                    break
            except:
                continue

        if not clicked:
            await self.page.keyboard.press("Tab")

        await asyncio.sleep(0.3)

        # ★★★ 본문 입력 시작 전에 모든 서식 버튼 해제 (가장 중요!)
        logger.info("🔧 본문 입력 시작 전 서식 초기화...")
        await self._disable_all_formatting_buttons()
        await asyncio.sleep(0.3)

        # ★★★ 한 번 더 확인 (중요!)
        await self._force_click_strikethrough_off()
        await asyncio.sleep(0.3)

        # ★ 마크다운 서식 지원 타이핑 방식
        logger.info("마크다운 서식 지원 본문 입력 시작...")
        lines = content.split("\n")
        markdown_count = 0

        for i, line in enumerate(lines):
            if line.strip():
                # 마크다운 서식 처리 시도
                is_markdown = await self._process_markdown_line(line)

                if is_markdown:
                    markdown_count += 1
                    logger.debug(f"줄 {i + 1}/{len(lines)} 마크다운 서식 적용")
                else:
                    # 일반 텍스트 타이핑
                    await self.page.keyboard.type(
                        line, delay=HumanDelay.get_typing_delay("content")
                    )
                    logger.debug(f"줄 {i + 1}/{len(lines)} 일반 텍스트 입력")

            if i < len(lines) - 1:
                await self.page.keyboard.press("Enter")

            # 줄 간 짧은 휴식
            await HumanDelay.random_wait(0.1, 0.2)

        if markdown_count > 0:
            logger.success(f"본문 입력 완료 (마크다운 서식 {markdown_count}개 적용)")
        else:
            logger.success("본문 입력 완료")

    async def publish_post(self, title: str = "") -> str:
        """
        포스트 발행 - 인간 행동 패턴 적용

        Args:
            title: 발행할 글의 제목 (검증용)

        Returns:
            발행된 글의 URL
        """
        self._current_title = title  # 검증용으로 저장
        logger.info("포스트 발행 중...")

        # ★★★ 발행 전 취소선 완전 제거 ★★★
        logger.info("🔧 발행 전 취소선 제거 시작...")
        try:
            # 1. 본문 영역 클릭하여 포커스
            content_el = self.page.locator(
                '.se-section-text p, [contenteditable="true"]'
            ).first
            if await content_el.is_visible(timeout=1000):
                await content_el.click()
                await asyncio.sleep(0.3)

            # 2. 전체 선택 (Cmd+A)
            await self.page.keyboard.press("Meta+KeyA")
            await asyncio.sleep(0.3)
            logger.info("전체 텍스트 선택됨")

            # 3. 취소선 버튼 찾아서 해제 (정확한 셀렉터 2025-12-26 업데이트)
            strike_cleared = await self.page.evaluate("""
                () => {
                    // 정확한 셀렉터로 취소선 버튼 찾기
                    const selectors = [
                        'button.se-strikethrough-toolbar-button',
                        'button[data-name="strikethrough"]',
                        '.se-strikethrough-toolbar-button'
                    ];

                    let strikeBtn = null;
                    for (const sel of selectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            strikeBtn = btn;
                            break;
                        }
                    }

                    if (strikeBtn) {
                        // ★★★ 핵심: 'se-is-selected' 클래스로 활성화 상태 확인 ★★★
                        const isActive = strikeBtn.classList.contains('se-is-selected');

                        if (isActive) {
                            strikeBtn.click();
                            console.log('[발행 전] 취소선 버튼 해제 (se-is-selected)');
                            return true;
                        }
                    }

                    // 모든 se-is-selected 서식 버튼 해제
                    const allSelected = document.querySelectorAll('button.se-is-selected');
                    allSelected.forEach(btn => btn.click());
                    return allSelected.length > 0;
                }
            """)

            if strike_cleared:
                logger.info("✅ 발행 전 취소선 버튼 해제됨 (se-is-selected)")
                await asyncio.sleep(0.5)

            # 4. 선택 해제 (Escape)
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            # 5. DOM에서 취소선 태그 직접 제거
            removed_count = await self.page.evaluate("""
                () => {
                    let count = 0;
                    const editor = document.querySelector('[contenteditable="true"]');
                    if (!editor) return count;

                    // s, strike, del 태그 제거
                    const strikeTags = editor.querySelectorAll('s, strike, del');
                    strikeTags.forEach(tag => {
                        const parent = tag.parentNode;
                        while (tag.firstChild) {
                            parent.insertBefore(tag.firstChild, tag);
                        }
                        parent.removeChild(tag);
                        count++;
                    });

                    // line-through 스타일 제거
                    const allElements = editor.querySelectorAll('*');
                    allElements.forEach(el => {
                        if (el.style.textDecoration && el.style.textDecoration.includes('line-through')) {
                            el.style.textDecoration = 'none';
                            count++;
                        }
                        // computed style도 확인
                        const computed = window.getComputedStyle(el);
                        if (computed.textDecoration.includes('line-through')) {
                            el.style.textDecoration = 'none';
                        }
                    });

                    return count;
                }
            """)

            if removed_count > 0:
                logger.info(f"✅ DOM에서 취소선 {removed_count}개 제거됨")

            logger.success("🔧 발행 전 취소선 제거 완료")

        except Exception as e:
            logger.warning(f"발행 전 취소선 제거 중 오류: {e}")

        await asyncio.sleep(0.5)

        # 0단계: 도움말 패널 닫기 + JS로 숨기기
        try:
            await self.page.evaluate("""
                const helpPanels = document.querySelectorAll('[class*="help-panel"], [class*="container__HW"]');
                helpPanels.forEach(el => el.style.display = 'none');
            """)
            help_panel = self.page.locator("button.se-help-panel-close-button").first
            if await help_panel.is_visible(timeout=500):
                await HumanDelay.wait("before_click")
                await help_panel.click()
                logger.info("도움말 패널 닫음")
        except:
            pass

        # 1단계: 상단 발행 버튼 클릭
        publish_selectors = [
            'button[class*="publish_btn"]',
            "button.publish_btn__m9KHH",
            "button.se-publish-button",
        ]

        clicked = False
        for selector in publish_selectors:
            try:
                publish_btn = self.page.locator(selector).first
                if await publish_btn.is_visible(timeout=800):
                    await HumanDelay.wait("before_click")
                    await publish_btn.click()
                    logger.info(f"1단계 - 발행 버튼 클릭: {selector}")
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            logger.warning("발행 버튼을 찾지 못함")

        await HumanDelay.wait("publish_wait")

        # 2단계: 발행 설정 팝업에서 최종 발행 버튼 클릭
        await self._handle_publish_popup()

        # ★★★ 발행 완료 대기 - 더 긴 대기 시간 및 검증 로직 강화 ★★★
        logger.info("발행 완료 대기 중... (최대 30초)")

        published_url = None

        # 1단계: URL 변경 감지 (최대 15초)
        for i in range(15):
            await asyncio.sleep(1)
            current_url = self.page.url
            logger.debug(f"발행 대기 {i+1}초: {current_url[:50]}...")

            # postwrite가 아닌 다른 URL로 이동하면 발행 완료 가능성
            if "postwrite" not in current_url.lower():
                # PostView URL인 경우 성공
                if "PostView" in current_url or "logNo=" in current_url:
                    logger.success(f"✅ 포스트 발행 완료 (URL 확인): {current_url}")
                    published_url = current_url
                    break
                else:
                    logger.info(f"URL 변경 감지: {current_url}")
                    published_url = current_url
                    break

        # 2단계: 발행 성공 시 추가 대기 (서버 처리 완료 보장)
        if published_url:
            logger.info("서버 처리 완료 대기 중 (5초)...")
            await asyncio.sleep(5)

        # 3단계: 실제 게시글 존재 여부 확인
        logger.info("실제 게시글 존재 여부 확인 중...")
        verified_url = await self._verify_post_published()

        if verified_url:
            logger.success(f"✅ 포스트 발행 확인 완료: {verified_url}")
            return verified_url

        # 4단계: URL 변경은 됐지만 확인 실패 시
        if published_url:
            logger.warning(f"⚠️ URL은 변경됐으나 게시글 확인 실패. URL: {published_url}")
            # 임시저장함 확인
            await self._check_temp_saved_posts()
            return published_url

        # 5단계: URL 변경 없이 타임아웃 - 발행 실패 가능성 높음
        logger.error("❌ 발행 실패: URL이 변경되지 않음")

        # ★★★ 디버깅: 발행 실패 시 스크린샷 ★★★
        try:
            import os
            debug_dir = os.environ.get("LOG_DIR", "/app/logs")
            screenshot_path = f"{debug_dir}/publish_failed.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"📸 발행 실패 시점 스크린샷 저장: {screenshot_path}")

            # 현재 페이지 상태 로깅
            current_html = await self.page.evaluate("() => document.body.innerHTML.substring(0, 2000)")
            logger.debug(f"현재 페이지 HTML (일부): {current_html[:500]}...")

            # 보이는 에러 메시지 확인
            error_msgs = await self.page.evaluate("""
                () => {
                    const errors = document.querySelectorAll('[class*="error"], [class*="alert"], [class*="warning"]');
                    return Array.from(errors).map(e => e.innerText).filter(t => t.length > 0).slice(0, 5);
                }
            """)
            if error_msgs:
                logger.warning(f"페이지 내 에러 메시지: {error_msgs}")
        except Exception as e:
            logger.debug(f"디버깅 정보 수집 실패: {e}")

        await self._check_temp_saved_posts()

        # 최신 글 확인 시도 (마지막 시도)
        try:
            await self.page.goto(f"https://blog.naver.com/{self.naver_id}")
            await asyncio.sleep(3)

            latest_post = self.page.locator(
                'a[href*="/PostView.naver"], a[href*="logNo="]'
            ).first
            if await latest_post.is_visible(timeout=5000):
                post_url = await latest_post.get_attribute("href")
                if post_url and not post_url.startswith("http"):
                    post_url = f"https://blog.naver.com{post_url}"
                logger.info(f"최신 글 발견 (미확인): {post_url}")
                return post_url
        except Exception as e:
            logger.warning(f"최신 글 확인 실패: {e}")

        # 발행 실패로 간주
        post_url = f"https://blog.naver.com/{self.naver_id}"
        logger.warning(f"⚠️ 발행 상태 불확실: {post_url}")
        return post_url

    async def _verify_post_published(self) -> str:
        """
        실제로 게시글이 발행되었는지 확인 - 제목으로 새 글인지 검증

        Returns:
            발행된 게시글 URL (성공 시) 또는 None (실패 시)
        """
        expected_title = getattr(self, "_current_title", "")

        try:
            # 블로그 메인으로 이동
            blog_url = f"https://blog.naver.com/{self.naver_id}"
            await self.page.goto(blog_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # 최신 글 목록에서 방금 작성한 글 확인
            latest_links = await self.page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="PostView"], a[href*="logNo="]');
                    const results = [];
                    for (let i = 0; i < Math.min(links.length, 5); i++) {
                        results.push({
                            href: links[i].href,
                            text: links[i].innerText.trim().substring(0, 100)
                        });
                    }
                    return results;
                }
            """)

            if latest_links and len(latest_links) > 0:
                logger.info(f"블로그에서 {len(latest_links)}개의 글 발견")
                for link in latest_links[:3]:
                    logger.debug(f"  - {link.get('text', 'N/A')[:40]}: {link.get('href', 'N/A')[:50]}")

                # ★★★ 제목으로 새 글인지 확인 ★★★
                if expected_title:
                    # 제목의 첫 10자가 포함된 글 찾기
                    title_prefix = expected_title[:10]
                    for link in latest_links:
                        link_text = link.get("text", "")
                        if title_prefix in link_text:
                            logger.success(f"✅ 새 글 발견 (제목 일치): {link_text[:40]}...")
                            return link.get("href")

                    # 제목 일치하는 글이 없으면 실패
                    logger.warning(f"⚠️ 제목 '{title_prefix}...'와 일치하는 글을 찾을 수 없음")
                    logger.warning(f"   최신 글들: {[link.get('text', '')[:30] for link in latest_links[:3]]}")
                    return None
                else:
                    # 제목 정보 없으면 첫 번째 글 반환 (이전 동작)
                    return latest_links[0].get("href")

            # 방법 2: iframe 내 글 목록 확인 (네이버 블로그 구조)
            iframe_content = await self.page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe#mainFrame');
                    if (iframe && iframe.contentDocument) {
                        const links = iframe.contentDocument.querySelectorAll('a[href*="PostView"]');
                        const results = [];
                        for (let i = 0; i < Math.min(links.length, 5); i++) {
                            results.push({
                                href: links[i].href,
                                text: links[i].innerText.trim().substring(0, 100)
                            });
                        }
                        return { found: results.length > 0, links: results };
                    }
                    return { found: false, links: [] };
                }
            """)

            if iframe_content.get("found"):
                iframe_links = iframe_content.get("links", [])
                if expected_title and iframe_links:
                    title_prefix = expected_title[:10]
                    for link in iframe_links:
                        link_text = link.get("text", "")
                        if title_prefix in link_text:
                            logger.success(f"✅ iframe에서 새 글 발견: {link_text[:40]}...")
                            return link.get("href")
                    logger.warning("iframe에서 제목 일치하는 글을 찾을 수 없음")
                    return None
                elif iframe_links:
                    return iframe_links[0].get("href")

            logger.warning("블로그에서 게시글을 찾을 수 없음")
            return None

        except Exception as e:
            logger.warning(f"게시글 확인 중 오류: {e}")
            return None

    async def _check_temp_saved_posts(self):
        """임시저장함 확인 (디버깅용)"""
        try:
            temp_url = f"https://blog.naver.com/{self.naver_id}/postwrite?Redirect=Write"
            await self.page.goto(temp_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # "작성 중인 글이 있습니다" 팝업 확인
            has_temp = await self.page.evaluate("""
                () => {
                    const popup = document.querySelector('.se-popup-content');
                    if (popup && popup.innerText.includes('작성 중인 글')) {
                        return { found: true, text: popup.innerText.substring(0, 100) };
                    }
                    return { found: false };
                }
            """)

            if has_temp.get("found"):
                logger.warning(f"⚠️ 임시저장된 글 발견: {has_temp.get('text', '')[:50]}")
            else:
                logger.info("임시저장함에 글 없음")

        except Exception as e:
            logger.debug(f"임시저장함 확인 실패: {e}")

    async def _handle_publish_popup(self):
        """
        발행 설정 팝업 처리 - 강화된 발행 로직

        네이버 블로그 발행 레이어에서:
        1. 공개 설정 확인 (전체공개)
        2. 최종 발행 버튼 클릭
        3. 발행 완료 확인
        """
        logger.info("발행 설정 레이어 대기 중...")

        # 1단계: 발행 설정 레이어가 나타날 때까지 대기 (더 긴 대기)
        publish_layer_selectors = [
            '[class*="layer_publish"]',
            '[class*="publish_layer"]',
            '[class*="PublishLayer"]',
            '[role="dialog"]',
            '.se-popup',
        ]

        layer_found = False
        for attempt in range(3):  # 3회 시도
            for selector in publish_layer_selectors:
                try:
                    layer = self.page.locator(selector).first
                    await layer.wait_for(state="visible", timeout=2000)
                    logger.info(f"발행 설정 레이어 발견: {selector}")
                    layer_found = True
                    break
                except:
                    continue
            if layer_found:
                break
            await asyncio.sleep(1)

        if not layer_found:
            logger.warning("발행 설정 레이어를 찾지 못함 - JavaScript로 확인")
            # JavaScript로 발행 레이어 상태 확인
            layer_check = await self.page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"], [class*="layer"], [class*="popup"]');
                    for (const d of dialogs) {
                        if (d.offsetParent !== null && d.innerText.includes('발행')) {
                            return { found: true, text: d.innerText.substring(0, 100) };
                        }
                    }
                    return { found: false };
                }
            """)
            if layer_check.get("found"):
                logger.info(f"JS로 발행 레이어 확인: {layer_check.get('text', '')[:50]}")
                layer_found = True

        # 레이어 애니메이션 완료 대기
        await asyncio.sleep(1.5)

        # ★★★ 디버깅: 발행 팝업 스크린샷 ★★★
        try:
            import os
            debug_dir = os.environ.get("LOG_DIR", "/app/logs")
            os.makedirs(debug_dir, exist_ok=True)
            screenshot_path = f"{debug_dir}/publish_popup_before.png"
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"📸 발행 팝업 스크린샷 저장: {screenshot_path}")
        except Exception as e:
            logger.debug(f"스크린샷 저장 실패: {e}")

        # ★★★ 1.5단계: 공개 설정이 '전체공개'인지 확인 ★★★
        try:
            await self.page.evaluate("""
                () => {
                    // '전체공개' 라디오 버튼 또는 옵션 선택
                    const publicOptions = document.querySelectorAll(
                        'input[value="open"], label:has-text("전체공개"), [class*="open"]'
                    );
                    for (const opt of publicOptions) {
                        if (opt.tagName === 'INPUT' && opt.type === 'radio') {
                            opt.checked = true;
                            opt.dispatchEvent(new Event('change', { bubbles: true }));
                        } else if (opt.tagName === 'LABEL' || opt.tagName === 'BUTTON') {
                            opt.click();
                        }
                    }
                }
            """)
            logger.debug("공개 설정 확인됨")
        except Exception as e:
            logger.debug(f"공개 설정 확인 실패 (무시): {e}")

        # 2단계: 최종 발행 버튼 찾기 - 더 많은 셀렉터 추가
        final_publish_selectors = [
            'button[class*="confirm_btn"]',
            'button[class*="confirm"]',
            'button[class*="publish_btn"]',
            '[class*="layer"] button[class*="confirm"]',
            '[role="dialog"] button:has-text("발행")',
            '[class*="layer"] button:has-text("발행")',
            '[class*="popup"] button:has-text("발행")',
            'button.se-popup-button-confirm',
        ]

        clicked = False
        for selector in final_publish_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await btn.click()
                    logger.info(f"2단계 - 최종 발행 버튼 클릭: {selector}")
                    clicked = True
                    await asyncio.sleep(2)  # 발행 처리 대기
                    break
            except:
                continue

        if clicked:
            # ★★★ 디버깅: 발행 버튼 클릭 후 스크린샷 ★★★
            try:
                import os
                debug_dir = os.environ.get("LOG_DIR", "/app/logs")
                screenshot_path = f"{debug_dir}/publish_popup_after_click.png"
                await self.page.screenshot(path=screenshot_path)
                logger.info(f"📸 발행 클릭 후 스크린샷 저장: {screenshot_path}")
            except Exception as e:
                logger.debug(f"스크린샷 저장 실패: {e}")
            return

        # 폴백: 마지막 보이는 "발행" 버튼
        logger.info("최종 발행 버튼 폴백 검색 중...")
        try:
            all_publish_btns = self.page.locator('button:has-text("발행")')
            count = await all_publish_btns.count()

            visible_btns = []
            for i in range(count):
                btn = all_publish_btns.nth(i)
                if await btn.is_visible():
                    visible_btns.append(btn)

            logger.info(f"보이는 '발행' 버튼: {len(visible_btns)}개")

            if len(visible_btns) >= 2:
                final_btn = visible_btns[-1]
                await final_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await final_btn.click()
                logger.info("2단계 - 최종 발행 버튼 클릭 (폴백 - 마지막)")
                await asyncio.sleep(2)
                return
            elif len(visible_btns) == 1:
                await asyncio.sleep(0.5)
                await visible_btns[0].click()
                logger.info("2단계 - 발행 버튼 클릭 (유일한 버튼)")
                await asyncio.sleep(2)
                return

        except Exception as e:
            logger.warning(f"폴백 발행 버튼 검색 실패: {e}")

        # ★★★ 최후의 수단: JavaScript로 모든 발행 버튼 찾아서 클릭 ★★★
        logger.info("JavaScript로 발행 버튼 강제 클릭 시도...")
        try:
            result = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const publishBtns = buttons.filter(btn => {
                        const text = (btn.innerText || btn.textContent || '').trim();
                        const isVisible = btn.offsetParent !== null;
                        const isPublish = text === '발행' || text.includes('발행');
                        // '예약발행' 등은 제외
                        const notScheduled = !text.includes('예약');
                        return isVisible && isPublish && notScheduled;
                    });

                    console.log('발행 버튼 수:', publishBtns.length);

                    if (publishBtns.length >= 2) {
                        // 레이어 내의 버튼 (보통 마지막)
                        publishBtns[publishBtns.length - 1].click();
                        return { clicked: true, index: publishBtns.length - 1 };
                    } else if (publishBtns.length === 1) {
                        publishBtns[0].click();
                        return { clicked: true, index: 0 };
                    }

                    return { clicked: false, count: publishBtns.length };
                }
            """)

            if result.get("clicked"):
                logger.info(f"2단계 - JavaScript로 발행 버튼 클릭 (인덱스: {result.get('index')})")
                await asyncio.sleep(2)
            else:
                logger.error(f"발행 버튼을 찾을 수 없음 (발견된 버튼: {result.get('count')})")

        except Exception as e:
            logger.error(f"JavaScript 발행 클릭 실패: {e}")

    async def insert_image(self, image_path: str):
        """이미지 삽입 - 클립보드 붙여넣기 방식"""
        logger.info(f"📷 이미지 삽입 중: {image_path}")

        from pathlib import Path
        import os
        import subprocess

        # 절대 경로로 변환
        abs_path = str(Path(image_path).resolve())

        # 파일 존재 확인
        if not os.path.exists(abs_path):
            logger.error(f"이미지 파일이 존재하지 않습니다: {abs_path}")
            return False

        try:
            # ★ 클립보드에 이미지 복사 (Mac용 osascript 사용)
            logger.info("클립보드에 이미지 복사 중...")

            # AppleScript로 이미지를 클립보드에 복사
            script = f'''
            set theFile to POSIX file "{abs_path}"
            set the clipboard to (read theFile as «class PNGf»)
            '''

            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )

            if result.returncode != 0:
                # PNG 실패시 JPEG로 시도
                script_jpeg = f'''
                set theFile to POSIX file "{abs_path}"
                set the clipboard to (read theFile as JPEG picture)
                '''
                result = subprocess.run(
                    ["osascript", "-e", script_jpeg], capture_output=True, text=True
                )

            if result.returncode == 0:
                logger.info("✅ 클립보드에 이미지 복사 완료")
            else:
                logger.warning(f"클립보드 복사 실패: {result.stderr}")
                return False

            # 본문 영역 클릭하여 포커스
            content_selectors = [
                ".se-section-text p",
                ".se-section-text .se-text-paragraph",
                '[contenteditable="true"]',
            ]

            for selector in content_selectors:
                try:
                    el = self.page.locator(selector).first
                    if await el.is_visible(timeout=1000):
                        await el.click()
                        logger.info(f"에디터 영역 클릭: {selector}")
                        break
                except:
                    continue

            await asyncio.sleep(0.5)

            # ★ Cmd+V로 이미지 붙여넣기
            await self.page.keyboard.press("Meta+KeyV")
            logger.info("Cmd+V로 이미지 붙여넣기 실행")

            # 이미지 업로드 완료 대기
            await asyncio.sleep(3)

            # 이미지가 에디터에 삽입되었는지 확인
            image_inserted = await self.page.evaluate("""
                () => {
                    const editor = document.querySelector('[contenteditable="true"]');
                    if (!editor) return false;
                    const images = editor.querySelectorAll('img');
                    return images.length > 0;
                }
            """)

            if image_inserted:
                logger.success("📷 이미지 삽입 완료!")
                return True
            else:
                logger.warning("이미지 삽입 확인 실패 (계속 진행)")
                return True

        except Exception as e:
            logger.warning(f"이미지 삽입 실패 (무시하고 계속): {e}")
            return False

    async def post(
        self, title: str, content: str, image_path: str = None, images: list = None
    ) -> dict:
        """
        전체 포스팅 프로세스 실행

        Args:
            title: 글 제목
            content: 글 본문
            image_path: 삽입할 이미지 경로 (단일 이미지, 하위 호환)
            images: 삽입할 이미지 경로 리스트 (다중 이미지)

        Returns:
            {
                "success": bool,       # 발행 성공 여부
                "url": str,            # 발행된 글 URL
                "error": str,          # 에러 메시지
                "verified": bool,      # 실제 게시글 확인 여부
            }
        """
        result = {"success": False, "url": "", "error": "", "verified": False}

        # 이미지 리스트 통합 (하위 호환성 유지)
        image_list = []
        if images:
            image_list = images
        elif image_path:
            image_list = [image_path]

        try:
            # 1. 브라우저 시작
            await self.start_browser()

            # 2. 로그인 상태 확인
            if not await self.check_login_status():
                raise Exception(
                    "로그인이 필요합니다. manual_login_clipboard.py를 먼저 실행하세요."
                )

            # 3. 글쓰기 페이지로 이동
            await self.navigate_to_write_page()

            # 4. 제목 입력
            await self.input_title(title)
            await asyncio.sleep(1)

            # 5. 본문 + 이미지 삽입 (이미지가 있으면 문단 사이에 배치)
            if image_list:
                await self.input_content_with_images(content, image_list)
            else:
                await self.input_content(content)
            await asyncio.sleep(1)

            # 6. 발행 (제목 전달하여 검증에 사용)
            post_url = await self.publish_post(title=title)

            # ★★★ 발행 결과 검증 ★★★
            # URL에 PostView 또는 logNo가 포함되어 있으면 성공
            if post_url and ("PostView" in post_url or "logNo=" in post_url):
                result["success"] = True
                result["verified"] = True
                result["url"] = post_url
                logger.success(f"✅ 포스팅 완료 (검증됨): {post_url}")
            elif post_url and self.naver_id in post_url:
                # URL은 있지만 게시글 확인 안 됨
                result["success"] = True
                result["verified"] = False
                result["url"] = post_url
                logger.warning(f"⚠️ 포스팅 완료 (미검증): {post_url}")
            else:
                # 발행 실패 가능성
                result["success"] = False
                result["error"] = "발행 후 게시글 URL을 확인할 수 없음"
                result["url"] = post_url or ""
                logger.error("❌ 포스팅 실패: 게시글 URL 미확인")

        except Exception as e:
            logger.error(f"포스팅 실패: {e}")
            result["error"] = str(e)

        finally:
            await self.close_browser()

        return result

    async def input_content_with_images(self, content: str, images: list):
        """
        본문과 이미지를 번갈아가며 삽입

        이미지가 본문 중간중간에 자연스럽게 배치됨
        예: 문단1 → 이미지1 → 문단2 → 이미지2 → 문단3 → 이미지3 → 나머지 문단들

        Args:
            content: 전체 본문
            images: 이미지 경로 리스트 (3-4개 권장)
        """
        logger.info(f"📝 본문 + 이미지 {len(images)}개 삽입 시작...")

        # 본문을 문단(빈 줄 기준)으로 분리
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if not paragraphs:
            paragraphs = [content]

        # 이미지 삽입 위치 계산
        # 예: 문단 10개, 이미지 3개 → 문단 3, 6, 9 뒤에 이미지 삽입
        num_images = len(images)
        num_paragraphs = len(paragraphs)

        # 이미지를 균등하게 배치할 위치 계산
        if num_images >= num_paragraphs:
            # 이미지가 문단보다 많으면 모든 문단 뒤에 이미지
            insert_positions = list(range(num_paragraphs))
        else:
            # 균등 배치: 첫 문단 이후부터 시작
            interval = max(1, num_paragraphs // (num_images + 1))
            insert_positions = []
            for i in range(num_images):
                pos = interval * (i + 1) - 1
                if pos < num_paragraphs:
                    insert_positions.append(pos)
                else:
                    insert_positions.append(num_paragraphs - 1)

        logger.info(f"   문단 {num_paragraphs}개, 이미지 삽입 위치: {insert_positions}")

        # 본문 영역 클릭
        content_selectors = [
            ".se-section-text p",
            ".se-section-text .se-text-paragraph",
            ".se-component:not(.se-documentTitle) .se-text-paragraph",
        ]

        clicked = False
        for selector in content_selectors:
            try:
                content_el = self.page.locator(selector).first
                if await content_el.is_visible(timeout=2000):
                    await HumanDelay.wait("between_fields")
                    await content_el.click()
                    clicked = True
                    logger.info(f"본문 영역 클릭: {selector}")
                    break
            except:
                continue

        if not clicked:
            await self.page.keyboard.press("Tab")

        await asyncio.sleep(0.3)

        # ★★★ 본문 입력 시작 전에 모든 서식 버튼 해제 (가장 중요!)
        logger.info("🔧 본문 입력 시작 전 서식 초기화...")
        await self._disable_all_formatting_buttons()
        await asyncio.sleep(0.3)

        # ★★★ 한 번 더 확인 (중요!)
        await self._force_click_strikethrough_off()
        await asyncio.sleep(0.3)

        # 문단과 이미지 번갈아 삽입 (마크다운 서식 지원)
        image_idx = 0
        markdown_count = 0

        for para_idx, paragraph in enumerate(paragraphs):
            # 문단 입력 (마크다운 서식 처리)
            lines = paragraph.split("\n")
            for i, line in enumerate(lines):
                if line.strip():
                    # ★ 마크다운 서식 처리 시도
                    is_markdown = await self._process_markdown_line(line)
                    if is_markdown:
                        markdown_count += 1
                    else:
                        await self.page.keyboard.type(
                            line, delay=HumanDelay.get_typing_delay("content")
                        )
                if i < len(lines) - 1:
                    await self.page.keyboard.press("Enter")
                await HumanDelay.random_wait(0.05, 0.1)

            # 문단 사이 줄바꿈
            await self.page.keyboard.press("Enter")
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.2)

            # 이 문단 뒤에 이미지 삽입할 차례인지 확인
            if image_idx < len(images) and para_idx in insert_positions:
                logger.info(f"   📷 이미지 {image_idx + 1}/{len(images)} 삽입 중...")

                # ★★★ 이미지 삽입 전 커서 위치 저장용 마커 입력
                await self._insert_image_and_move_below(images[image_idx])
                await asyncio.sleep(0.5)

                # ★★★ 이미지 삽입 후 서식 다시 해제 (중요!)
                await self._disable_all_formatting_buttons()
                await asyncio.sleep(0.3)

                image_idx += 1

        # 남은 이미지가 있으면 마지막에 삽입
        while image_idx < len(images):
            logger.info(f"   📷 남은 이미지 {image_idx + 1}/{len(images)} 삽입 중...")
            await self._insert_image_and_move_below(images[image_idx])
            await asyncio.sleep(0.5)
            await self._disable_all_formatting_buttons()
            await asyncio.sleep(0.3)
            image_idx += 1

        if markdown_count > 0:
            logger.success(
                f"✅ 본문 + 이미지 {len(images)}개 삽입 완료 (마크다운 서식 {markdown_count}개 적용)"
            )
        else:
            logger.success(f"✅ 본문 + 이미지 {len(images)}개 삽입 완료")

    async def _disable_all_formatting_buttons(self):
        """모든 서식 버튼 (취소선, 굵게, 기울임 등) 강제 해제 - 완전 재작성"""
        try:
            logger.debug("🔧 서식 해제 시작...")

            # Escape 키로 선택 해제
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.1)

            # 핵심 방법: _force_click_strikethrough_off 호출
            # 이 메서드가 execCommand + 버튼 인덱스 기반 + DOM 정리 모두 수행
            await self._force_click_strikethrough_off()

            logger.debug("🔧 서식 해제 완료")

        except Exception as e:
            logger.warning(f"서식 버튼 해제 중 오류 (계속 진행): {e}")

    async def _force_click_strikethrough_off(self):
        """취소선 버튼 강제 해제 - 정확한 셀렉터 사용 (2025-12-26 업데이트)"""
        try:
            # ═══════════════════════════════════════════════════════════════
            # 방법 0 (최우선): 정확한 클래스/속성 셀렉터로 취소선 버튼 직접 찾기
            # 네이버 스마트에디터 ONE 취소선 버튼 구조:
            # <button class="se-strikethrough-toolbar-button se-property-toolbar-toggle-button __se-sentry"
            #         data-name="strikethrough" data-type="toggle" ...>
            # ═══════════════════════════════════════════════════════════════
            exact_result = await self.page.evaluate("""
                () => {
                    // 정확한 셀렉터 우선순위:
                    // 1. 클래스명으로 직접 찾기 (가장 확실)
                    // 2. data-name으로 찾기
                    // 3. 폴백: 기존 방식

                    const selectors = [
                        'button.se-strikethrough-toolbar-button',
                        'button[data-name="strikethrough"]',
                        '.se-strikethrough-toolbar-button'
                    ];

                    let strikeBtn = null;
                    let usedSelector = '';

                    for (const sel of selectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            strikeBtn = btn;
                            usedSelector = sel;
                            break;
                        }
                    }

                    if (!strikeBtn) {
                        return { found: false, error: '취소선 버튼을 찾을 수 없음' };
                    }

                    // ★★★ 핵심: 네이버 스마트에디터 ONE은 'se-is-selected' 클래스로 활성화 상태 표시 ★★★
                    // 2025-12-26 디버깅으로 확인됨
                    const isActive = strikeBtn.classList.contains('se-is-selected');

                    if (isActive) {
                        strikeBtn.click();
                        console.log('[취소선 해제] se-is-selected 감지, 버튼 클릭:', usedSelector);
                        return { found: true, wasActive: true, clicked: true, selector: usedSelector };
                    }

                    return { found: true, wasActive: false, clicked: false, selector: usedSelector };
                }
            """)

            if exact_result.get("clicked"):
                logger.info(
                    f"✅ 취소선 버튼 해제 완료 (셀렉터: {exact_result.get('selector')})"
                )
                await asyncio.sleep(0.3)
                # 정확한 셀렉터로 성공하면 바로 DOM 정리 후 반환
                await self._remove_strikethrough_from_dom()
                return

            if exact_result.get("found") and not exact_result.get("wasActive"):
                logger.debug("취소선 버튼 발견됨 (비활성 상태)")

            # ═══════════════════════════════════════════════════════════════
            # 방법 1 (폴백): 초록색 SVG 감지로 활성화된 서식 버튼 찾기
            # ═══════════════════════════════════════════════════════════════
            btn_result = await self.page.evaluate("""
                () => {
                    const toolbar = document.querySelector('.se-toolbar');
                    if (!toolbar) return { error: '툴바 없음' };

                    const allButtons = toolbar.querySelectorAll('button');
                    let clicked = false;

                    for (let i = 0; i < allButtons.length; i++) {
                        const btn = allButtons[i];
                        const svg = btn.querySelector('svg');
                        if (!svg) continue;

                        const paths = svg.querySelectorAll('path');
                        for (const path of paths) {
                            const fill = (path.getAttribute('fill') || '').toLowerCase();

                            // 초록색 확인 (활성화 상태)
                            if (fill === '#00c73c' || fill === '#03c75a' ||
                                fill.includes('rgb(0, 199') || fill.includes('rgb(3, 199')) {
                                btn.click();
                                console.log(`[취소선 해제] 버튼 #${i} 클릭 (초록색 감지)`);
                                clicked = true;
                                break;
                            }
                        }
                        if (clicked) break;
                    }

                    return { clicked: clicked };
                }
            """)

            if btn_result.get("clicked"):
                logger.info(
                    f"✅ 취소선 버튼 해제 완료 (index={btn_result.get('index')})"
                )
                await asyncio.sleep(0.3)

            # ═══════════════════════════════════════════════════════════════
            # 방법 2: execCommand로 추가 해제 시도
            # ═══════════════════════════════════════════════════════════════
            exec_result = await self.page.evaluate("""
                () => {
                    try {
                        const isStrikeActive = document.queryCommandState('strikeThrough');
                        if (isStrikeActive) {
                            document.execCommand('strikeThrough', false, null);
                            return { wasActive: true, success: true };
                        }
                        return { wasActive: false, success: true };
                    } catch (e) {
                        return { error: e.message };
                    }
                }
            """)

            if exec_result.get("wasActive"):
                logger.info("✅ execCommand로 취소선 추가 해제")
                await asyncio.sleep(0.2)

            # ═══════════════════════════════════════════════════════════════
            # 방법 3: DOM에서 취소선 태그/스타일 직접 제거
            # ═══════════════════════════════════════════════════════════════
            await self._remove_strikethrough_from_dom()

        except Exception as e:
            logger.warning(f"취소선 강제 해제 중 오류: {e}")

    async def _remove_strikethrough_from_dom(self):
        """DOM에서 취소선 태그와 스타일을 직접 제거"""
        try:
            removed = await self.page.evaluate("""
                () => {
                    let removedCount = 0;

                    // 에디터 영역 찾기
                    const editors = document.querySelectorAll('[contenteditable="true"]');

                    for (const editor of editors) {
                        // 1. <s>, <strike>, <del> 태그를 텍스트로 변환
                        const strikeTags = editor.querySelectorAll('s, strike, del');
                        strikeTags.forEach(tag => {
                            const parent = tag.parentNode;
                            while (tag.firstChild) {
                                parent.insertBefore(tag.firstChild, tag);
                            }
                            parent.removeChild(tag);
                            removedCount++;
                        });

                        // 2. text-decoration: line-through 스타일 제거
                        const allElements = editor.querySelectorAll('*');
                        allElements.forEach(el => {
                            if (el.style && el.style.textDecoration) {
                                if (el.style.textDecoration.includes('line-through')) {
                                    el.style.textDecoration = el.style.textDecoration.replace('line-through', '').trim() || 'none';
                                    removedCount++;
                                }
                            }
                        });

                        // 3. 인라인 스타일에서 text-decoration 속성 제거
                        const styledElements = editor.querySelectorAll('[style*="line-through"]');
                        styledElements.forEach(el => {
                            const style = el.getAttribute('style') || '';
                            const newStyle = style.replace(/text-decoration[^;]*line-through[^;]*/gi, '');
                            if (newStyle.trim()) {
                                el.setAttribute('style', newStyle);
                            } else {
                                el.removeAttribute('style');
                            }
                            removedCount++;
                        });
                    }

                    return { removed: removedCount };
                }
            """)

            if removed.get("removed", 0) > 0:
                logger.info(f"✅ DOM에서 취소선 {removed['removed']}개 제거")

        except Exception as e:
            logger.debug(f"DOM 취소선 제거 중 오류 (무시): {e}")

    async def _insert_image_and_move_below(self, image_path: str):
        """이미지 삽입 후 커서를 이미지 아래로 이동"""
        from pathlib import Path
        import os
        import subprocess

        # 절대 경로로 변환
        abs_path = str(Path(image_path).resolve())

        if not os.path.exists(abs_path):
            logger.error(f"이미지 파일이 존재하지 않습니다: {abs_path}")
            return False

        try:
            # 클립보드에 이미지 복사
            script = f'''
            set theFile to POSIX file "{abs_path}"
            set the clipboard to (read theFile as «class PNGf»)
            '''
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )

            if result.returncode != 0:
                # JPEG로 재시도
                script_jpeg = f'''
                set theFile to POSIX file "{abs_path}"
                set the clipboard to (read theFile as JPEG picture)
                '''
                result = subprocess.run(
                    ["osascript", "-e", script_jpeg], capture_output=True, text=True
                )

            if result.returncode != 0:
                logger.warning(f"클립보드 복사 실패: {result.stderr}")
                return False

            logger.info("✅ 클립보드에 이미지 복사 완료")

            # Cmd+V로 이미지 붙여넣기
            await self.page.keyboard.press("Meta+KeyV")
            logger.info("Cmd+V로 이미지 붙여넣기 실행")

            # 이미지 업로드 완료 대기
            await asyncio.sleep(3)

            # ★★★ 핵심: 이미지 삽입 후 커서를 이미지 아래로 이동
            # 네이버 에디터에서는 이미지가 새 컴포넌트로 삽입되므로,
            # 다음 컴포넌트로 이동해야 함

            # 1. ArrowDown으로 이미지 아래로 이동
            await self.page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)

            # 2. End 키로 줄 끝으로 이동 (혹시 텍스트가 있을 경우)
            await self.page.keyboard.press("End")
            await asyncio.sleep(0.1)

            # 3. 줄바꿈 추가
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.2)

            logger.success("📷 이미지 삽입 및 커서 이동 완료")
            return True

        except Exception as e:
            logger.warning(f"이미지 삽입 실패: {e}")
            return False

    async def _move_cursor_to_end(self):
        """커서를 에디터 맨 끝으로 이동"""
        try:
            # Cmd+End (Mac) 또는 Ctrl+End (Windows)로 문서 끝으로 이동
            await self.page.keyboard.press("Meta+ArrowDown")
            await asyncio.sleep(0.1)

            # JavaScript로도 커서를 끝으로 이동
            await self.page.evaluate("""
                () => {
                    const editor = document.querySelector('.se-component-content[contenteditable="true"]') ||
                                   document.querySelector('[contenteditable="true"]');
                    if (editor) {
                        // 에디터 끝으로 스크롤
                        editor.scrollTop = editor.scrollHeight;

                        // 커서를 맨 끝으로 이동
                        const range = document.createRange();
                        const sel = window.getSelection();
                        range.selectNodeContents(editor);
                        range.collapse(false); // false = 끝으로
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                }
            """)
            logger.debug("커서를 문서 끝으로 이동")
        except Exception as e:
            logger.debug(f"커서 이동 실패 (무시): {e}")


# ============================================
# 실행
# ============================================


async def main():
    """테스트 실행"""
    import sys

    # 기본값
    naver_id = "wncksdid0750"
    title = "테스트 포스팅 - 자동화 테스트"
    content = """안녕하세요!

이 글은 자동화 테스트로 작성된 글입니다.

Python과 Playwright를 사용하여 자동으로 포스팅되었습니다.

테스트가 성공적으로 완료되었습니다!"""

    # 커맨드라인 인자 처리
    if len(sys.argv) > 1:
        naver_id = sys.argv[1]
    if len(sys.argv) > 2:
        title = sys.argv[2]
    if len(sys.argv) > 3:
        content = sys.argv[3]

    logger.info("=" * 60)
    logger.info("네이버 블로그 자동 포스팅")
    logger.info("=" * 60)
    logger.info(f"계정: {naver_id}")
    logger.info(f"제목: {title}")
    logger.info("")

    poster = NaverBlogPoster(naver_id)
    result = await poster.post(title, content)

    if result["success"]:
        logger.success(f"\n✅ 포스팅 성공!")
        logger.success(f"URL: {result['url']}")
    else:
        logger.error(f"\n❌ 포스팅 실패: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
