"""
텔레그램 알림 모듈
- 포스팅 성공/실패 알림
- 일일 리포트
- 긴급 오류 알림
"""

import os
import asyncio
from typing import Optional
from datetime import datetime
from loguru import logger

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot 패키지 없음. pip install python-telegram-bot")


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        """
        Args:
            bot_token: 텔레그램 봇 토큰 (없으면 환경변수에서 로드)
            chat_id: 알림 받을 채팅 ID
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        self.bot = None
        if TELEGRAM_AVAILABLE and self.bot_token:
            self.bot = Bot(token=self.bot_token)

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        메시지 전송

        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 (HTML, Markdown)

        Returns:
            성공 여부
        """
        if not self.bot or not self.chat_id:
            logger.debug("텔레그램 설정 없음 - 알림 스킵")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug("텔레그램 알림 전송 완료")
            return True

        except TelegramError as e:
            logger.error(f"텔레그램 전송 실패: {e}")
            return False

    async def send_post_success(
        self,
        title: str,
        url: str,
        posts_today: int,
        daily_limit: int
    ):
        """포스팅 성공 알림"""
        message = f"""✅ <b>블로그 포스팅 성공!</b>

📝 <b>제목:</b> {title[:50]}{'...' if len(title) > 50 else ''}
🔗 <a href="{url}">글 보기</a>

📊 오늘 {posts_today}/{daily_limit}개 발행
⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)

    async def send_post_failure(self, error: str, errors_count: int):
        """포스팅 실패 알림"""
        message = f"""❌ <b>블로그 포스팅 실패!</b>

⚠️ <b>오류:</b> {error[:100]}
📊 누적 실패: {errors_count}회
⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

확인이 필요합니다!
"""
        await self.send_message(message)

    async def send_daily_report(
        self,
        posts_today: int,
        total_posts: int,
        errors_count: int,
        uptime_hours: float
    ):
        """일일 리포트"""
        message = f"""📊 <b>일일 리포트</b>

📝 오늘 포스팅: {posts_today}개
📈 총 포스팅: {total_posts}개
❌ 총 오류: {errors_count}회
⏱ 가동 시간: {uptime_hours:.1f}시간

{datetime.now().strftime('%Y-%m-%d')} 리포트
"""
        await self.send_message(message)

    async def send_startup_notification(
        self,
        naver_id: str,
        interval: str,
        daily_limit: int
    ):
        """시작 알림"""
        message = f"""🚀 <b>블로그 봇 시작!</b>

👤 계정: {naver_id}
⏰ 간격: {interval}
📊 일일 제한: {daily_limit}개

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)

    async def send_shutdown_notification(
        self,
        total_posts: int,
        errors_count: int,
        uptime: str
    ):
        """종료 알림"""
        message = f"""⏹ <b>블로그 봇 종료</b>

📈 총 포스팅: {total_posts}개
❌ 총 오류: {errors_count}회
⏱ 가동 시간: {uptime}

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(message)


# 글로벌 인스턴스
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """싱글톤 notifier 반환"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


async def send_notification(message: str) -> bool:
    """간단한 알림 전송 (헬퍼 함수)"""
    notifier = get_notifier()
    return await notifier.send_message(message)


# ============================================
# 테스트
# ============================================

async def test_telegram():
    """텔레그램 알림 테스트"""
    notifier = TelegramNotifier()

    if not notifier.bot:
        print("텔레그램 설정이 없습니다.")
        print("TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 .env에 설정하세요.")
        return

    print("텔레그램 알림 테스트 전송 중...")

    success = await notifier.send_message("🧪 테스트 알림입니다!")

    if success:
        print("✅ 테스트 성공!")
    else:
        print("❌ 테스트 실패!")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    asyncio.run(test_telegram())
