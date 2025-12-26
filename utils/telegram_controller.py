"""
텔레그램 원격 제어 시스템
- 봇 명령어를 통한 원격 제어
- 상태 조회 및 제어 명령
- 인증된 관리자만 제어 가능
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot 패키지가 설치되지 않았습니다")


class TelegramController:
    """텔레그램 원격 제어 클래스"""

    # 명령어 목록
    COMMANDS = {
        "/status": "현재 상태 조회",
        "/start_scheduler": "스케줄러 시작",
        "/stop_scheduler": "스케줄러 중지",
        "/post": "즉시 포스팅 실행",
        "/stats": "통계 조회",
        "/health": "헬스체크 실행",
        "/accounts": "계정 상태 조회",
        "/help": "도움말"
    }

    def __init__(self, scheduler=None):
        """
        Args:
            scheduler: AutoPostingScheduler 인스턴스 (제어용)
        """
        self.scheduler = scheduler
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None

        # 환경변수에서 설정 로드
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

        # 콜백 함수 저장소
        self.callbacks: Dict[str, Callable] = {}

        if not TELEGRAM_AVAILABLE:
            logger.error("텔레그램 패키지가 설치되지 않았습니다")
            return

        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
            return

        logger.info("TelegramController 초기화")

    def is_authorized(self, chat_id: int) -> bool:
        """관리자 인증 확인"""
        if not self.admin_chat_id:
            return False
        return str(chat_id) == str(self.admin_chat_id)

    async def start(self) -> None:
        """텔레그램 봇 시작"""
        if not TELEGRAM_AVAILABLE or not self.bot_token:
            logger.warning("텔레그램 컨트롤러를 시작할 수 없습니다")
            return

        try:
            # Application 생성
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot

            # 명령어 핸들러 등록
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("start_scheduler", self._cmd_start_scheduler))
            self.application.add_handler(CommandHandler("stop_scheduler", self._cmd_stop_scheduler))
            self.application.add_handler(CommandHandler("post", self._cmd_post))
            self.application.add_handler(CommandHandler("stats", self._cmd_stats))
            self.application.add_handler(CommandHandler("health", self._cmd_health))
            self.application.add_handler(CommandHandler("accounts", self._cmd_accounts))

            # 폴링 시작
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.success("텔레그램 컨트롤러 시작됨")

        except Exception as e:
            logger.error(f"텔레그램 컨트롤러 시작 실패: {e}")

    async def stop(self) -> None:
        """텔레그램 봇 중지"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("텔레그램 컨트롤러 중지됨")

    def register_callback(self, name: str, callback: Callable) -> None:
        """
        콜백 함수 등록

        Args:
            name: 콜백 이름 (예: "get_status", "start_scheduler")
            callback: 콜백 함수
        """
        self.callbacks[name] = callback
        logger.debug(f"콜백 등록: {name}")

    async def send_message(self, message: str) -> bool:
        """
        관리자에게 메시지 전송

        Args:
            message: 전송할 메시지

        Returns:
            성공 여부
        """
        if not self.bot or not self.admin_chat_id:
            return False

        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            return False

    # ============================================
    # 명령어 핸들러
    # ============================================

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """시작 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            logger.warning(f"미인증 접근 시도: {chat_id}")
            return

        await update.message.reply_text(
            "🤖 <b>네이버 블로그 봇 컨트롤러</b>\n\n"
            "사용 가능한 명령어를 보려면 /help 를 입력하세요.",
            parse_mode="HTML"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """도움말 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        help_text = "📋 <b>사용 가능한 명령어</b>\n\n"
        for cmd, desc in self.COMMANDS.items():
            help_text += f"• <code>{cmd}</code> - {desc}\n"

        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """상태 조회 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        await update.message.reply_text("🔄 상태 조회 중...")

        try:
            # 콜백을 통해 상태 조회
            if "get_status" in self.callbacks:
                status = await self.callbacks["get_status"]()
            else:
                status = self._get_basic_status()

            status_text = self._format_status(status)
            await update.message.reply_text(status_text, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ 상태 조회 실패: {e}")

    async def _cmd_start_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """스케줄러 시작 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        try:
            if "start_scheduler" in self.callbacks:
                await self.callbacks["start_scheduler"]()
                await update.message.reply_text("✅ 스케줄러가 시작되었습니다.")
            elif self.scheduler:
                await self.scheduler.start()
                await update.message.reply_text("✅ 스케줄러가 시작되었습니다.")
            else:
                await update.message.reply_text("❌ 스케줄러가 연결되지 않았습니다.")

        except Exception as e:
            await update.message.reply_text(f"❌ 스케줄러 시작 실패: {e}")

    async def _cmd_stop_scheduler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """스케줄러 중지 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        try:
            if "stop_scheduler" in self.callbacks:
                await self.callbacks["stop_scheduler"]()
                await update.message.reply_text("⏹ 스케줄러가 중지되었습니다.")
            elif self.scheduler:
                await self.scheduler.stop()
                await update.message.reply_text("⏹ 스케줄러가 중지되었습니다.")
            else:
                await update.message.reply_text("❌ 스케줄러가 연결되지 않았습니다.")

        except Exception as e:
            await update.message.reply_text(f"❌ 스케줄러 중지 실패: {e}")

    async def _cmd_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """즉시 포스팅 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        await update.message.reply_text("📝 포스팅 작업을 시작합니다...")

        try:
            if "trigger_post" in self.callbacks:
                result = await self.callbacks["trigger_post"]()
                if result.get("success"):
                    await update.message.reply_text(
                        f"✅ 포스팅 완료!\n\n"
                        f"제목: {result.get('title', 'N/A')}\n"
                        f"URL: {result.get('url', 'N/A')}"
                    )
                else:
                    await update.message.reply_text(f"❌ 포스팅 실패: {result.get('error')}")
            else:
                await update.message.reply_text("❌ 포스팅 기능이 연결되지 않았습니다.")

        except Exception as e:
            await update.message.reply_text(f"❌ 포스팅 실패: {e}")

    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """통계 조회 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        try:
            if "get_stats" in self.callbacks:
                stats = await self.callbacks["get_stats"]()
                stats_text = self._format_stats(stats)
            else:
                stats_text = "📊 통계 기능이 연결되지 않았습니다."

            await update.message.reply_text(stats_text, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ 통계 조회 실패: {e}")

    async def _cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """헬스체크 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        await update.message.reply_text("🔍 헬스체크 실행 중...")

        try:
            if "run_health_check" in self.callbacks:
                result = await self.callbacks["run_health_check"]()
                health_text = self._format_health(result)
            else:
                # 기본 헬스체크
                from monitoring.health_checker import HealthChecker
                checker = HealthChecker()
                await checker.run_all_checks()
                health_text = self._format_health(checker.get_status_report())

            await update.message.reply_text(health_text, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ 헬스체크 실패: {e}")

    async def _cmd_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """계정 상태 조회 명령어"""
        chat_id = update.effective_chat.id

        if not self.is_authorized(chat_id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            return

        try:
            if "get_accounts" in self.callbacks:
                accounts = await self.callbacks["get_accounts"]()
                accounts_text = self._format_accounts(accounts)
            else:
                from scheduler.account_manager import AccountManager
                manager = AccountManager()
                accounts_text = self._format_accounts(manager.get_account_status())

            await update.message.reply_text(accounts_text, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ 계정 조회 실패: {e}")

    # ============================================
    # 포맷팅 헬퍼
    # ============================================

    def _get_basic_status(self) -> Dict[str, Any]:
        """기본 상태 정보"""
        return {
            "is_running": self.scheduler.is_running if self.scheduler else False,
            "last_update": datetime.now().isoformat()
        }

    def _format_status(self, status: Dict[str, Any]) -> str:
        """상태 정보 포맷팅"""
        is_running = status.get("is_running", False)
        running_emoji = "🟢" if is_running else "🔴"

        text = f"📊 <b>시스템 상태</b>\n\n"
        text += f"{running_emoji} 스케줄러: {'실행 중' if is_running else '중지됨'}\n"
        text += f"⏰ 조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        if "next_post_time" in status:
            text += f"📅 다음 포스팅: {status['next_post_time']}\n"

        if "today_posts" in status:
            text += f"📝 오늘 포스팅: {status['today_posts']}회\n"

        return text

    def _format_stats(self, stats: Dict[str, Any]) -> str:
        """통계 정보 포맷팅"""
        text = f"📈 <b>통계</b>\n\n"

        if "total_posts" in stats:
            text += f"📝 총 포스팅: {stats['total_posts']}개\n"
        if "today_posts" in stats:
            text += f"📅 오늘 포스팅: {stats['today_posts']}개\n"
        if "success_rate" in stats:
            text += f"✅ 성공률: {stats['success_rate']}%\n"

        return text

    def _format_health(self, health: Dict[str, Any]) -> str:
        """헬스체크 결과 포맷팅"""
        overall = health.get("overall_status", "unknown")
        status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}.get(overall, "⚪")

        text = f"🏥 <b>헬스체크 결과</b>\n\n"
        text += f"{status_emoji} 전체 상태: {overall.upper()}\n\n"

        components = health.get("components", {})
        for name, info in components.items():
            comp_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "❌"}.get(
                info.get("status", "unknown"), "❓"
            )
            text += f"{comp_emoji} {name}: {info.get('message', 'N/A')}\n"

        return text

    def _format_accounts(self, accounts: Dict[str, Any]) -> str:
        """계정 정보 포맷팅"""
        text = f"👥 <b>계정 상태</b>\n\n"
        text += f"총 계정: {accounts.get('total_accounts', 0)}개\n"
        text += f"사용 가능: {accounts.get('available_accounts', 0)}개\n\n"

        for nid, info in accounts.get("accounts", {}).items():
            status_emoji = "🟢" if info.get("is_available") else "🔴"
            text += f"{status_emoji} {nid}\n"
            text += f"   상태: {info.get('status', 'N/A')}\n"
            text += f"   오늘 포스팅: {info.get('today_post_count', 0)}회\n"

        return text


# ============================================
# 테스트 코드
# ============================================

async def test_telegram_controller():
    """TelegramController 테스트"""
    print("\n=== TelegramController 테스트 ===\n")

    controller = TelegramController()

    if not TELEGRAM_AVAILABLE:
        print("텔레그램 패키지가 설치되지 않았습니다")
        return

    if not controller.bot_token:
        print("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
        return

    print("명령어 목록:")
    for cmd, desc in controller.COMMANDS.items():
        print(f"  {cmd}: {desc}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_telegram_controller())
