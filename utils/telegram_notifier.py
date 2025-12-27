"""
텔레그램 알림 모듈 (강화 버전)
- 포스팅 성공/실패 알림
- 일일 리포트
- 긴급 오류 알림
- 시스템 상태 실시간 모니터링
- 다양한 경고 레벨 알림
- 상세 에러 분석 알림
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from loguru import logger

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot 패키지 없음. pip install python-telegram-bot")


class AlertLevel(Enum):
    """알림 레벨"""
    INFO = "info"           # 정보성 알림
    SUCCESS = "success"     # 성공 알림
    WARNING = "warning"     # 경고 알림
    ERROR = "error"         # 오류 알림
    CRITICAL = "critical"   # 심각한 오류 알림


@dataclass
class AlertConfig:
    """알림 설정"""
    enable_info: bool = True
    enable_success: bool = True
    enable_warning: bool = True
    enable_error: bool = True
    enable_critical: bool = True
    # 반복 알림 방지 (분 단위)
    cooldown_minutes: Dict[str, int] = None

    def __post_init__(self):
        if self.cooldown_minutes is None:
            self.cooldown_minutes = {
                "info": 30,
                "success": 0,  # 성공은 항상 알림
                "warning": 10,
                "error": 5,
                "critical": 0  # 심각은 항상 알림
            }


class TelegramNotifier:
    """텔레그램 알림 클래스 (강화 버전)"""

    # 알림 레벨별 이모지
    LEVEL_EMOJI = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.SUCCESS: "✅",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        config: Optional[AlertConfig] = None
    ):
        """
        Args:
            bot_token: 텔레그램 봇 토큰 (없으면 환경변수에서 로드)
            chat_id: 알림 받을 채팅 ID
            config: 알림 설정
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.config = config or AlertConfig()

        # 마지막 알림 시간 추적 (중복 방지)
        self._last_alerts: Dict[str, datetime] = {}

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

    # ============================================
    # 강화된 알림 메서드들
    # ============================================

    def _should_send_alert(self, alert_key: str, level: AlertLevel) -> bool:
        """알림 발송 여부 확인 (쿨다운 체크)"""
        cooldown = self.config.cooldown_minutes.get(level.value, 0)
        if cooldown == 0:
            return True

        last_time = self._last_alerts.get(alert_key)
        if last_time is None:
            return True

        elapsed = (datetime.now() - last_time).total_seconds() / 60
        return elapsed >= cooldown

    def _record_alert(self, alert_key: str):
        """알림 발송 기록"""
        self._last_alerts[alert_key] = datetime.now()

    async def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        details: Optional[Dict[str, Any]] = None,
        alert_key: Optional[str] = None
    ) -> bool:
        """
        레벨별 알림 전송

        Args:
            title: 알림 제목
            message: 알림 내용
            level: 알림 레벨
            details: 추가 상세 정보
            alert_key: 중복 방지용 키

        Returns:
            전송 성공 여부
        """
        # 레벨별 활성화 확인
        level_enabled = {
            AlertLevel.INFO: self.config.enable_info,
            AlertLevel.SUCCESS: self.config.enable_success,
            AlertLevel.WARNING: self.config.enable_warning,
            AlertLevel.ERROR: self.config.enable_error,
            AlertLevel.CRITICAL: self.config.enable_critical
        }

        if not level_enabled.get(level, True):
            return False

        # 쿨다운 확인
        key = alert_key or f"{level.value}:{title}"
        if not self._should_send_alert(key, level):
            logger.debug(f"알림 쿨다운 중: {key}")
            return False

        emoji = self.LEVEL_EMOJI.get(level, "📢")
        text = f"{emoji} <b>{title}</b>\n\n{message}"

        if details:
            text += "\n\n📋 <b>상세 정보:</b>\n"
            for k, v in details.items():
                text += f"  • {k}: {v}\n"

        text += f"\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        result = await self.send_message(text)
        if result:
            self._record_alert(key)
        return result

    async def send_system_status(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        active_tasks: int = 0,
        queue_size: int = 0
    ):
        """시스템 상태 알림"""
        # 상태에 따른 레벨 결정
        level = AlertLevel.INFO
        warnings = []

        if cpu_percent > 90:
            level = AlertLevel.CRITICAL
            warnings.append(f"CPU 과부하: {cpu_percent}%")
        elif cpu_percent > 70:
            level = AlertLevel.WARNING
            warnings.append(f"CPU 높음: {cpu_percent}%")

        if memory_percent > 90:
            level = AlertLevel.CRITICAL
            warnings.append(f"메모리 부족: {memory_percent}%")
        elif memory_percent > 80:
            if level != AlertLevel.CRITICAL:
                level = AlertLevel.WARNING
            warnings.append(f"메모리 높음: {memory_percent}%")

        if disk_percent > 95:
            level = AlertLevel.CRITICAL
            warnings.append(f"디스크 거의 가득: {disk_percent}%")
        elif disk_percent > 85:
            if level != AlertLevel.CRITICAL:
                level = AlertLevel.WARNING
            warnings.append(f"디스크 높음: {disk_percent}%")

        # 정상 상태면 알림 안 함
        if level == AlertLevel.INFO:
            return

        title = "시스템 리소스 경고" if level == AlertLevel.WARNING else "시스템 리소스 위험"

        message = "🖥 <b>시스템 상태:</b>\n"
        message += f"  • CPU: {cpu_percent:.1f}%\n"
        message += f"  • 메모리: {memory_percent:.1f}%\n"
        message += f"  • 디스크: {disk_percent:.1f}%\n"
        message += f"  • 활성 작업: {active_tasks}\n"
        message += f"  • 대기 큐: {queue_size}\n"

        if warnings:
            message += "\n⚠️ <b>경고:</b>\n"
            for w in warnings:
                message += f"  • {w}\n"

        await self.send_alert(title, message, level, alert_key="system_status")

    async def send_api_status(
        self,
        api_name: str,
        status: str,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """API 상태 알림"""
        if status == "healthy":
            if response_time_ms and response_time_ms > 5000:  # 5초 이상이면 경고
                level = AlertLevel.WARNING
                title = f"API 느린 응답: {api_name}"
                message = f"응답 시간이 {response_time_ms:.0f}ms로 느립니다."
            else:
                return  # 정상이면 알림 안 함
        elif status == "warning":
            level = AlertLevel.WARNING
            title = f"API 경고: {api_name}"
            message = error_message or "API에 문제가 감지되었습니다."
        else:  # critical or error
            level = AlertLevel.ERROR
            title = f"API 오류: {api_name}"
            message = error_message or "API에 연결할 수 없습니다."

        details = {"API": api_name}
        if response_time_ms:
            details["응답시간"] = f"{response_time_ms:.0f}ms"

        await self.send_alert(title, message, level, details, alert_key=f"api_{api_name}")

    async def send_session_warning(
        self,
        account_id: str,
        days_until_expiry: int,
        last_used: Optional[datetime] = None
    ):
        """세션 만료 경고"""
        if days_until_expiry <= 1:
            level = AlertLevel.CRITICAL
            title = "세션 만료 임박!"
        elif days_until_expiry <= 3:
            level = AlertLevel.WARNING
            title = "세션 만료 예정"
        else:
            return  # 3일 이상 남으면 알림 안 함

        message = f"계정 <b>{account_id}</b>의 세션이 곧 만료됩니다.\n"
        message += f"남은 기간: <b>{days_until_expiry}일</b>"

        details = {"계정": account_id}
        if last_used:
            details["마지막 사용"] = last_used.strftime("%Y-%m-%d %H:%M")

        await self.send_alert(title, message, level, details, alert_key=f"session_{account_id}")

    async def send_error_analysis(
        self,
        error_type: str,
        error_message: str,
        occurrence_count: int,
        first_occurrence: datetime,
        suggested_action: Optional[str] = None
    ):
        """에러 분석 알림"""
        if occurrence_count >= 5:
            level = AlertLevel.CRITICAL
            title = "반복 에러 발생 (심각)"
        elif occurrence_count >= 3:
            level = AlertLevel.ERROR
            title = "반복 에러 발생"
        else:
            level = AlertLevel.WARNING
            title = "에러 발생"

        message = f"<b>에러 유형:</b> {error_type}\n"
        message += f"<b>내용:</b> {error_message[:200]}\n"
        message += f"<b>발생 횟수:</b> {occurrence_count}회\n"
        message += f"<b>최초 발생:</b> {first_occurrence.strftime('%H:%M:%S')}"

        if suggested_action:
            message += f"\n\n💡 <b>권장 조치:</b>\n{suggested_action}"

        await self.send_alert(title, message, level, alert_key=f"error_{error_type}")

    async def send_health_check_result(
        self,
        overall_status: str,
        components: Dict[str, Dict[str, Any]],
        failed_components: List[str]
    ):
        """헬스체크 결과 알림"""
        if overall_status == "healthy":
            return  # 정상이면 알림 안 함

        if overall_status == "critical":
            level = AlertLevel.CRITICAL
            title = "🔴 시스템 헬스체크 위험"
        else:
            level = AlertLevel.WARNING
            title = "🟡 시스템 헬스체크 경고"

        message = "컴포넌트 상태:\n"
        for name, info in components.items():
            status = info.get("status", "unknown")
            emoji = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
            message += f"  {emoji} {name}: {info.get('message', status)}\n"

        if failed_components:
            message += f"\n❌ <b>문제 컴포넌트:</b> {', '.join(failed_components)}"

        await self.send_alert(title, message, level, alert_key="health_check")

    async def send_rate_limit_warning(
        self,
        service: str,
        current_usage: int,
        limit: int,
        reset_time: Optional[datetime] = None
    ):
        """Rate Limit 경고"""
        usage_percent = (current_usage / limit) * 100

        if usage_percent >= 95:
            level = AlertLevel.CRITICAL
            title = f"Rate Limit 초과 임박: {service}"
        elif usage_percent >= 80:
            level = AlertLevel.WARNING
            title = f"Rate Limit 경고: {service}"
        else:
            return

        message = f"서비스: <b>{service}</b>\n"
        message += f"사용량: <b>{current_usage}/{limit}</b> ({usage_percent:.1f}%)\n"

        if reset_time:
            message += f"리셋 시간: {reset_time.strftime('%H:%M:%S')}"

        await self.send_alert(title, message, level, alert_key=f"ratelimit_{service}")

    async def send_queue_status(
        self,
        pending_posts: int,
        failed_posts: int,
        next_scheduled: Optional[datetime] = None
    ):
        """포스팅 큐 상태 알림"""
        if failed_posts >= 3:
            level = AlertLevel.ERROR
            title = "포스팅 큐 오류"
            message = f"실패한 포스트가 {failed_posts}개 있습니다.\n"
            message += f"대기 중: {pending_posts}개"
        elif pending_posts >= 10:
            level = AlertLevel.WARNING
            title = "포스팅 큐 적체"
            message = f"대기 중인 포스트: {pending_posts}개\n"
            message += f"실패: {failed_posts}개"
        else:
            return

        if next_scheduled:
            message += f"\n다음 포스팅: {next_scheduled.strftime('%H:%M:%S')}"

        await self.send_alert(title, message, level, alert_key="queue_status")

    async def send_account_status(
        self,
        account_id: str,
        status: str,
        posts_today: int,
        daily_limit: int,
        consecutive_failures: int = 0
    ):
        """계정 상태 알림"""
        if consecutive_failures >= 3:
            level = AlertLevel.CRITICAL
            title = f"계정 문제: {account_id}"
            message = f"연속 {consecutive_failures}회 실패!\n"
            message += "계정 확인이 필요합니다."
        elif posts_today >= daily_limit:
            level = AlertLevel.WARNING
            title = f"일일 한도 도달: {account_id}"
            message = f"오늘 포스팅: {posts_today}/{daily_limit}개\n"
            message += "내일까지 포스팅이 중지됩니다."
        else:
            return

        await self.send_alert(title, message, level, alert_key=f"account_{account_id}")

    async def send_recovery_notification(
        self,
        issue_type: str,
        recovery_action: str,
        success: bool,
        details: Optional[str] = None
    ):
        """복구 시도 알림"""
        if success:
            level = AlertLevel.SUCCESS
            title = f"자동 복구 성공: {issue_type}"
            message = f"조치: {recovery_action}\n결과: 정상화됨"
        else:
            level = AlertLevel.ERROR
            title = f"자동 복구 실패: {issue_type}"
            message = f"조치: {recovery_action}\n결과: 실패"
            if details:
                message += f"\n상세: {details}"
            message += "\n\n수동 확인이 필요합니다."

        await self.send_alert(title, message, level, alert_key=f"recovery_{issue_type}")

    async def send_cost_alert(
        self,
        service: str,
        current_cost: float,
        daily_budget: float,
        monthly_cost: float,
        monthly_budget: float
    ):
        """비용 알림"""
        daily_percent = (current_cost / daily_budget) * 100
        monthly_percent = (monthly_cost / monthly_budget) * 100

        if daily_percent >= 100 or monthly_percent >= 100:
            level = AlertLevel.CRITICAL
            title = f"💰 비용 초과: {service}"
        elif daily_percent >= 80 or monthly_percent >= 80:
            level = AlertLevel.WARNING
            title = f"💰 비용 경고: {service}"
        else:
            return

        message = f"<b>일일:</b> ${current_cost:.2f} / ${daily_budget:.2f} ({daily_percent:.1f}%)\n"
        message += f"<b>월간:</b> ${monthly_cost:.2f} / ${monthly_budget:.2f} ({monthly_percent:.1f}%)"

        await self.send_alert(title, message, level, alert_key=f"cost_{service}")

    async def send_maintenance_reminder(
        self,
        task: str,
        last_done: Optional[datetime] = None,
        recommended_interval_days: int = 7
    ):
        """유지보수 알림"""
        if last_done:
            days_since = (datetime.now() - last_done).days
            if days_since < recommended_interval_days:
                return

            level = AlertLevel.INFO if days_since < recommended_interval_days * 2 else AlertLevel.WARNING
        else:
            level = AlertLevel.INFO
            days_since = "알 수 없음"

        title = f"🔧 유지보수 필요: {task}"
        message = f"마지막 수행: {days_since}일 전\n"
        message += f"권장 주기: {recommended_interval_days}일"

        await self.send_alert(title, message, level, alert_key=f"maintenance_{task}")

    async def send_performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        unit: str = "",
        trend: str = "stable"  # up, down, stable
    ):
        """성능 지표 알림"""
        if current_value <= threshold:
            return

        percent_over = ((current_value - threshold) / threshold) * 100

        if percent_over >= 50:
            level = AlertLevel.CRITICAL
        elif percent_over >= 20:
            level = AlertLevel.ERROR
        else:
            level = AlertLevel.WARNING

        trend_emoji = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"

        title = f"성능 이슈: {metric_name}"
        message = f"현재 값: <b>{current_value}{unit}</b>\n"
        message += f"임계값: {threshold}{unit}\n"
        message += f"초과율: {percent_over:.1f}%\n"
        message += f"추세: {trend_emoji} {trend}"

        await self.send_alert(title, message, level, alert_key=f"perf_{metric_name}")


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
