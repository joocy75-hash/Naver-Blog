"""
브라우저 세션 관리 모듈
- Playwright 세션 암호화 저장
- 세션 복구 및 갱신 (자동 갱신 지원)
- 보안 세션 관리
- 세션 만료 경고 시스템
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from loguru import logger


# 환경변수에서 세션 유효기간 설정 (기본값: 7일)
DEFAULT_SESSION_MAX_AGE_DAYS = int(os.getenv("SESSION_MAX_AGE_DAYS", "7"))
# 세션 만료 경고 임계값 (일 단위)
SESSION_WARNING_THRESHOLDS = [1, 2, 3]  # 1일, 2일, 3일 전 경고


class SecureSessionManager:
    """암호화된 브라우저 세션 관리 클래스"""

    def __init__(
        self,
        encryption_key_path: str = "./secrets/encryption.key",
        session_dir: str = "./data/sessions"
    ):
        """
        Args:
            encryption_key_path: 암호화 키 파일 경로
            session_dir: 세션 파일 저장 디렉토리
        """
        self.encryption_key_path = Path(encryption_key_path)
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.cipher = self._load_cipher()

    def _load_cipher(self) -> Fernet:
        """암호화 키 로드"""
        if not self.encryption_key_path.exists():
            raise FileNotFoundError(
                f"암호화 키 파일이 없습니다: {self.encryption_key_path}\n"
                "먼저 credential_manager를 실행하여 키를 생성하세요."
            )

        with open(self.encryption_key_path, 'rb') as f:
            key = f.read()

        return Fernet(key)

    def _get_session_path(self, session_name: str = "default") -> Path:
        """세션 파일 경로 가져오기"""
        return self.session_dir / f"{session_name}.session.encrypted"

    def save_session(
        self,
        storage_state: Dict[str, Any],
        session_name: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Playwright 세션을 암호화하여 저장

        Args:
            storage_state: Playwright의 storage_state (쿠키, 로컬스토리지 등)
            session_name: 세션 이름
            metadata: 추가 메타데이터 (선택)

        Returns:
            성공 여부
        """
        try:
            # 메타데이터 추가
            session_data = {
                "storage_state": storage_state,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            # JSON 직렬화
            json_data = json.dumps(session_data, ensure_ascii=False)

            # 암호화
            encrypted_data = self.cipher.encrypt(json_data.encode())

            # 파일 저장
            session_path = self._get_session_path(session_name)
            with open(session_path, 'wb') as f:
                f.write(encrypted_data)

            # 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(session_path, 0o600)

            logger.success(f"세션 저장 완료: {session_path}")
            return True

        except Exception as e:
            logger.error(f"세션 저장 실패: {e}")
            return False

    def load_session(
        self,
        session_name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        암호화된 세션 복호화하여 로드

        Args:
            session_name: 세션 이름

        Returns:
            storage_state 딕셔너리 또는 None
        """
        session_path = self._get_session_path(session_name)

        # 파일이 없는 것은 정상 (처음 실행 or 세션 만료 후 삭제)
        if not session_path.exists():
            logger.info(f"세션 파일이 없습니다: {session_path}")
            return None

        try:
            # 파일 읽기
            with open(session_path, 'rb') as f:
                encrypted_data = f.read()

        except PermissionError as e:
            logger.error(
                f"❌ 세션 파일 읽기 권한 없음: {session_path}\n"
                f"   해결: chmod 600 {session_path}"
            )
            return None

        except OSError as e:
            logger.error(
                f"❌ 세션 파일 읽기 중 I/O 오류: {e}\n"
                f"   파일: {session_path}\n"
                f"   디스크 상태를 확인하세요"
            )
            return None

        try:
            # 복호화
            decrypted_data = self.cipher.decrypt(encrypted_data)

        except Exception as e:
            logger.error(
                f"❌ 세션 복호화 실패: {session_path}\n"
                f"   오류: {type(e).__name__} - {e}\n"
                f"   원인: 암호화 키 불일치 또는 파일 손상\n"
                f"   해결: 세션 파일을 삭제하고 재로그인하세요"
            )
            # 손상된 파일 백업
            try:
                backup_path = session_path.with_suffix('.corrupted')
                session_path.rename(backup_path)
                logger.info(f"   손상된 세션 백업: {backup_path}")
            except:
                pass
            return None

        try:
            # JSON 파싱
            session_data = json.loads(decrypted_data.decode())

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(
                f"❌ 세션 데이터 파싱 실패: {session_path}\n"
                f"   오류: {type(e).__name__} - {e}\n"
                f"   원인: 세션 파일 손상\n"
                f"   해결: 세션 파일을 삭제하고 재로그인하세요"
            )
            return None

        # 버전 확인
        version = session_data.get("version")
        if version != "1.0":
            logger.warning(
                f"⚠️ 세션 버전 불일치: {version} (예상: 1.0)\n"
                f"   세션이 정상 작동하지 않을 수 있습니다"
            )

        logger.success(f"✅ 세션 로드 완료: {session_path}")
        return session_data.get("storage_state")

    def get_session_metadata(
        self,
        session_name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """세션 메타데이터 가져오기"""
        try:
            session_path = self._get_session_path(session_name)

            if not session_path.exists():
                return None

            with open(session_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)
            session_data = json.loads(decrypted_data.decode())

            return {
                "created_at": session_data.get("created_at"),
                "version": session_data.get("version"),
                "metadata": session_data.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            return None

    def is_session_valid(
        self,
        session_name: str = "default",
        max_age_days: int = None
    ) -> bool:
        """
        세션 유효성 검사 (갱신 시간 기준)

        Args:
            session_name: 세션 이름
            max_age_days: 최대 유효 기간 (일), None이면 환경변수 사용

        Returns:
            유효 여부
        """
        if max_age_days is None:
            max_age_days = DEFAULT_SESSION_MAX_AGE_DAYS

        metadata = self.get_session_metadata(session_name)

        if not metadata:
            return False

        try:
            # 갱신 시간이 있으면 갱신 시간 기준, 없으면 생성 시간 기준
            inner_metadata = metadata.get("metadata", {})
            last_renewed = inner_metadata.get("last_renewed_at")

            if last_renewed:
                reference_time = datetime.fromisoformat(last_renewed)
                time_type = "갱신"
            else:
                reference_time = datetime.fromisoformat(metadata["created_at"])
                time_type = "생성"

            age = datetime.now() - reference_time

            if age > timedelta(days=max_age_days):
                logger.warning(
                    f"세션이 만료되었습니다 ({time_type} 후 {age.days}일 경과, "
                    f"최대 {max_age_days}일)"
                )
                return False

            logger.info(f"세션 유효 ({time_type} 후 {age.days}일 경과)")
            return True

        except Exception as e:
            logger.error(f"세션 유효성 검사 실패: {e}")
            return False

    def renew_session(
        self,
        session_name: str = "default",
        new_storage_state: dict = None
    ) -> bool:
        """
        세션 갱신 (포스팅 성공 시 호출하여 유효기간 연장)

        Args:
            session_name: 세션 이름
            new_storage_state: 새 storage_state (없으면 기존 것 유지)

        Returns:
            성공 여부
        """
        try:
            session_path = self._get_session_path(session_name)

            if not session_path.exists():
                logger.warning(f"갱신할 세션이 없습니다: {session_name}")
                return False

            # 기존 세션 로드
            with open(session_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)
            session_data = json.loads(decrypted_data.decode())

            # 갱신 시간 업데이트
            if "metadata" not in session_data:
                session_data["metadata"] = {}

            session_data["metadata"]["last_renewed_at"] = datetime.now().isoformat()

            # 새 storage_state가 제공되면 업데이트
            if new_storage_state:
                session_data["storage_state"] = new_storage_state

            # 다시 암호화하여 저장
            json_data = json.dumps(session_data, ensure_ascii=False)
            encrypted_data = self.cipher.encrypt(json_data.encode())

            with open(session_path, 'wb') as f:
                f.write(encrypted_data)

            logger.success(f"세션 갱신 완료: {session_name}")
            return True

        except Exception as e:
            logger.error(f"세션 갱신 실패: {e}")
            return False

    def get_days_until_expiry(
        self,
        session_name: str = "default",
        max_age_days: int = None
    ) -> int:
        """
        세션 만료까지 남은 일수 계산

        Returns:
            남은 일수 (만료됐으면 음수, 세션 없으면 -999)
        """
        if max_age_days is None:
            max_age_days = DEFAULT_SESSION_MAX_AGE_DAYS

        metadata = self.get_session_metadata(session_name)

        if not metadata:
            return -999

        try:
            inner_metadata = metadata.get("metadata", {})
            last_renewed = inner_metadata.get("last_renewed_at")

            if last_renewed:
                reference_time = datetime.fromisoformat(last_renewed)
            else:
                reference_time = datetime.fromisoformat(metadata["created_at"])

            expiry_time = reference_time + timedelta(days=max_age_days)
            remaining = expiry_time - datetime.now()

            return remaining.days

        except Exception as e:
            logger.error(f"만료일 계산 실패: {e}")
            return -999

    def check_expiry_warning(
        self,
        session_name: str = "default",
        warning_thresholds: list = None
    ) -> Tuple[bool, int]:
        """
        세션 만료 경고 필요 여부 확인

        Returns:
            (경고 필요 여부, 남은 일수)
        """
        if warning_thresholds is None:
            warning_thresholds = SESSION_WARNING_THRESHOLDS

        days_remaining = self.get_days_until_expiry(session_name)

        if days_remaining == -999:
            return False, -999

        needs_warning = days_remaining in warning_thresholds or days_remaining <= 0

        if needs_warning and days_remaining > 0:
            logger.warning(f"⚠️ 세션 만료 {days_remaining}일 전! 재로그인 권장")
        elif days_remaining <= 0:
            logger.error(f"❌ 세션이 만료되었습니다! 재로그인 필요")

        return needs_warning, days_remaining

    def delete_session(self, session_name: str = "default") -> bool:
        """세션 파일 삭제"""
        try:
            session_path = self._get_session_path(session_name)

            if session_path.exists():
                session_path.unlink()
                logger.success(f"세션 삭제 완료: {session_path}")
                return True
            else:
                logger.warning(f"삭제할 세션이 없습니다: {session_path}")
                return False

        except Exception as e:
            logger.error(f"세션 삭제 실패: {e}")
            return False

    def list_sessions(self) -> list[str]:
        """저장된 모든 세션 목록"""
        try:
            sessions = []
            for path in self.session_dir.glob("*.session.encrypted"):
                session_name = path.stem.replace(".session", "")
                sessions.append(session_name)

            logger.info(f"세션 목록: {sessions}")
            return sessions

        except Exception as e:
            logger.error(f"세션 목록 조회 실패: {e}")
            return []

    def cleanup_expired_sessions(self, max_age_days: int = 7) -> int:
        """만료된 세션 자동 정리"""
        deleted_count = 0

        for session_name in self.list_sessions():
            if not self.is_session_valid(session_name, max_age_days):
                if self.delete_session(session_name):
                    deleted_count += 1

        logger.info(f"만료된 세션 {deleted_count}개 정리 완료")
        return deleted_count


# ============================================
# Playwright 통합 헬퍼
# ============================================

async def save_playwright_session(
    browser_context,
    session_manager: SecureSessionManager,
    session_name: str = "default",
    account_id: Optional[str] = None
) -> bool:
    """
    Playwright BrowserContext의 세션 저장

    Args:
        browser_context: Playwright의 BrowserContext
        session_manager: SecureSessionManager 인스턴스
        session_name: 세션 이름
        account_id: 계정 ID (메타데이터용)

    Returns:
        성공 여부
    """
    try:
        # Playwright에서 storage_state 가져오기
        storage_state = await browser_context.storage_state()

        # 메타데이터
        metadata = {
            "account_id": account_id,
            "browser": "chromium",
            "saved_at": datetime.now().isoformat()
        }

        # 암호화하여 저장
        return session_manager.save_session(
            storage_state=storage_state,
            session_name=session_name,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Playwright 세션 저장 실패: {e}")
        return False


async def load_playwright_session(
    browser,
    session_manager: SecureSessionManager,
    session_name: str = "default"
):
    """
    암호화된 세션으로 Playwright BrowserContext 생성

    Args:
        browser: Playwright의 Browser 인스턴스
        session_manager: SecureSessionManager 인스턴스
        session_name: 세션 이름

    Returns:
        BrowserContext 또는 None
    """
    try:
        # 세션 유효성 검사
        if not session_manager.is_session_valid(session_name):
            logger.warning("세션이 유효하지 않습니다. 새 로그인 필요")
            return None

        # 세션 로드
        storage_state = session_manager.load_session(session_name)

        if not storage_state:
            return None

        # BrowserContext 생성
        context = await browser.new_context(storage_state=storage_state)

        logger.success("Playwright 세션 복구 완료")
        return context

    except Exception as e:
        logger.error(f"Playwright 세션 로드 실패: {e}")
        return None


async def renew_playwright_session(
    browser_context,
    session_manager: SecureSessionManager,
    session_name: str = "default"
) -> bool:
    """
    포스팅 성공 후 Playwright 세션 갱신 (유효기간 연장)

    Args:
        browser_context: Playwright의 BrowserContext
        session_manager: SecureSessionManager 인스턴스
        session_name: 세션 이름

    Returns:
        성공 여부
    """
    try:
        # 현재 storage_state 가져오기
        storage_state = await browser_context.storage_state()

        # 세션 갱신 (last_renewed_at 업데이트 + storage_state 갱신)
        return session_manager.renew_session(
            session_name=session_name,
            new_storage_state=storage_state
        )

    except Exception as e:
        logger.error(f"Playwright 세션 갱신 실패: {e}")
        return False


if __name__ == "__main__":
    # 테스트
    manager = SecureSessionManager()

    # 테스트 세션 저장
    test_storage_state = {
        "cookies": [
            {"name": "test_cookie", "value": "test_value", "domain": ".naver.com"}
        ],
        "origins": []
    }

    manager.save_session(
        storage_state=test_storage_state,
        session_name="test",
        metadata={"account": "test_user"}
    )

    # 테스트 세션 로드
    loaded = manager.load_session("test")
    print(f"로드된 세션: {loaded}")

    # 메타데이터 확인
    metadata = manager.get_session_metadata("test")
    print(f"메타데이터: {metadata}")

    # 세션 목록
    print(f"세션 목록: {manager.list_sessions()}")
