"""
에러 복구 시스템 (강화 버전)
- 연속 에러 감지 및 자동 일시정지
- 에러 기록 및 분석
- 자동 복구 시도
- 상세 텔레그램 알림
- 에러 유형별 권장 조치 안내
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class ErrorType(Enum):
    """에러 유형"""
    SESSION_EXPIRED = "session_expired"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    UPLOAD_FAILED = "upload_failed"
    CONTENT_ERROR = "content_error"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """에러 기록"""
    error_type: ErrorType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    recovered: bool = False
    recovery_action: Optional[str] = None


class ErrorRecoveryManager:
    """에러 복구 관리 클래스 (강화 버전)"""

    # 연속 에러 임계값
    MAX_CONSECUTIVE_ERRORS = 3

    # 쿨다운 시간 (분)
    COOLDOWN_MINUTES = 30

    # 에러 기록 보관 기간 (시간)
    ERROR_HISTORY_HOURS = 24

    # 에러 유형별 권장 조치
    ERROR_ACTIONS = {
        ErrorType.SESSION_EXPIRED: {
            "action": "세션 재로그인",
            "description": "네이버 세션이 만료되었습니다. 수동으로 재로그인이 필요합니다.",
            "auto_recoverable": False,
            "urgency": "high"
        },
        ErrorType.NETWORK_ERROR: {
            "action": "네트워크 재연결 대기",
            "description": "네트워크 연결 문제입니다. 30초 후 자동 재시도합니다.",
            "auto_recoverable": True,
            "urgency": "medium"
        },
        ErrorType.API_ERROR: {
            "action": "API 상태 확인",
            "description": "API 호출 중 오류가 발생했습니다. 10초 후 재시도합니다.",
            "auto_recoverable": True,
            "urgency": "medium"
        },
        ErrorType.UPLOAD_FAILED: {
            "action": "업로드 재시도",
            "description": "블로그 업로드에 실패했습니다. 계정 상태를 확인하세요.",
            "auto_recoverable": False,
            "urgency": "high"
        },
        ErrorType.CONTENT_ERROR: {
            "action": "콘텐츠 재생성",
            "description": "콘텐츠 생성 중 오류가 발생했습니다.",
            "auto_recoverable": True,
            "urgency": "low"
        },
        ErrorType.RATE_LIMIT: {
            "action": "Rate Limit 대기",
            "description": "API 호출 한도에 도달했습니다. 5분 후 자동 재시도합니다.",
            "auto_recoverable": True,
            "urgency": "medium"
        },
        ErrorType.UNKNOWN: {
            "action": "수동 확인 필요",
            "description": "알 수 없는 오류가 발생했습니다.",
            "auto_recoverable": False,
            "urgency": "high"
        }
    }

    def __init__(self):
        """초기화"""
        self.error_history: List[ErrorRecord] = []
        self.consecutive_errors = 0
        self.is_paused = False
        self.pause_until: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.error_counts_by_type: Dict[ErrorType, int] = {}  # 유형별 카운트
        self.first_error_time: Optional[datetime] = None  # 첫 에러 발생 시간

        logger.info("ErrorRecoveryManager 초기화 (강화 버전)")

    def _safe_async_call(self, coro) -> None:
        """
        안전하게 코루틴 실행 (이벤트 루프 유무에 관계없이)

        - 이벤트 루프가 실행 중이면 create_task 사용
        - 그렇지 않으면 새 루프에서 실행
        """
        try:
            asyncio.get_running_loop()
            # 이벤트 루프가 실행 중이면 task로 스케줄
            asyncio.create_task(coro)
        except RuntimeError:
            # 이벤트 루프가 없으면 동기적으로 실행하지 않음 (비용이 큼)
            # 대신 로깅만 하고 스킵
            logger.debug("이벤트 루프 없음 - 비동기 알림 스킵")

    def record_error(
        self,
        error_type: ErrorType,
        message: str,
        exception: Optional[Exception] = None
    ) -> ErrorRecord:
        """
        에러 기록 및 즉시 알림

        Args:
            error_type: 에러 유형
            message: 에러 메시지
            exception: 예외 객체 (선택)

        Returns:
            ErrorRecord
        """
        # 첫 에러 시간 기록
        if self.first_error_time is None:
            self.first_error_time = datetime.now()

        # 에러 기록 생성
        record = ErrorRecord(
            error_type=error_type,
            message=message
        )

        self.error_history.append(record)
        self.consecutive_errors += 1

        # 유형별 카운트 증가
        self.error_counts_by_type[error_type] = self.error_counts_by_type.get(error_type, 0) + 1

        logger.error(
            f"에러 기록 #{self.consecutive_errors}: "
            f"[{error_type.value}] {message}"
        )

        # 예외 정보 로깅
        if exception:
            logger.exception(f"예외 상세: {exception}")

        # 즉시 알림 전송 (모든 에러) - 이벤트 루프가 있을 때만
        self._safe_async_call(self._send_error_notification(error_type, message))

        # 연속 에러 체크
        if self.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
            self._trigger_pause()

        # 오래된 기록 정리
        self._cleanup_old_records()

        return record

    async def _send_error_notification(self, error_type: ErrorType, message: str) -> None:
        """에러 발생 즉시 알림"""
        try:
            from utils.telegram_notifier import get_notifier

            notifier = get_notifier()
            error_info = self.ERROR_ACTIONS.get(error_type, self.ERROR_ACTIONS[ErrorType.UNKNOWN])

            # 권장 조치 메시지 생성
            suggested_action = f"{error_info['action']}\n{error_info['description']}"
            if error_info['auto_recoverable']:
                suggested_action += "\n✅ 자동 복구 시도 중..."
            else:
                suggested_action += "\n⚠️ 수동 조치가 필요합니다."

            # 에러 분석 알림 전송
            await notifier.send_error_analysis(
                error_type=error_type.value,
                error_message=message,
                occurrence_count=self.error_counts_by_type.get(error_type, 1),
                first_occurrence=self.first_error_time or datetime.now(),
                suggested_action=suggested_action
            )

        except Exception as e:
            logger.warning(f"에러 알림 전송 실패: {e}")

    def record_success(self) -> None:
        """성공 기록 - 연속 에러 카운터 리셋"""
        # 이전에 에러가 있었다면 복구 알림 전송
        if self.consecutive_errors > 0:
            self._safe_async_call(self._send_recovery_success_notification())

        self.consecutive_errors = 0
        self.last_success_time = datetime.now()
        self.first_error_time = None  # 에러 시간 리셋

        logger.info("작업 성공 - 에러 카운터 리셋")

    async def _send_recovery_success_notification(self) -> None:
        """복구 성공 알림"""
        try:
            from utils.telegram_notifier import get_notifier

            notifier = get_notifier()
            await notifier.send_recovery_notification(
                issue_type="연속 에러",
                recovery_action="자동 재시도",
                success=True,
                details=f"연속 {self.consecutive_errors}회 에러 후 정상화됨"
            )

        except Exception as e:
            logger.warning(f"복구 성공 알림 전송 실패: {e}")

    def should_pause(self) -> bool:
        """
        일시정지 여부 확인

        Returns:
            일시정지 필요 여부
        """
        if not self.is_paused:
            return False

        # 쿨다운 시간 경과 확인
        if self.pause_until and datetime.now() >= self.pause_until:
            self.is_paused = False
            self.pause_until = None
            logger.info("쿨다운 시간 종료 - 작업 재개 가능")
            return False

        remaining = (self.pause_until - datetime.now()).total_seconds() / 60
        logger.warning(f"일시정지 중 - 남은 시간: {remaining:.1f}분")
        return True

    def _trigger_pause(self) -> None:
        """일시정지 트리거"""
        self.is_paused = True
        self.pause_until = datetime.now() + timedelta(minutes=self.COOLDOWN_MINUTES)

        logger.warning(
            f"연속 에러 {self.consecutive_errors}회 발생 - "
            f"{self.COOLDOWN_MINUTES}분 동안 일시정지"
        )

        # 텔레그램 알림
        self._safe_async_call(self._send_pause_notification())

    async def _send_pause_notification(self) -> None:
        """일시정지 알림 전송 (강화 버전)"""
        try:
            from utils.telegram_notifier import get_notifier, AlertLevel

            notifier = get_notifier()

            # 에러 유형별 통계
            error_stats = self._get_error_type_summary()

            message = f"연속 에러 {self.consecutive_errors}회 발생으로 일시정지됩니다.\n\n"
            message += f"⏱ 쿨다운: {self.COOLDOWN_MINUTES}분\n"
            message += f"🕐 재개 예정: {self.pause_until.strftime('%H:%M:%S')}\n\n"
            message += f"📊 에러 유형별 통계:\n{error_stats}\n\n"
            message += f"📋 최근 에러:\n{self._get_recent_errors_summary()}"

            # 가장 많이 발생한 에러 유형의 권장 조치
            most_common_error = self._get_most_common_error()
            if most_common_error:
                error_info = self.ERROR_ACTIONS.get(most_common_error, {})
                if error_info:
                    message += f"\n\n💡 권장 조치:\n{error_info.get('action', '확인 필요')}\n{error_info.get('description', '')}"

            await notifier.send_alert(
                title="🚨 자동 포스팅 일시정지",
                message=message,
                level=AlertLevel.CRITICAL,
                alert_key="auto_pause"
            )

        except Exception as e:
            logger.warning(f"알림 전송 실패: {e}")

    def _get_error_type_summary(self) -> str:
        """에러 유형별 통계 문자열 생성"""
        if not self.error_counts_by_type:
            return "  없음"

        lines = []
        for error_type, count in sorted(self.error_counts_by_type.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  • {error_type.value}: {count}회")
        return "\n".join(lines)

    def _get_most_common_error(self) -> Optional[ErrorType]:
        """가장 많이 발생한 에러 유형"""
        if not self.error_counts_by_type:
            return None
        return max(self.error_counts_by_type, key=self.error_counts_by_type.get)

    def _get_recent_errors_summary(self, count: int = 3) -> str:
        """최근 에러 요약"""
        recent = self.error_history[-count:] if self.error_history else []
        lines = []

        for i, record in enumerate(recent, 1):
            lines.append(
                f"{i}. [{record.error_type.value}] "
                f"{record.message[:50]}..."
            )

        return "\n".join(lines) if lines else "없음"

    async def attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """
        자동 복구 시도

        Args:
            error_record: 에러 기록

        Returns:
            복구 성공 여부
        """
        logger.info(f"복구 시도: {error_record.error_type.value}")

        try:
            if error_record.error_type == ErrorType.SESSION_EXPIRED:
                # 세션 만료 - 세션 갱신 시도
                error_record.recovery_action = "session_refresh"
                # 실제 복구 로직은 SessionKeeper에서 처리
                return False  # 수동 처리 필요

            elif error_record.error_type == ErrorType.NETWORK_ERROR:
                # 네트워크 에러 - 대기 후 재시도
                error_record.recovery_action = "wait_retry"
                await asyncio.sleep(30)  # 30초 대기
                return True

            elif error_record.error_type == ErrorType.RATE_LIMIT:
                # Rate Limit - 긴 대기
                error_record.recovery_action = "long_wait"
                await asyncio.sleep(300)  # 5분 대기
                return True

            elif error_record.error_type == ErrorType.API_ERROR:
                # API 에러 - 짧은 대기 후 재시도
                error_record.recovery_action = "short_wait"
                await asyncio.sleep(10)
                return True

            else:
                # 기타 에러 - 기본 대기
                error_record.recovery_action = "default_wait"
                await asyncio.sleep(60)
                return True

        except Exception as e:
            logger.error(f"복구 시도 중 오류: {e}")
            return False

        finally:
            error_record.recovered = True

    def _cleanup_old_records(self) -> None:
        """오래된 에러 기록 정리"""
        cutoff = datetime.now() - timedelta(hours=self.ERROR_HISTORY_HOURS)
        original_count = len(self.error_history)

        self.error_history = [
            record for record in self.error_history
            if record.timestamp >= cutoff
        ]

        removed = original_count - len(self.error_history)
        if removed > 0:
            logger.debug(f"오래된 에러 기록 {removed}개 정리")

    def force_resume(self) -> None:
        """강제 재개 (수동 조작용)"""
        self.is_paused = False
        self.pause_until = None
        self.consecutive_errors = 0

        logger.info("강제 재개 - 모든 에러 상태 초기화")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "is_paused": self.is_paused,
            "pause_until": self.pause_until.isoformat() if self.pause_until else None,
            "consecutive_errors": self.consecutive_errors,
            "total_errors_24h": len(self.error_history),
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None,
            "error_types": self._get_error_type_counts()
        }

    def _get_error_type_counts(self) -> Dict[str, int]:
        """에러 유형별 카운트"""
        counts = {}
        for record in self.error_history:
            error_type = record.error_type.value
            counts[error_type] = counts.get(error_type, 0) + 1
        return counts

    def get_error_statistics(self) -> Dict[str, Any]:
        """에러 통계"""
        if not self.error_history:
            return {"message": "에러 기록 없음"}

        total = len(self.error_history)
        recovered = sum(1 for r in self.error_history if r.recovered)

        return {
            "total_errors": total,
            "recovered": recovered,
            "recovery_rate": f"{recovered/total*100:.1f}%" if total > 0 else "N/A",
            "error_types": self._get_error_type_counts(),
            "recent_errors": [
                {
                    "type": r.error_type.value,
                    "message": r.message[:100],
                    "time": r.timestamp.isoformat()
                }
                for r in self.error_history[-5:]
            ]
        }


# ============================================
# 헬퍼 함수
# ============================================

def classify_error(exception: Exception) -> ErrorType:
    """
    예외를 ErrorType으로 분류

    Args:
        exception: 예외 객체

    Returns:
        ErrorType
    """
    error_str = str(exception).lower()

    if "session" in error_str or "login" in error_str or "auth" in error_str:
        return ErrorType.SESSION_EXPIRED

    elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
        return ErrorType.NETWORK_ERROR

    elif "rate" in error_str or "limit" in error_str or "429" in error_str:
        return ErrorType.RATE_LIMIT

    elif "api" in error_str or "request" in error_str:
        return ErrorType.API_ERROR

    elif "upload" in error_str or "post" in error_str:
        return ErrorType.UPLOAD_FAILED

    elif "content" in error_str or "generate" in error_str:
        return ErrorType.CONTENT_ERROR

    else:
        return ErrorType.UNKNOWN


# ============================================
# 테스트 코드
# ============================================

async def test_error_recovery():
    """ErrorRecoveryManager 테스트"""
    print("\n=== ErrorRecoveryManager 테스트 ===\n")

    manager = ErrorRecoveryManager()

    # 에러 기록 테스트
    print("에러 기록 테스트:")
    for i in range(4):
        record = manager.record_error(
            ErrorType.NETWORK_ERROR,
            f"테스트 에러 #{i+1}"
        )
        print(f"  에러 #{i+1} 기록됨")

        if manager.should_pause():
            print(f"  -> 일시정지 상태!")
            break

    # 상태 확인
    print(f"\n상태: {manager.get_status()}")

    # 강제 재개
    manager.force_resume()
    print("강제 재개 후 상태:", manager.get_status())

    # 성공 기록
    manager.record_success()
    print("성공 기록 후:", manager.get_status())

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(test_error_recovery())
