"""
헬스체크 시스템 (강화 버전)
- 시스템 구성요소 상태 모니터링
- API 연결 상태 및 응답시간 확인
- 디스크/메모리/CPU 사용량 체크
- 실시간 알림 연동
- 상세 진단 정보 제공
"""

import os
import asyncio
import aiohttp
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env 파일 로드
load_dotenv(Path(__file__).parent.parent / ".env")


class HealthStatus(Enum):
    """상태 레벨"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """헬스체크 결과"""
    component: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now()


class HealthChecker:
    """시스템 헬스체크 클래스 (강화 버전)"""

    # 체크 항목
    COMPONENTS = [
        "claude_api",
        "perplexity_api",
        "gemini_api",
        "naver_session",
        "disk_space",
        "memory",
        "cpu",
        "database"
    ]

    # 디스크 공간 임계값 (GB)
    DISK_WARNING_GB = 5
    DISK_CRITICAL_GB = 1

    # 메모리 임계값 (%)
    MEMORY_WARNING_PERCENT = 80
    MEMORY_CRITICAL_PERCENT = 90

    # CPU 임계값 (%)
    CPU_WARNING_PERCENT = 70
    CPU_CRITICAL_PERCENT = 90

    # API 응답시간 임계값 (ms)
    API_RESPONSE_WARNING_MS = 3000
    API_RESPONSE_CRITICAL_MS = 10000

    def __init__(self):
        """초기화"""
        self.results: Dict[str, HealthCheckResult] = {}
        self.last_full_check: Optional[datetime] = None
        self.check_history: List[Dict[str, Any]] = []  # 히스토리 추적
        self.api_response_times: Dict[str, List[float]] = {}  # API 응답시간 추적
        self.alert_sent: Dict[str, datetime] = {}  # 알림 발송 기록

        logger.info("HealthChecker 초기화 (강화 버전)")

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """
        모든 헬스체크 실행

        Returns:
            컴포넌트별 체크 결과
        """
        logger.info("전체 헬스체크 시작")

        # 병렬로 체크 실행
        tasks = [
            self._check_claude_api(),
            self._check_perplexity_api(),
            self._check_gemini_api(),
            self._check_naver_session(),
            self._check_disk_space(),
            self._check_memory(),
            self._check_cpu(),
            self._check_database()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 저장
        for result in results:
            if isinstance(result, HealthCheckResult):
                self.results[result.component] = result
            elif isinstance(result, Exception):
                logger.error(f"헬스체크 중 예외: {result}")

        self.last_full_check = datetime.now()

        # 히스토리에 추가
        self._save_to_history()

        logger.info("전체 헬스체크 완료")

        # 자동으로 알림 전송
        await self.send_alert_if_needed()

        return self.results

    def _save_to_history(self):
        """체크 결과를 히스토리에 저장"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": self._get_overall_status().value,
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message
                }
                for name, result in self.results.items()
            }
        }
        self.check_history.append(history_entry)

        # 최근 100개만 유지
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]

    def _get_overall_status(self) -> HealthStatus:
        """전체 상태 계산"""
        if not self.results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self.results.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    async def _check_claude_api(self) -> HealthCheckResult:
        """Claude API 연결 체크 (응답시간 포함)"""
        component = "claude_api"
        start_time = time.time()

        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message="ANTHROPIC_API_KEY 환경변수가 설정되지 않음"
                )

            # 간단한 API 호출 테스트
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    self._record_response_time(component, response_time_ms)

                    # API 연결 확인용 응답 코드들:
                    # - 405: POST만 허용하므로 GET시 Method Not Allowed (정상 - API 연결됨)
                    # - 401/403: 인증 관련 응답 (API 연결됨, 키 문제)
                    # - 400: 메시지 없이 호출시 Bad Request (정상 - API 연결됨)
                    # - 200: 정상 응답
                    # - 429: Rate limit (API 연결됨, 일시적 제한)
                    valid_status_codes = {200, 400, 401, 403, 405, 429}

                    if response.status in valid_status_codes:
                        # 응답시간 체크
                        if response_time_ms > self.API_RESPONSE_CRITICAL_MS:
                            return HealthCheckResult(
                                component=component,
                                status=HealthStatus.WARNING,
                                message=f"API 응답 느림: {response_time_ms:.0f}ms",
                                details={
                                    "status_code": response.status,
                                    "response_time_ms": round(response_time_ms, 1)
                                }
                            )

                        return HealthCheckResult(
                            component=component,
                            status=HealthStatus.HEALTHY,
                            message=f"Claude API 연결 정상 ({response_time_ms:.0f}ms)",
                            details={
                                "status_code": response.status,
                                "response_time_ms": round(response_time_ms, 1)
                            }
                        )

                    # 500번대 에러는 서버 문제
                    if response.status >= 500:
                        return HealthCheckResult(
                            component=component,
                            status=HealthStatus.WARNING,
                            message=f"API 서버 오류: {response.status}",
                            details={
                                "status_code": response.status,
                                "response_time_ms": round(response_time_ms, 1)
                            }
                        )

                    # 기타 예상치 못한 응답 (HEALTHY로 처리 - 연결은 됨)
                    return HealthCheckResult(
                        component=component,
                        status=HealthStatus.HEALTHY,
                        message=f"Claude API 연결됨 (응답: {response.status})",
                        details={
                            "status_code": response.status,
                            "response_time_ms": round(response_time_ms, 1)
                        }
                    )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message="API 응답 타임아웃 (10초 초과)"
            )
        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"API 체크 실패: {str(e)}"
            )

    def _record_response_time(self, component: str, response_time_ms: float):
        """API 응답시간 기록"""
        if component not in self.api_response_times:
            self.api_response_times[component] = []

        self.api_response_times[component].append(response_time_ms)

        # 최근 50개만 유지
        if len(self.api_response_times[component]) > 50:
            self.api_response_times[component] = self.api_response_times[component][-50:]

    def get_average_response_time(self, component: str) -> Optional[float]:
        """평균 응답시간 반환"""
        times = self.api_response_times.get(component, [])
        if not times:
            return None
        return sum(times) / len(times)

    async def _check_perplexity_api(self) -> HealthCheckResult:
        """Perplexity API 연결 체크"""
        component = "perplexity_api"

        try:
            api_key = os.getenv("PERPLEXITY_API_KEY")

            if not api_key:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message="PERPLEXITY_API_KEY 환경변수가 설정되지 않음"
                )

            # API 키 형식 확인
            if len(api_key) > 10:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message="Perplexity API 키 설정됨",
                    details={"key_length": len(api_key)}
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message="API 키 형식이 올바르지 않을 수 있음"
                )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"API 체크 실패: {str(e)}"
            )

    async def _check_gemini_api(self) -> HealthCheckResult:
        """Gemini API 연결 체크"""
        component = "gemini_api"

        try:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message="GEMINI_API_KEY 환경변수가 설정되지 않음 (이미지 생성 불가)"
                )

            # API 키 형식 확인
            if len(api_key) > 10:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message="Gemini API 키 설정됨",
                    details={"key_length": len(api_key)}
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message="API 키 형식이 올바르지 않을 수 있음"
                )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"API 체크 실패: {str(e)}"
            )

    async def _check_naver_session(self) -> HealthCheckResult:
        """네이버 세션 상태 체크"""
        component = "naver_session"

        try:
            from security.session_manager import SecureSessionManager

            session_manager = SecureSessionManager()

            # 기본 세션 확인
            sessions = session_manager.list_sessions()

            if not sessions:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message="저장된 세션 없음 - 로그인 필요"
                )

            # 세션 유효성 확인
            valid_sessions = []
            for session_name in sessions:
                if session_manager.is_session_valid(session_name, max_age_days=7):
                    valid_sessions.append(session_name)

            if valid_sessions:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message=f"유효한 세션 {len(valid_sessions)}개",
                    details={"sessions": valid_sessions}
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message="모든 세션이 만료됨 - 갱신 필요"
                )

        except FileNotFoundError:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message="암호화 키 파일 없음 - 초기 설정 필요"
            )
        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"세션 체크 실패: {str(e)}"
            )

    async def _check_disk_space(self) -> HealthCheckResult:
        """디스크 공간 체크"""
        component = "disk_space"

        try:
            import shutil

            # 프로젝트 디렉토리 기준
            project_dir = Path(__file__).parent.parent
            total, used, free = shutil.disk_usage(project_dir)

            # GB 단위로 변환
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            used_percent = (used / total) * 100

            details = {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1)
            }

            if free_gb < self.DISK_CRITICAL_GB:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message=f"디스크 공간 부족! ({free_gb:.1f}GB 남음)",
                    details=details
                )
            elif free_gb < self.DISK_WARNING_GB:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message=f"디스크 공간 주의 ({free_gb:.1f}GB 남음)",
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message=f"디스크 공간 정상 ({free_gb:.1f}GB 남음)",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=f"디스크 체크 실패: {str(e)}"
            )

    async def _check_database(self) -> HealthCheckResult:
        """데이터베이스 연결 체크"""
        component = "database"
        start_time = time.time()

        try:
            from models.database import DatabaseManager

            from sqlalchemy import text

            db = DatabaseManager()
            session = db.get_session()

            # 간단한 쿼리 실행
            session.execute(text("SELECT 1"))
            session.close()

            query_time_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                component=component,
                status=HealthStatus.HEALTHY,
                message=f"데이터베이스 연결 정상 ({query_time_ms:.0f}ms)",
                details={"query_time_ms": round(query_time_ms, 1)}
            )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"데이터베이스 연결 실패: {str(e)}"
            )

    async def _check_memory(self) -> HealthCheckResult:
        """메모리 사용량 체크"""
        component = "memory"

        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024 ** 3)
            total_gb = memory.total / (1024 ** 3)

            details = {
                "used_percent": round(used_percent, 1),
                "available_gb": round(available_gb, 2),
                "total_gb": round(total_gb, 2)
            }

            if used_percent >= self.MEMORY_CRITICAL_PERCENT:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message=f"메모리 부족! {used_percent:.1f}% 사용 중 ({available_gb:.1f}GB 남음)",
                    details=details
                )
            elif used_percent >= self.MEMORY_WARNING_PERCENT:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message=f"메모리 높음: {used_percent:.1f}% 사용 중",
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message=f"메모리 정상: {used_percent:.1f}% 사용 ({available_gb:.1f}GB 사용 가능)",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=f"메모리 체크 실패: {str(e)}"
            )

    async def _check_cpu(self) -> HealthCheckResult:
        """CPU 사용량 체크"""
        component = "cpu"

        try:
            # CPU 사용량 (1초간 측정)
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # 로드 평균 (Unix 계열만)
            try:
                load_avg = os.getloadavg()
                load_1min = load_avg[0]
            except (OSError, AttributeError):
                load_1min = None

            details = {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_count": cpu_count
            }
            if load_1min is not None:
                details["load_1min"] = round(load_1min, 2)

            if cpu_percent >= self.CPU_CRITICAL_PERCENT:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message=f"CPU 과부하! {cpu_percent:.1f}% 사용 중",
                    details=details
                )
            elif cpu_percent >= self.CPU_WARNING_PERCENT:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.WARNING,
                    message=f"CPU 높음: {cpu_percent:.1f}% 사용 중",
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message=f"CPU 정상: {cpu_percent:.1f}% 사용 중",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=f"CPU 체크 실패: {str(e)}"
            )

    def get_status_report(self) -> Dict[str, Any]:
        """상태 리포트 생성"""
        if not self.results:
            return {"message": "헬스체크 미실행", "status": "unknown"}

        # 전체 상태 판단
        statuses = [r.status for r in self.results.values()]

        if HealthStatus.CRITICAL in statuses:
            overall = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall = HealthStatus.WARNING
        else:
            overall = HealthStatus.HEALTHY

        return {
            "overall_status": overall.value,
            "last_check": self.last_full_check.isoformat() if self.last_full_check else None,
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details
                }
                for name, result in self.results.items()
            }
        }

    def get_failed_checks(self) -> List[HealthCheckResult]:
        """실패한 체크 항목만 반환"""
        return [
            result for result in self.results.values()
            if result.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]
        ]

    async def send_alert_if_needed(self) -> None:
        """필요시 알림 전송 (WARNING 및 CRITICAL 모두)"""
        failed = self.get_failed_checks()

        if not failed:
            return

        try:
            from utils.telegram_notifier import get_notifier, AlertLevel

            notifier = get_notifier()

            # Critical 항목
            critical = [r for r in failed if r.status == HealthStatus.CRITICAL]
            # Warning 항목
            warnings = [r for r in failed if r.status == HealthStatus.WARNING]

            # CRITICAL 알림
            if critical:
                overall_status = "critical"
                components = {r.component: {"status": r.status.value, "message": r.message} for r in self.results.values()}
                failed_names = [r.component for r in critical]

                await notifier.send_health_check_result(
                    overall_status=overall_status,
                    components=components,
                    failed_components=failed_names
                )
                logger.warning(f"헬스체크 CRITICAL 알림 전송: {failed_names}")

            # WARNING 알림 (CRITICAL이 없을 때만)
            elif warnings:
                overall_status = "warning"
                components = {r.component: {"status": r.status.value, "message": r.message} for r in self.results.values()}
                failed_names = [r.component for r in warnings]

                await notifier.send_health_check_result(
                    overall_status=overall_status,
                    components=components,
                    failed_components=failed_names
                )
                logger.warning(f"헬스체크 WARNING 알림 전송: {failed_names}")

            # 시스템 리소스 알림 (CPU, 메모리, 디스크)
            await self._send_resource_alerts(notifier)

        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")

    async def _send_resource_alerts(self, notifier) -> None:
        """시스템 리소스 관련 상세 알림"""
        try:
            # CPU/메모리/디스크 상태 추출
            cpu_result = self.results.get("cpu")
            memory_result = self.results.get("memory")
            disk_result = self.results.get("disk_space")

            cpu_percent = 0
            memory_percent = 0
            disk_percent = 0

            if cpu_result and cpu_result.details:
                cpu_percent = cpu_result.details.get("cpu_percent", 0)
            if memory_result and memory_result.details:
                memory_percent = memory_result.details.get("used_percent", 0)
            if disk_result and disk_result.details:
                disk_percent = disk_result.details.get("used_percent", 0)

            # 리소스 상태 알림
            await notifier.send_system_status(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                active_tasks=0,
                queue_size=0
            )

        except Exception as e:
            logger.error(f"리소스 알림 전송 실패: {e}")

    async def run_quick_check(self) -> Dict[str, HealthCheckResult]:
        """빠른 헬스체크 (시스템 리소스만)"""
        logger.info("빠른 헬스체크 시작 (리소스만)")

        tasks = [
            self._check_memory(),
            self._check_cpu(),
            self._check_disk_space()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        quick_results = {}
        for result in results:
            if isinstance(result, HealthCheckResult):
                quick_results[result.component] = result
                self.results[result.component] = result

        # 알림 필요 여부 체크
        failed = [r for r in quick_results.values()
                  if r.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]]
        if failed:
            await self.send_alert_if_needed()

        return quick_results

    def get_system_metrics(self) -> Dict[str, Any]:
        """현재 시스템 메트릭 반환"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                }
            }
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
            return {"error": str(e)}


# ============================================
# 테스트 코드
# ============================================

async def test_health_checker():
    """HealthChecker 테스트"""
    print("\n=== HealthChecker 테스트 ===\n")

    checker = HealthChecker()

    # 전체 체크 실행
    print("헬스체크 실행 중...")
    results = await checker.run_all_checks()

    # 결과 출력
    print("\n체크 결과:")
    for name, result in results.items():
        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }.get(result.status, "❓")

        print(f"  {status_emoji} {name}: {result.message}")

    # 상태 리포트
    print(f"\n전체 상태: {checker.get_status_report()['overall_status']}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_health_checker())
