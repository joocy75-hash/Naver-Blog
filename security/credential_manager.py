"""
자격증명 관리 모듈
- 시스템 키체인을 통한 안전한 비밀번호 저장
- 환경 변수 암호화/복호화
- API 키 안전 관리
- Docker 환경 자동 감지 및 호환성 지원
"""

import os
import keyring
from cryptography.fernet import Fernet
from typing import Optional
from pathlib import Path
from loguru import logger


def is_docker_environment() -> bool:
    """
    Docker 환경인지 자동 감지 (cgroup v1/v2 모두 지원)

    감지 방법:
    1. /.dockerenv 파일 존재 (Docker 전용)
    2. /run/.containerenv 파일 존재 (Podman 등)
    3. /proc/1/cgroup 내용 확인 (cgroup v1/v2)
    4. 환경 변수 RUNNING_IN_DOCKER
    """
    # 1. Docker 환경 파일 확인
    if Path("/.dockerenv").exists():
        return True

    # 2. 컨테이너 환경 파일 확인 (Podman, containerd 등)
    if Path("/run/.containerenv").exists():
        return True

    # 3. cgroup에서 docker/containerd 확인 (v1 및 v2 지원)
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read().lower()
            # cgroup v1: "docker" 문자열 포함
            # cgroup v2: "containerd", "docker" 등 포함
            if any(keyword in content for keyword in ["docker", "containerd", "kubepods"]):
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # 4. 환경변수 확인
    if os.environ.get("RUNNING_IN_DOCKER", "").lower() == "true":
        return True

    # 5. 컨테이너 특정 환경변수 확인
    if os.environ.get("container"):  # systemd-nspawn, Podman 등에서 설정
        return True

    return False


# Docker 환경 여부 (모듈 로드 시 한 번만 확인)
IS_DOCKER = is_docker_environment()

# Docker 환경에서는 keyring 비활성화 (headless 환경에서 동작하지 않음)
KEYRING_AVAILABLE = not IS_DOCKER

if IS_DOCKER:
    logger.info("Docker 환경 감지: 환경 변수 우선 모드 활성화")


