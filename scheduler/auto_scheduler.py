"""
24시간 자동 포스팅 스케줄러
- APScheduler 기반 백그라운드 스케줄링
- 1-2시간 간격으로 자동 포스팅
- 텔레그램 알림 연동
- 서버 배포용 (systemd, Docker 지원)
"""

import os
import sys
import asyncio
import random
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from pipeline import BlogPostPipeline

# 새로 추가된 시스템 모듈
from scheduler.topic_rotator import TopicRotator
from scheduler.account_manager import AccountManager
from utils.error_recovery import ErrorRecoveryManager, ErrorType, classify_error
from monitoring.health_checker import HealthChecker
from monitoring.reporter import StatisticsReporter
from models.database import DatabaseManager, DBSession


class AutoPostingScheduler:
    """
    24시간 자동 포스팅 스케줄러

    사용법:
        scheduler = AutoPostingScheduler(
            naver_id="your_id",
            min_interval_hours=1,
            max_interval_hours=2
        )
        scheduler.start()  # 블로킹 모드로 실행
    """

    # 템플릿 가중치 (더 자주 사용할 템플릿에 높은 가중치)
    TEMPLATE_WEIGHTS = {
        "trading_mistake": 3,  # 매매 실수 - 인기 높음
        "market_analysis": 2,  # 시장 분석
        "investment_tip": 3,  # 투자 팁 - 인기 높음
        "psychology": 2,  # 투자 심리
    }

    # 활동 시간대 (한국 시간 기준)
    ACTIVE_HOURS = {
        "morning": (7, 9),  # 아침: 7시-9시
        "lunch": (11, 13),  # 점심: 11시-13시
        "afternoon": (14, 17),  # 오후: 14시-17시
        "evening": (19, 22),  # 저녁: 19시-22시
        "night": (22, 24),  # 밤: 22시-24시
    }

    def __init__(
        self,
        naver_id: str,
        min_interval_hours: float = 1.0,
        max_interval_hours: float = 2.0,
        daily_limit: int = 12,
        model: str = "haiku",
        telegram_enabled: bool = True,
        multi_account: bool = False,
    ):
        """
        Args:
            naver_id: 네이버 계정 ID
            min_interval_hours: 최소 포스팅 간격 (시간)
            max_interval_hours: 최대 포스팅 간격 (시간)
            daily_limit: 일일 최대 포스팅 수
            model: 글쓰기 모델 ("haiku" 또는 "sonnet")
            telegram_enabled: 텔레그램 알림 활성화
            multi_account: 다중 계정 모드 활성화
        """
        self.naver_id = naver_id
        self.min_interval = min_interval_hours
        self.max_interval = max_interval_hours
        self.daily_limit = daily_limit
        self.model = model
        self.telegram_enabled = telegram_enabled
        self.multi_account = multi_account

        # 상태 추적
        self.posts_today = 0
        self.last_post_time: Optional[datetime] = None
        self.total_posts = 0
        self.errors_count = 0
        self.start_time: Optional[datetime] = None
        self.is_running = False

        # 스케줄러 (AsyncIOScheduler로 변경 - async 함수 직접 지원)
        self.scheduler = AsyncIOScheduler()
        self.pipeline: Optional[BlogPostPipeline] = None

        # 새로운 시스템 모듈 초기화
        self.db = DatabaseManager()
        self.topic_rotator = TopicRotator(db=self.db)
        self.account_manager = AccountManager(db=self.db) if multi_account else None
        self.error_recovery = ErrorRecoveryManager()
        self.health_checker = HealthChecker()
        self.reporter = StatisticsReporter(db=self.db)

        # 로그 설정
        self._setup_logging()

    def _setup_logging(self):
        """로깅 설정"""
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)

        # 파일 로그 추가
        logger.add(
            log_dir / "scheduler_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        )

    def _get_random_interval(self) -> float:
        """랜덤 포스팅 간격 (시간) 반환"""
        return random.uniform(self.min_interval, self.max_interval)

    def _get_weighted_template(self) -> str:
        """가중치 기반 랜덤 템플릿 선택"""
        templates = []
        for template, weight in self.TEMPLATE_WEIGHTS.items():
            templates.extend([template] * weight)
        return random.choice(templates)

    def _is_active_hour(self) -> bool:
        """현재 시간이 활동 시간대인지 확인"""
        current_hour = datetime.now().hour

        for period, (start, end) in self.ACTIVE_HOURS.items():
            if start <= current_hour < end:
                return True

        return False

    def _should_post(self) -> bool:
        """포스팅 가능 여부 확인"""
        # 에러 복구 시스템 - 일시정지 상태 확인
        if self.error_recovery.should_pause():
            logger.warning("에러 복구 시스템에 의해 일시정지 중")
            return False

        # 일일 제한 확인
        if self.posts_today >= self.daily_limit:
            logger.warning(
                f"일일 포스팅 제한 도달: {self.posts_today}/{self.daily_limit}"
            )
            return False

        # ★ 24시간 운영: 활동 시간대 체크 비활성화
        # 원격 서버에서는 24시간 무인 운영되므로 시간대 제한 없이 포스팅
        # (필요시 아래 주석 해제하여 시간대 제한 적용 가능)
        # if not self._is_active_hour():
        #     logger.info("현재 비활동 시간대 - 포스팅 스킵")
        #     return False

        return True

    async def _post_job(self):
        """실제 포스팅 작업 - 새로운 시스템 통합"""
        job_start = datetime.now()
        current_naver_id = self.naver_id
        logger.info("=" * 50)
        logger.info(
            f"📝 자동 포스팅 작업 시작 ({job_start.strftime('%Y-%m-%d %H:%M:%S')})"
        )

        # 포스팅 가능 여부 확인
        if not self._should_post():
            self._schedule_next_post()
            return

        try:
            # 다중 계정 모드: 사용 가능한 계정 선택
            if self.multi_account and self.account_manager:
                account = self.account_manager.get_best_account()
                if account:
                    current_naver_id = account.naver_id
                    logger.info(f"   사용 계정: {current_naver_id}")
                else:
                    logger.warning("사용 가능한 계정 없음 - 기본 계정 사용")

            # 파이프라인 초기화 (lazy)
            if not self.pipeline or self.pipeline.naver_id != current_naver_id:
                self.pipeline = BlogPostPipeline(
                    naver_id=current_naver_id, model=self.model
                )

            # TopicRotator를 사용한 카테고리 선택
            category = self.topic_rotator.get_next_category()
            logger.info(
                f"   카테고리: {category} ({self.topic_rotator.CATEGORY_NAMES.get(category)})"
            )

            # 랜덤 템플릿/키워드 선택
            template_type = self._get_weighted_template()
            keywords = self.pipeline.list_keywords(template_type)
            keyword = random.choice(keywords) if keywords else None

            logger.info(f"   템플릿: {template_type}, 키워드: {keyword}")

            # 중복 주제 확인
            if keyword:
                with DBSession(self.db) as session:
                    if self.db.is_topic_duplicate(session, keyword):
                        logger.warning(f"중복 주제 감지: {keyword} - 다른 키워드 선택")
                        # 다른 키워드 선택 시도
                        available_keywords = [k for k in keywords if k != keyword]
                        keyword = (
                            random.choice(available_keywords)
                            if available_keywords
                            else keyword
                        )

            # 마케팅 콘텐츠 발행
            result = await self.pipeline.run_marketing(
                template_type=template_type,
                keyword=keyword,
                generate_image=True,
                dry_run=False,
            )

            # 결과 처리
            if result.get("success"):
                self.posts_today += 1
                self.total_posts += 1
                self.last_post_time = datetime.now()

                # 에러 복구 시스템에 성공 기록
                self.error_recovery.record_success()

                # 다중 계정 모드: 계정에 성공 기록
                if self.multi_account and self.account_manager:
                    self.account_manager.record_post_success(current_naver_id)

                logger.success(f"✅ 포스팅 성공 #{self.total_posts}")
                logger.success(f"   제목: {result.get('title', '')[:40]}...")
                logger.success(f"   URL: {result.get('url', 'N/A')}")

                # 텔레그램 알림
                await self._send_telegram_notification(
                    success=True,
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                )
            else:
                self.errors_count += 1
                error_msg = result.get("error", "알 수 없는 오류")
                logger.error(f"❌ 포스팅 실패: {error_msg}")

                # 에러 복구 시스템에 실패 기록
                error_type = classify_error(Exception(error_msg))
                self.error_recovery.record_error(error_type, error_msg)

                # 다중 계정 모드: 계정에 실패 기록
                if self.multi_account and self.account_manager:
                    self.account_manager.record_post_failure(current_naver_id)

                await self._send_telegram_notification(success=False, error=error_msg)

        except Exception as e:
            self.errors_count += 1
            logger.exception(f"❌ 포스팅 작업 중 예외 발생: {e}")

            # 에러 복구 시스템에 기록
            error_type = classify_error(e)
            self.error_recovery.record_error(error_type, str(e), exception=e)

            # 다중 계정 모드: 계정에 실패 기록
            if self.multi_account and self.account_manager:
                self.account_manager.record_post_failure(current_naver_id)

            await self._send_telegram_notification(success=False, error=str(e))

        finally:
            # 다음 포스팅 스케줄링
            self._schedule_next_post()

            elapsed = (datetime.now() - job_start).total_seconds()
            logger.info(f"   작업 소요 시간: {elapsed:.1f}초")
            logger.info("=" * 50)

    def _schedule_next_post(self):
        """다음 포스팅 스케줄링"""
        interval_hours = self._get_random_interval()
        next_time = datetime.now() + timedelta(hours=interval_hours)

        logger.info(
            f"⏰ 다음 포스팅 예정: {next_time.strftime('%H:%M:%S')} ({interval_hours:.1f}시간 후)"
        )

        # 기존 일회성 작업 제거 후 새로 스케줄
        try:
            self.scheduler.remove_job("next_post")
        except:
            pass

        self.scheduler.add_job(
            self._post_job,
            trigger="date",
            run_date=next_time,
            id="next_post",
            replace_existing=True,
        )

    async def _send_telegram_notification(
        self, success: bool, title: str = "", url: str = "", error: str = ""
    ):
        """텔레그램 알림 전송"""
        if not self.telegram_enabled:
            logger.debug("텔레그램 알림 비활성화됨")
            return

        logger.info("📱 텔레그램 알림 전송 시도...")

        try:
            from utils.telegram_notifier import send_notification

            if success:
                message = f"""✅ 블로그 포스팅 성공!

📝 제목: {title[:50]}...
🔗 URL: {url}
📊 오늘 {self.posts_today}/{self.daily_limit}개
⏱ 총 {self.total_posts}개 발행
"""
            else:
                message = f"""❌ 블로그 포스팅 실패

⚠️ 오류: {error[:100]}
📊 실패 횟수: {self.errors_count}
"""

            result = await send_notification(message)
            if result:
                logger.success("📱 텔레그램 알림 전송 완료")
            else:
                logger.warning("📱 텔레그램 알림 전송 실패 (설정 확인 필요)")

        except ImportError as e:
            logger.warning(f"텔레그램 알림 모듈 없음: {e}")
        except Exception as e:
            logger.warning(f"텔레그램 알림 실패: {e}")

    async def _reset_daily_counter(self):
        """자정에 일일 카운터 리셋"""
        logger.info("🔄 일일 포스팅 카운터 리셋")
        self.posts_today = 0

        # 다중 계정 모드: 모든 계정 카운터 리셋
        if self.multi_account and self.account_manager:
            self.account_manager.reset_daily_counts()

    async def _run_health_check(self):
        """정기 헬스체크 실행"""
        logger.info("🏥 정기 헬스체크 실행")
        try:
            await self.health_checker.run_all_checks()
            report = self.health_checker.get_status_report()

            if report.get("overall_status") == "critical":
                logger.error(f"헬스체크 결과: CRITICAL")
                await self.health_checker.send_alert_if_needed()
            elif report.get("overall_status") == "warning":
                logger.warning(f"헬스체크 결과: WARNING")
            else:
                logger.info(f"헬스체크 결과: HEALTHY")

        except Exception as e:
            logger.error(f"헬스체크 실패: {e}")

    async def _send_daily_report(self):
        """일간 리포트 전송"""
        logger.info("📊 일간 리포트 생성 및 전송")
        try:
            await self.reporter.send_daily_report()
        except Exception as e:
            logger.error(f"일간 리포트 전송 실패: {e}")

    async def _send_weekly_report(self):
        """주간 리포트 전송"""
        logger.info("📈 주간 리포트 생성 및 전송")
        try:
            await self.reporter.send_weekly_report()
        except Exception as e:
            logger.error(f"주간 리포트 전송 실패: {e}")

    async def _run_quick_resource_check(self):
        """빠른 시스템 리소스 체크 (15분마다)"""
        logger.debug("⚡ 빠른 리소스 체크 실행")
        try:
            await self.health_checker.run_quick_check()
        except Exception as e:
            logger.error(f"빠른 리소스 체크 실패: {e}")

    async def _check_session_status(self):
        """세션 상태 체크 및 만료 경고"""
        logger.info("🔐 세션 상태 체크")
        try:
            from security.session_manager import SecureSessionManager
            from utils.telegram_notifier import get_notifier

            session_manager = SecureSessionManager()
            sessions = session_manager.list_sessions()
            notifier = get_notifier()

            for session_name in sessions:
                # 세션 유효성 확인
                if not session_manager.is_session_valid(session_name, max_age_days=7):
                    # 만료됨
                    await notifier.send_session_warning(
                        account_id=session_name, days_until_expiry=0
                    )
                elif not session_manager.is_session_valid(session_name, max_age_days=5):
                    # 2일 이내 만료
                    await notifier.send_session_warning(
                        account_id=session_name, days_until_expiry=2
                    )
                elif not session_manager.is_session_valid(session_name, max_age_days=4):
                    # 3일 이내 만료
                    await notifier.send_session_warning(
                        account_id=session_name, days_until_expiry=3
                    )

        except Exception as e:
            logger.error(f"세션 상태 체크 실패: {e}")

    def _on_job_executed(self, event):
        """작업 완료 이벤트 핸들러"""
        logger.debug(f"Job executed: {event.job_id}")

    def _on_job_error(self, event):
        """작업 오류 이벤트 핸들러"""
        logger.error(f"Job error: {event.job_id} - {event.exception}")

    def start(self, blocking: bool = True):
        """
        스케줄러 시작

        Args:
            blocking: True면 블로킹 모드 (서버용), False면 논블로킹
        """
        self.start_time = datetime.now()
        self.is_running = True

        logger.info("=" * 60)
        logger.info("🚀 24시간 자동 포스팅 스케줄러 시작")
        logger.info("=" * 60)
        logger.info(f"   네이버 ID: {self.naver_id}")
        logger.info(f"   포스팅 간격: {self.min_interval}-{self.max_interval}시간")
        logger.info(f"   일일 제한: {self.daily_limit}개")
        logger.info(f"   모델: {self.model}")
        logger.info(f"   텔레그램 알림: {'ON' if self.telegram_enabled else 'OFF'}")
        logger.info("=" * 60)

        # asyncio 이벤트 루프에서 실행
        if blocking:
            asyncio.run(self._async_main())
        else:
            # 논블로킹 모드 - 백그라운드 스레드에서 실행
            import threading

            thread = threading.Thread(
                target=lambda: asyncio.run(self._async_main()), daemon=True
            )
            thread.start()

    async def _async_main(self):
        """비동기 메인 루프"""
        # 이벤트 리스너 등록
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

        # 자정 카운터 리셋 작업
        self.scheduler.add_job(
            self._reset_daily_counter,
            trigger=CronTrigger(hour=0, minute=0),
            id="daily_reset",
        )

        # 정기 헬스체크 (1시간마다)
        self.scheduler.add_job(
            self._run_health_check, trigger=IntervalTrigger(hours=1), id="health_check"
        )

        # 빠른 리소스 체크 (15분마다 - CPU, 메모리, 디스크만)
        self.scheduler.add_job(
            self._run_quick_resource_check,
            trigger=IntervalTrigger(minutes=15),
            id="quick_resource_check",
        )

        # 세션 상태 체크 (3시간마다)
        self.scheduler.add_job(
            self._check_session_status,
            trigger=IntervalTrigger(hours=3),
            id="session_check",
        )

        # 일간 리포트 (매일 저녁 9시)
        self.scheduler.add_job(
            self._send_daily_report,
            trigger=CronTrigger(hour=21, minute=0),
            id="daily_report",
        )

        # 주간 리포트 (매주 일요일 저녁 8시)
        self.scheduler.add_job(
            self._send_weekly_report,
            trigger=CronTrigger(day_of_week="sun", hour=20, minute=0),
            id="weekly_report",
        )

        # 첫 포스팅 즉시 스케줄
        self._schedule_next_post()

        # 스케줄러 시작
        self.scheduler.start()
        logger.info("AsyncIOScheduler 시작됨")

        # 시작 시 헬스체크 및 시작 알림 전송
        try:
            await self._run_health_check()
            await self._send_startup_alert()
        except Exception as e:
            logger.warning(f"초기 헬스체크/시작 알림 실패: {e}")

        # 시그널 핸들러 등록
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self._async_shutdown(s))
            )

        # 무한 대기 (스케줄러가 백그라운드에서 실행됨)
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("메인 루프 취소됨")
        finally:
            await self._async_cleanup()

    async def _async_shutdown(self, sig):
        """비동기 종료 처리"""
        logger.info(f"시그널 수신: {sig}")
        self.is_running = False

    async def _async_cleanup(self):
        """비동기 정리 작업"""
        logger.info("=" * 60)
        logger.info("⏹ 스케줄러 종료 중...")

        uptime_str = "알 수 없음"
        if self.start_time:
            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split(".")[0]
            logger.info(f"   가동 시간: {uptime_str}")
            logger.info(f"   총 포스팅: {self.total_posts}개")
            logger.info(f"   오류 횟수: {self.errors_count}")

        # 종료 알림 전송
        try:
            await self._send_shutdown_alert(uptime_str)
        except Exception as e:
            logger.warning(f"종료 알림 전송 실패: {e}")

        self.scheduler.shutdown(wait=False)
        logger.info("👋 스케줄러 종료 완료")
        logger.info("=" * 60)

    async def _send_startup_alert(self):
        """시작 알림 전송 (강화 버전)"""
        try:
            from utils.telegram_notifier import get_notifier, AlertLevel

            notifier = get_notifier()

            # 시스템 메트릭 수집
            metrics = self.health_checker.get_system_metrics()

            message = f"👤 계정: {self.naver_id}\n"
            message += f"⏰ 포스팅 간격: {self.min_interval}-{self.max_interval}시간\n"
            message += f"📊 일일 제한: {self.daily_limit}개\n"
            message += f"🤖 모델: {self.model}\n"
            message += f"📱 텔레그램 알림: {'ON' if self.telegram_enabled else 'OFF'}\n"
            message += f"👥 다중 계정: {'ON' if self.multi_account else 'OFF'}\n\n"

            message += "📊 시스템 상태:\n"
            if "cpu" in metrics:
                message += f"  • CPU: {metrics['cpu']['percent']}%\n"
            if "memory" in metrics:
                message += f"  • 메모리: {metrics['memory']['percent']}%\n"
            if "disk" in metrics:
                message += f"  • 디스크: {metrics['disk']['percent']}%\n"

            # 헬스체크 결과 요약
            health_report = self.health_checker.get_status_report()
            overall = health_report.get("overall_status", "unknown")
            status_emoji = (
                "✅" if overall == "healthy" else "⚠️" if overall == "warning" else "❌"
            )
            message += f"\n{status_emoji} 헬스체크: {overall.upper()}"

            await notifier.send_alert(
                title="🚀 블로그 봇 시작",
                message=message,
                level=AlertLevel.SUCCESS,
                alert_key="startup",
            )

            logger.info("시작 알림 전송 완료")

        except Exception as e:
            logger.warning(f"시작 알림 전송 실패: {e}")

    def stop(self):
        """스케줄러 중지 (동기 인터페이스)"""
        self.is_running = False

    async def _send_shutdown_alert(self, uptime_str: str):
        """종료 알림 전송"""
        try:
            from utils.telegram_notifier import get_notifier, AlertLevel

            notifier = get_notifier()

            message = f"📈 총 포스팅: {self.total_posts}개\n"
            message += f"✅ 오늘 포스팅: {self.posts_today}개\n"
            message += f"❌ 총 오류: {self.errors_count}회\n"
            message += f"⏱ 가동 시간: {uptime_str}\n"

            # 에러 통계
            if self.error_recovery.error_history:
                error_stats = self.error_recovery._get_error_type_summary()
                message += f"\n📊 에러 유형별:\n{error_stats}"

            await notifier.send_alert(
                title="⏹ 블로그 봇 종료",
                message=message,
                level=AlertLevel.INFO,
                alert_key="shutdown",
            )

        except Exception as e:
            logger.warning(f"종료 알림 전송 실패: {e}")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        status = {
            "running": self.scheduler.running,
            "posts_today": self.posts_today,
            "total_posts": self.total_posts,
            "errors_count": self.errors_count,
            "last_post_time": self.last_post_time.isoformat()
            if self.last_post_time
            else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "daily_limit": self.daily_limit,
            "multi_account": self.multi_account,
            "error_recovery": self.error_recovery.get_status(),
        }

        # 다중 계정 모드 상태
        if self.multi_account and self.account_manager:
            status["accounts"] = self.account_manager.get_account_status()

        # 헬스 상태
        status["health"] = self.health_checker.get_status_report()

        return status


