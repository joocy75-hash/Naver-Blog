"""
다중 계정 관리 시스템
- 계정 순환 사용
- 계정별 상태 관리
- 계정 쿨다운 관리
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import DatabaseManager, DBSession, Account


@dataclass
class AccountInfo:
    """계정 정보"""
    naver_id: str
    blog_id: Optional[str] = None
    status: str = "active"  # active, cooldown, suspended, banned
    last_post_at: Optional[datetime] = None
    today_post_count: int = 0
    cooldown_until: Optional[datetime] = None
    error_count: int = 0


class AccountManager:
    """다중 계정 관리 클래스"""

    # 계정당 일일 최대 포스팅 수
    MAX_DAILY_POSTS_PER_ACCOUNT = 5

    # 포스팅 후 쿨다운 시간 (분)
    POST_COOLDOWN_MINUTES = 60

    # 에러 발생 시 쿨다운 시간 (분)
    ERROR_COOLDOWN_MINUTES = 120

    # 최대 연속 에러 횟수
    MAX_CONSECUTIVE_ERRORS = 3

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Args:
            db: DatabaseManager 인스턴스 (None이면 자동 생성)
        """
        self.db = db or DatabaseManager()
        self.accounts: Dict[str, AccountInfo] = {}

        # 환경변수에서 계정 목록 로드
        self._load_accounts()

        logger.info(f"AccountManager 초기화: {len(self.accounts)}개 계정")

    def _load_accounts(self) -> None:
        """환경변수에서 계정 목록 로드"""
        # NAVER_ACCOUNTS 형식: "id1:blog1,id2:blog2,..."
        accounts_str = os.getenv("NAVER_ACCOUNTS", "")

        if accounts_str:
            for account_pair in accounts_str.split(","):
                parts = account_pair.strip().split(":")
                if len(parts) >= 1:
                    naver_id = parts[0].strip()
                    blog_id = parts[1].strip() if len(parts) > 1 else None

                    self.accounts[naver_id] = AccountInfo(
                        naver_id=naver_id,
                        blog_id=blog_id
                    )
                    logger.debug(f"계정 로드: {naver_id}")

        # 기본 계정 (NAVER_ID 환경변수)
        default_id = os.getenv("NAVER_ID")
        if default_id and default_id not in self.accounts:
            self.accounts[default_id] = AccountInfo(
                naver_id=default_id,
                blog_id=os.getenv("NAVER_BLOG_ID")
            )
            logger.debug(f"기본 계정 로드: {default_id}")

        # DB에서 계정 상태 동기화
        self._sync_from_database()

    def _sync_from_database(self) -> None:
        """데이터베이스에서 계정 상태 동기화"""
        try:
            with DBSession(self.db) as session:
                for naver_id, account_info in self.accounts.items():
                    db_account = session.query(Account).filter(
                        Account.naver_id == naver_id
                    ).first()

                    if db_account:
                        account_info.status = db_account.status
                        account_info.last_post_at = db_account.last_post_at

                        # 오늘 포스팅 수 계산
                        today_start = datetime.now().replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        if db_account.last_post_at and db_account.last_post_at >= today_start:
                            # 실제로는 Post 테이블에서 계산해야 함
                            pass

        except Exception as e:
            logger.warning(f"계정 상태 동기화 실패: {e}")

    def get_next_account(self) -> Optional[AccountInfo]:
        """
        다음 사용할 계정 반환 (라운드 로빈 + 쿨다운 고려)

        Returns:
            사용 가능한 계정 정보 또는 None
        """
        available_accounts = self._get_available_accounts()

        if not available_accounts:
            logger.warning("사용 가능한 계정이 없습니다")
            return None

        # 마지막 포스팅이 가장 오래된 계정 선택
        selected = min(
            available_accounts,
            key=lambda x: x.last_post_at or datetime.min
        )

        logger.info(f"다음 사용 계정 선택: {selected.naver_id}")
        return selected

    def get_best_account(self) -> Optional[AccountInfo]:
        """
        최적 계정 반환 (오늘 포스팅 수 적은 순 + 쿨다운 고려)

        Returns:
            최적 계정 정보 또는 None
        """
        available_accounts = self._get_available_accounts()

        if not available_accounts:
            logger.warning("사용 가능한 계정이 없습니다")
            return None

        # 오늘 포스팅 수가 적고, 마지막 포스팅이 오래된 순
        selected = min(
            available_accounts,
            key=lambda x: (x.today_post_count, x.last_post_at or datetime.min)
        )

        logger.info(f"최적 계정 선택: {selected.naver_id} (오늘 {selected.today_post_count}회 포스팅)")
        return selected

    def _get_available_accounts(self) -> List[AccountInfo]:
        """사용 가능한 계정 목록 반환"""
        now = datetime.now()
        available = []

        for account in self.accounts.values():
            # 상태 체크
            if account.status not in ["active"]:
                continue

            # 쿨다운 체크
            if account.cooldown_until and account.cooldown_until > now:
                remaining = (account.cooldown_until - now).total_seconds() / 60
                logger.debug(f"{account.naver_id}: 쿨다운 중 (남은 시간: {remaining:.1f}분)")
                continue

            # 일일 제한 체크
            if account.today_post_count >= self.MAX_DAILY_POSTS_PER_ACCOUNT:
                logger.debug(f"{account.naver_id}: 일일 제한 도달")
                continue

            available.append(account)

        return available

    def record_post_success(self, naver_id: str) -> None:
        """
        포스팅 성공 기록

        Args:
            naver_id: 계정 ID
        """
        if naver_id not in self.accounts:
            return

        account = self.accounts[naver_id]
        account.last_post_at = datetime.now()
        account.today_post_count += 1
        account.error_count = 0
        account.cooldown_until = datetime.now() + timedelta(minutes=self.POST_COOLDOWN_MINUTES)

        logger.info(
            f"포스팅 성공 기록: {naver_id} "
            f"(오늘 {account.today_post_count}회, "
            f"쿨다운 {self.POST_COOLDOWN_MINUTES}분)"
        )

        # DB 업데이트
        self._update_database(naver_id)

    def record_post_failure(self, naver_id: str) -> None:
        """
        포스팅 실패 기록

        Args:
            naver_id: 계정 ID
        """
        if naver_id not in self.accounts:
            return

        account = self.accounts[naver_id]
        account.error_count += 1
        account.cooldown_until = datetime.now() + timedelta(minutes=self.ERROR_COOLDOWN_MINUTES)

        # 연속 에러 시 계정 정지
        if account.error_count >= self.MAX_CONSECUTIVE_ERRORS:
            account.status = "suspended"
            logger.warning(f"계정 정지: {naver_id} (연속 에러 {account.error_count}회)")
        else:
            logger.warning(
                f"포스팅 실패 기록: {naver_id} "
                f"(에러 {account.error_count}회, 쿨다운 {self.ERROR_COOLDOWN_MINUTES}분)"
            )

    def _update_database(self, naver_id: str) -> None:
        """데이터베이스 계정 정보 업데이트"""
        try:
            with DBSession(self.db) as session:
                self.db.update_account_last_post(session, naver_id)
        except Exception as e:
            logger.error(f"DB 업데이트 실패: {e}")

    def reset_daily_counts(self) -> None:
        """일일 포스팅 카운트 리셋 (매일 자정 호출)"""
        for account in self.accounts.values():
            account.today_post_count = 0

        logger.info("모든 계정 일일 카운트 리셋")

    def reactivate_account(self, naver_id: str) -> bool:
        """
        정지된 계정 재활성화

        Args:
            naver_id: 계정 ID

        Returns:
            성공 여부
        """
        if naver_id not in self.accounts:
            return False

        account = self.accounts[naver_id]
        account.status = "active"
        account.error_count = 0
        account.cooldown_until = None

        logger.info(f"계정 재활성화: {naver_id}")
        return True

    def get_account_status(self, naver_id: Optional[str] = None) -> Dict[str, Any]:
        """
        계정 상태 조회

        Args:
            naver_id: 특정 계정 ID (None이면 전체)

        Returns:
            계정 상태 정보
        """
        if naver_id:
            if naver_id not in self.accounts:
                return {"error": "계정을 찾을 수 없습니다"}

            account = self.accounts[naver_id]
            return self._account_to_dict(account)

        # 전체 계정 상태
        return {
            "total_accounts": len(self.accounts),
            "available_accounts": len(self._get_available_accounts()),
            "accounts": {
                nid: self._account_to_dict(acc)
                for nid, acc in self.accounts.items()
            }
        }

    def _account_to_dict(self, account: AccountInfo) -> Dict[str, Any]:
        """AccountInfo를 딕셔너리로 변환"""
        now = datetime.now()

        return {
            "naver_id": account.naver_id,
            "blog_id": account.blog_id,
            "status": account.status,
            "last_post_at": account.last_post_at.isoformat() if account.last_post_at else None,
            "today_post_count": account.today_post_count,
            "error_count": account.error_count,
            "cooldown_until": account.cooldown_until.isoformat() if account.cooldown_until else None,
            "is_available": (
                account.status == "active" and
                (not account.cooldown_until or account.cooldown_until <= now) and
                account.today_post_count < self.MAX_DAILY_POSTS_PER_ACCOUNT
            )
        }


# ============================================
# 테스트 코드
# ============================================

def test_account_manager():
    """AccountManager 테스트"""
    print("\n=== AccountManager 테스트 ===\n")

    manager = AccountManager()

    # 계정 상태 출력
    print("전체 계정 상태:")
    status = manager.get_account_status()
    print(f"  총 계정 수: {status['total_accounts']}")
    print(f"  사용 가능: {status['available_accounts']}")

    # 다음 계정 선택
    next_account = manager.get_next_account()
    if next_account:
        print(f"\n다음 사용 계정: {next_account.naver_id}")

        # 포스팅 성공 시뮬레이션
        manager.record_post_success(next_account.naver_id)
        print(f"포스팅 성공 기록됨")

    print("\n테스트 완료!")


if __name__ == "__main__":
    test_account_manager()
