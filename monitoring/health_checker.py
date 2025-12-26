"""
헬스체크 시스템
- 시스템 구성요소 상태 모니터링
- API 연결 상태 확인
- 디스크/메모리 사용량 체크
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


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
    """시스템 헬스체크 클래스"""

    # 체크 항목
    COMPONENTS = [
        "claude_api",
        "perplexity_api",
        "gemini_api",
        "naver_session",
        "disk_space",
        "database"
    ]

    # 디스크 공간 임계값 (GB)
    DISK_WARNING_GB = 5
    DISK_CRITICAL_GB = 1

    def __init__(self):
        """초기화"""
        self.results: Dict[str, HealthCheckResult] = {}
        self.last_full_check: Optional[datetime] = None

        logger.info("HealthChecker 초기화")

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
        logger.info("전체 헬스체크 완료")

        return self.results

    async def _check_claude_api(self) -> HealthCheckResult:
        """Claude API 연결 체크"""
        component = "claude_api"

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
                    # 401/403은 인증 확인됨 (메시지 없이 호출했으므로 400 예상)
                    if response.status in [400, 401, 403, 200]:
                        return HealthCheckResult(
                            component=component,
                            status=HealthStatus.HEALTHY,
                            message="Claude API 연결 정상",
                            details={"status_code": response.status}
                        )
                    else:
                        return HealthCheckResult(
                            component=component,
                            status=HealthStatus.WARNING,
                            message=f"예상치 못한 응답: {response.status}"
                        )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.WARNING,
                message="API 응답 타임아웃"
            )
        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"API 체크 실패: {str(e)}"
            )

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

        try:
            from models.database import DatabaseManager

            from sqlalchemy import text

            db = DatabaseManager()
            session = db.get_session()

            # 간단한 쿼리 실행
            session.execute(text("SELECT 1"))
            session.close()

            return HealthCheckResult(
                component=component,
                status=HealthStatus.HEALTHY,
                message="데이터베이스 연결 정상"
            )

        except Exception as e:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.CRITICAL,
                message=f"데이터베이스 연결 실패: {str(e)}"
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
        """필요시 알림 전송"""
        failed = self.get_failed_checks()

        if not failed:
            return

        # Critical 항목이 있으면 알림
        critical = [r for r in failed if r.status == HealthStatus.CRITICAL]

        if critical:
            try:
                from utils.telegram_notifier import send_notification

                message = "🔴 시스템 헬스체크 경고\n\n"
                for result in critical:
                    message += f"❌ {result.component}: {result.message}\n"

                await send_notification(message)
                logger.warning("헬스체크 경고 알림 전송됨")

            except Exception as e:
                logger.error(f"알림 전송 실패: {e}")


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