class CredentialManager:
    """안전한 자격증명 관리 클래스"""

    SERVICE_NAME = "naver_blog_automation"
    API_SERVICE = "api_keys"

    def __init__(self, encryption_key_path: Optional[str] = None):
        """
        Args:
            encryption_key_path: 암호화 키 파일 경로 (없으면 자동 생성)
        """
        self.encryption_key_path = encryption_key_path or "./secrets/encryption.key"
        self.cipher = self._load_or_create_cipher()

    def _load_or_create_cipher(self) -> Fernet:
        """암호화 키 로드 또는 생성"""
        key_path = Path(self.encryption_key_path)

        if key_path.exists():
            with open(key_path, 'rb') as f:
                key = f.read()
            logger.info("암호화 키 로드 완료")
        else:
            # 새 키 생성
            key = Fernet.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(key_path, 'wb') as f:
                f.write(key)
            # 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(key_path, 0o600)
            logger.info(f"새 암호화 키 생성: {key_path}")

        return Fernet(key)

    # ============================================
    # 키체인 관리 (가장 안전한 방법)
    # ============================================

    def store_naver_credentials(self, naver_id: str, naver_pw: str) -> bool:
        """네이버 계정 정보를 시스템 키체인에 저장"""
        try:
            keyring.set_password(self.SERVICE_NAME, naver_id, naver_pw)
            logger.success(f"네이버 계정 저장 완료: {naver_id}")
            return True
        except Exception as e:
            logger.error(f"네이버 계정 저장 실패: {e}")
            return False

    def get_naver_credentials(self, naver_id: str) -> Optional[str]:
        """네이버 계정 정보를 키체인에서 불러오기"""
        try:
            password = keyring.get_password(self.SERVICE_NAME, naver_id)
            if password:
                logger.info(f"네이버 계정 불러오기 완료: {naver_id}")
            else:
                logger.warning(f"키체인에 계정 정보 없음: {naver_id}")
            return password
        except Exception as e:
            logger.error(f"네이버 계정 불러오기 실패: {e}")
            return None

    def store_api_key(self, service: str, api_key: str) -> bool:
        """API 키를 키체인에 저장"""
        try:
            keyring.set_password(self.API_SERVICE, service, api_key)
            logger.success(f"API 키 저장 완료: {service}")
            return True
        except Exception as e:
            logger.error(f"API 키 저장 실패 ({service}): {e}")
            return False

    def get_api_key(self, service: str) -> Optional[str]:
        """API 키를 환경변수 또는 키체인에서 불러오기 (Docker 호환)"""
        # 환경변수 이름 매핑
        env_var_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "brave": "BRAVE_API_KEY",
            "telegram": "TELEGRAM_BOT_TOKEN",
        }

        # 1. 환경변수 확인 (Docker/서버 환경 우선)
        env_var = env_var_map.get(service.lower())
        if env_var:
            api_key = os.environ.get(env_var)
            if api_key:
                logger.info(f"환경변수에서 API 키 로드: {service}")
                return api_key

        # 2. 키체인 시도 (로컬 환경에서만)
        if KEYRING_AVAILABLE:
            try:
                api_key = keyring.get_password(self.API_SERVICE, service)
                if api_key:
                    logger.info(f"키체인에서 API 키 로드: {service}")
                    return api_key
            except keyring.errors.KeyringError as e:
                # 키체인 특정 오류 (권한, 잠금 등)
                logger.warning(f"키체인 접근 오류 ({service}): {type(e).__name__} - {e}")
            except Exception as e:
                # 예상치 못한 오류
                logger.warning(f"키체인 접근 중 예상치 못한 오류 ({service}): {type(e).__name__} - {e}")
        else:
            logger.debug(f"Docker 환경: 키체인 접근 생략 ({service})")

        # API 키를 찾을 수 없음 - 상세 안내 제공
        env_var_name = env_var_map.get(service.lower(), "UNKNOWN")
        logger.error(
            f"❌ API 키를 찾을 수 없습니다: {service}\n"
            f"   환경변수: {env_var_name}\n"
            f"   키체인 가능: {KEYRING_AVAILABLE}\n"
            f"   해결방법:\n"
            f"     1. 환경변수 설정: export {env_var_name}='your_api_key'\n"
            f"     2. 또는 .env 파일에 추가: {env_var_name}=your_api_key\n"
            f"     3. 로컬 환경: python -m security.credential_manager (키체인 저장)"
        )
        return None

    # ============================================
    # 파일 암호화 (백업용)
    # ============================================

    def encrypt_string(self, plaintext: str) -> str:
        """문자열 암호화"""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt_string(self, encrypted_text: str) -> str:
        """문자열 복호화"""
        decrypted = self.cipher.decrypt(encrypted_text.encode())
        return decrypted.decode()

    def encrypt_file(self, input_path: str, output_path: str) -> bool:
        """파일 암호화"""
        try:
            with open(input_path, 'rb') as f:
                data = f.read()

            encrypted_data = self.cipher.encrypt(data)

            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            os.chmod(output_path, 0o600)
            logger.success(f"파일 암호화 완료: {output_path}")
            return True
        except Exception as e:
            logger.error(f"파일 암호화 실패: {e}")
            return False

    def decrypt_file(self, input_path: str, output_path: str) -> bool:
        """파일 복호화"""
        try:
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)

            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            logger.success(f"파일 복호화 완료: {output_path}")
            return True
        except Exception as e:
            logger.error(f"파일 복호화 실패: {e}")
            return False

    # ============================================
    # 환경 변수 안전 관리
    # ============================================

    def get_credential_from_env_or_keychain(
        self,
        env_var: str,
        keychain_service: str,
        keychain_username: str
    ) -> Optional[str]:
        """
        환경 변수 또는 키체인에서 자격증명 가져오기
        우선순위: 키체인 > 환경 변수
        """
        # 1. 키체인 시도
        credential = keyring.get_password(keychain_service, keychain_username)
        if credential:
            logger.info(f"키체인에서 자격증명 로드: {keychain_username}")
            return credential

        # 2. 환경 변수 시도
        credential = os.getenv(env_var)
        if credential:
            logger.warning(
                f"환경 변수에서 자격증명 로드: {env_var} "
                "(보안을 위해 키체인 사용 권장)"
            )
            return credential

        logger.error(f"자격증명을 찾을 수 없음: {env_var}")
        return None

    def delete_credential(self, service: str, username: str) -> bool:
        """키체인에서 자격증명 삭제"""
        try:
            keyring.delete_password(service, username)
            logger.success(f"자격증명 삭제 완료: {service}/{username}")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"삭제할 자격증명 없음: {service}/{username}")
            return False
        except Exception as e:
            logger.error(f"자격증명 삭제 실패: {e}")
            return False


# ============================================
# 편의 함수
# ============================================

def setup_credentials_interactive():
    """대화형 자격증명 설정"""
    print("\n🔐 자격증명 설정 시작\n")

    manager = CredentialManager()

    # 네이버 계정
    print("=== 네이버 계정 ===")
    naver_id = input("네이버 ID: ").strip()
    naver_pw = input("네이버 비밀번호: ").strip()

    if naver_id and naver_pw:
        manager.store_naver_credentials(naver_id, naver_pw)

    # API 키들
    print("\n=== API 키 ===")

    anthropic_key = input("Anthropic API Key (Claude): ").strip()
    if anthropic_key:
        manager.store_api_key("anthropic", anthropic_key)

    google_key = input("Google API Key (Gemini): ").strip()
    if google_key:
        manager.store_api_key("google", google_key)

    perplexity_key = input("Perplexity API Key: ").strip()
    if perplexity_key:
        manager.store_api_key("perplexity", perplexity_key)

    brave_key = input("Brave API Key (선택, Enter로 건너뛰기): ").strip()
    if brave_key:
        manager.store_api_key("brave", brave_key)

    print("\n✅ 자격증명 설정 완료!")
    print("모든 정보가 시스템 키체인에 안전하게 저장되었습니다.")


if __name__ == "__main__":
    # 대화형 설정 실행
    setup_credentials_interactive()
