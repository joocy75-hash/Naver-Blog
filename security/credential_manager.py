"""
자격증명 관리 모듈
- 시스템 키체인을 통한 안전한 비밀번호 저장
- 환경 변수 암호화/복호화
- API 키 안전 관리
"""

import os
import keyring
from cryptography.fernet import Fernet
from typing import Optional
from pathlib import Path
from loguru import logger


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
        """API 키를 키체인에서 불러오기"""
        try:
            api_key = keyring.get_password(self.API_SERVICE, service)
            if api_key:
                logger.info(f"API 키 불러오기 완료: {service}")
            else:
                logger.warning(f"키체인에 API 키 없음: {service}")
            return api_key
        except Exception as e:
            logger.error(f"API 키 불러오기 실패 ({service}): {e}")
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
