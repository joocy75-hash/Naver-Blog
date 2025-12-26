"""
클립보드 기반 자동 입력 헬퍼
- pyperclip + keyboard를 사용하여 실제 붙여넣기처럼 동작
- fill() 함수가 오작동할 때 대안으로 사용
- SecureSessionManager와 연동
"""

import asyncio
import platform
import random
from typing import Optional
from loguru import logger

# 플랫폼별 키보드 라이브러리
try:
    import pyperclip
except ImportError:
    logger.error("pyperclip이 설치되지 않았습니다: pip install pyperclip")
    raise

try:
    import pyautogui
    # macOS에서 더 안정적인 pyautogui 사용
    pyautogui.PAUSE = 0.05  # 명령 간 기본 딜레이
    pyautogui.FAILSAFE = True  # 마우스를 모서리로 이동하면 중단
except ImportError:
    logger.warning("pyautogui가 설치되지 않았습니다: pip install pyautogui")
    pyautogui = None


class ClipboardInputHelper:
    """클립보드 기반 텍스트 입력 헬퍼"""

    def __init__(
        self,
        typing_delay_min: float = 0.03,
        typing_delay_max: float = 0.08,
        use_chunk_paste: bool = True,
        chunk_size_range: tuple = (3, 8)
    ):
        """
        Args:
            typing_delay_min: 최소 입력 딜레이 (초)
            typing_delay_max: 최대 입력 딜레이 (초)
            use_chunk_paste: 청크 단위 붙여넣기 사용 여부
            chunk_size_range: 청크 크기 범위 (최소, 최대)
        """
        self.typing_delay_min = typing_delay_min
        self.typing_delay_max = typing_delay_max
        self.use_chunk_paste = use_chunk_paste
        self.chunk_size_range = chunk_size_range
        self.is_macos = platform.system() == "Darwin"

        # 원본 클립보드 내용 백업용
        self._original_clipboard: Optional[str] = None

    def _get_paste_hotkey(self) -> tuple:
        """플랫폼별 붙여넣기 단축키 반환"""
        if self.is_macos:
            return ('command', 'v')
        else:
            return ('ctrl', 'v')

    def _backup_clipboard(self):
        """현재 클립보드 내용 백업"""
        try:
            self._original_clipboard = pyperclip.paste()
        except Exception:
            self._original_clipboard = None

    def _restore_clipboard(self):
        """클립보드 내용 복원"""
        if self._original_clipboard is not None:
            try:
                pyperclip.copy(self._original_clipboard)
            except Exception:
                pass

    async def paste_text(self, text: str, restore_clipboard: bool = True):
        """
        클립보드를 통해 텍스트 붙여넣기

        Args:
            text: 붙여넣을 텍스트
            restore_clipboard: 작업 후 원래 클립보드 복원 여부
        """
        if not pyautogui:
            raise RuntimeError("pyautogui가 필요합니다: pip install pyautogui")

        # 클립보드 백업
        if restore_clipboard:
            self._backup_clipboard()

        try:
            # 텍스트를 클립보드에 복사
            pyperclip.copy(text)
            await asyncio.sleep(0.05)

            # 붙여넣기 단축키 실행
            hotkey = self._get_paste_hotkey()
            pyautogui.hotkey(*hotkey)

            # 완료 대기
            await asyncio.sleep(0.1)

            logger.debug(f"텍스트 붙여넣기 완료: {text[:30]}...")

        finally:
            # 클립보드 복원
            if restore_clipboard:
                await asyncio.sleep(0.05)
                self._restore_clipboard()

    async def paste_text_chunked(
        self,
        text: str,
        restore_clipboard: bool = True
    ):
        """
        청크 단위로 텍스트 붙여넣기 (더 자연스러운 입력)

        Args:
            text: 붙여넣을 텍스트
            restore_clipboard: 작업 후 원래 클립보드 복원 여부
        """
        if not pyautogui:
            raise RuntimeError("pyautogui가 필요합니다: pip install pyautogui")

        # 클립보드 백업
        if restore_clipboard:
            self._backup_clipboard()

        try:
            # 텍스트를 청크로 분할
            chunks = self._split_into_chunks(text)
            hotkey = self._get_paste_hotkey()

            for chunk in chunks:
                # 청크를 클립보드에 복사
                pyperclip.copy(chunk)
                await asyncio.sleep(0.03)

                # 붙여넣기
                pyautogui.hotkey(*hotkey)

                # 자연스러운 딜레이
                delay = random.uniform(
                    self.typing_delay_min,
                    self.typing_delay_max
                )
                await asyncio.sleep(delay)

            logger.debug(f"청크 붙여넣기 완료 ({len(chunks)}개 청크)")

        finally:
            # 클립보드 복원
            if restore_clipboard:
                await asyncio.sleep(0.05)
                self._restore_clipboard()

    def _split_into_chunks(self, text: str) -> list:
        """텍스트를 청크로 분할"""
        chunks = []
        i = 0

        while i < len(text):
            # 랜덤 청크 크기
            chunk_size = random.randint(*self.chunk_size_range)
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
            i += chunk_size

        return chunks

    async def type_with_clipboard(
        self,
        page,
        selector: str,
        text: str,
        click_first: bool = True,
        clear_existing: bool = True
    ):
        """
        Playwright 페이지의 특정 요소에 클립보드 방식으로 입력
        (Playwright 내부 명령어 사용 - 브라우저 포커스 문제 해결)

        Args:
            page: Playwright Page 객체
            selector: CSS 선택자
            text: 입력할 텍스트
            click_first: 입력 전 요소 클릭 여부
            clear_existing: 기존 내용 삭제 여부
        """
        # 요소 클릭하여 포커스
        if click_first:
            await page.click(selector)
            await asyncio.sleep(random.uniform(0.1, 0.2))

        # 기존 내용 삭제 (Playwright 방식)
        if clear_existing:
            await page.fill(selector, '')
            await asyncio.sleep(0.05)

        # JavaScript로 클립보드 붙여넣기 시뮬레이션
        await page.evaluate(f'''
            (text) => {{
                const el = document.querySelector("{selector}");
                if (el) {{
                    el.focus();
                    el.value = text;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
        ''', text)

        await asyncio.sleep(0.1)
        logger.info(f"클립보드 입력 완료: {selector}")

    async def type_credentials(
        self,
        page,
        id_selector: str,
        pw_selector: str,
        naver_id: str,
        naver_pw: str
    ):
        """
        로그인 자격 증명 입력 (클립보드 방식)

        Args:
            page: Playwright Page 객체
            id_selector: 아이디 입력창 CSS 선택자
            pw_selector: 비밀번호 입력창 CSS 선택자
            naver_id: 네이버 아이디
            naver_pw: 네이버 비밀번호
        """
        logger.info("자격 증명 입력 시작 (클립보드 방식)...")

        # 아이디 입력
        await self.type_with_clipboard(
            page,
            id_selector,
            naver_id,
            click_first=True,
            clear_existing=True
        )

        # 자연스러운 딜레이 (탭 이동처럼)
        await asyncio.sleep(random.uniform(0.3, 0.6))

        # 비밀번호 입력
        await self.type_with_clipboard(
            page,
            pw_selector,
            naver_pw,
            click_first=True,
            clear_existing=True
        )

        logger.success("자격 증명 입력 완료")