# ============================================
# CLI 진입점
# ============================================


def main():
    """CLI 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="24시간 자동 블로그 포스팅 스케줄러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python -m scheduler.auto_scheduler                    # 기본 설정으로 실행
  python -m scheduler.auto_scheduler --interval 1 2    # 1-2시간 간격
  python -m scheduler.auto_scheduler --limit 10        # 일일 10개 제한
  python -m scheduler.auto_scheduler --test            # 테스트 모드 (1회 실행)
        """,
    )

    parser.add_argument("--naver-id", default="wncksdid0750", help="네이버 계정 ID")

    parser.add_argument(
        "--interval",
        type=float,
        nargs=2,
        default=[1.0, 2.0],
        metavar=("MIN", "MAX"),
        help="포스팅 간격 (시간), 기본값: 1-2시간",
    )

    parser.add_argument(
        "--limit", type=int, default=12, help="일일 최대 포스팅 수, 기본값: 12"
    )

    parser.add_argument(
        "--model",
        choices=["haiku", "sonnet"],
        default="haiku",
        help="글쓰기 모델, 기본값: haiku",
    )

    parser.add_argument(
        "--no-telegram", action="store_true", help="텔레그램 알림 비활성화"
    )

    parser.add_argument(
        "--test", action="store_true", help="테스트 모드 (1회 포스팅 후 종료)"
    )

    parser.add_argument(
        "--multi-account",
        action="store_true",
        help="다중 계정 모드 활성화 (NAVER_ACCOUNTS 환경변수 필요)",
    )

    args = parser.parse_args()

    # 스케줄러 생성
    scheduler = AutoPostingScheduler(
        naver_id=args.naver_id,
        min_interval_hours=args.interval[0],
        max_interval_hours=args.interval[1],
        daily_limit=args.limit,
        model=args.model,
        telegram_enabled=not args.no_telegram,
        multi_account=args.multi_account,
    )

    if args.test:
        # 테스트 모드: 1회 실행
        logger.info("🧪 테스트 모드 - 1회 포스팅 후 종료")
        asyncio.run(scheduler._post_job())
    else:
        # 정상 모드: 24시간 실행
        scheduler.start(blocking=True)


if __name__ == "__main__":
    main()