# ============================================
# 세션 매니저와 통합된 로그인 헬퍼
# ============================================

async def clipboard_assisted_login(
    page,
    naver_id: str,
    naver_pw: str,
    session_manager=None,
    session_name: str = "default"
) -> bool:
    """
    클립보드 방식을 사용한 로그인 헬퍼

    Args:
        page: Playwright Page 객체
        naver_id: 네이버 아이디
        naver_pw: 네이버 비밀번호
        session_manager: SecureSessionManager 인스턴스 (선택)
        session_name: 저장할 세션 이름

    Returns:
        로그인 성공 여부
    """
    helper = ClipboardInputHelper()

    try:
        # 네이버 로그인 페이지 이동
        await page.goto('https://nid.naver.com/nidlogin.login')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # 클립보드 방식으로 자격 증명 입력
        await helper.type_credentials(
            page,
            id_selector='#id',
            pw_selector='#pw',
            naver_id=naver_id,
            naver_pw=naver_pw
        )

        # 잠시 대기 후 로그인 버튼 클릭
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await page.click('#log\\.login')

        # 로그인 완료 대기 (캡챠, 2FA가 없는 경우)
        logger.info("로그인 처리 대기 중...")
        await asyncio.sleep(3)

        # 로그인 성공 확인
        current_url = page.url
        if 'nid.naver.com' not in current_url or 'nidlogin' not in current_url:
            logger.success("로그인 성공!")

            # 세션 저장 (옵션)
            if session_manager:
                context = page.context
                storage_state = await context.storage_state()
                session_manager.save_session(
                    storage_state=storage_state,
                    session_name=session_name,
                    metadata={"account_id": naver_id, "method": "clipboard"}
                )
                logger.info(f"세션 저장 완료: {session_name}")

            return True
        else:
            logger.warning("로그인 페이지에 머물러 있음 - 캡챠/2FA 필요할 수 있음")
            return False

    except Exception as e:
        logger.error(f"로그인 실패: {e}")
        return False


# ============================================
# 테스트 및 예제
# ============================================

if __name__ == "__main__":
    # 간단한 테스트
    async def test_clipboard():
        helper = ClipboardInputHelper()

        print("3초 후 클립보드 테스트를 시작합니다.")
        print("텍스트 입력창에 커서를 두세요!")
        await asyncio.sleep(3)

        test_text = "테스트 텍스트입니다. Hello World! 123"
        await helper.paste_text_chunked(test_text)

        print("테스트 완료!")

    asyncio.run(test_clipboard())
