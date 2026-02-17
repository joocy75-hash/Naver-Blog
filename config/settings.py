"""
애플리케이션 설정
- 환경 변수 로드
- 설정값 관리
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# ============================================
# 보안 설정
# ============================================

ENCRYPTION_KEY_PATH = os.getenv('ENCRYPTION_KEY_PATH', str(PROJECT_ROOT / 'secrets' / 'encryption.key'))
SESSION_ENCRYPTION = os.getenv('SESSION_ENCRYPTION', 'True').lower() == 'true'

# ============================================
# 데이터베이스
# ============================================

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/blog_bot.db')

# ============================================
# Rate Limiting
# ============================================

MAX_DAILY_POSTS = int(os.getenv('MAX_DAILY_POSTS', '3'))
MIN_POST_INTERVAL_HOURS = int(os.getenv('MIN_POST_INTERVAL_HOURS', '6'))
API_COOLDOWN_SECONDS = int(os.getenv('API_COOLDOWN_SECONDS', '60'))

# ============================================
# 행동 시뮬레이션
# ============================================

TYPING_SPEED_MIN_MS = int(os.getenv('TYPING_SPEED_MIN_MS', '80'))
TYPING_SPEED_MAX_MS = int(os.getenv('TYPING_SPEED_MAX_MS', '180'))
MOUSE_MOVEMENT_BEZIER = os.getenv('MOUSE_MOVEMENT_BEZIER', 'True').lower() == 'true'
SCROLL_SPEED_HUMAN_LIKE = os.getenv('SCROLL_SPEED_HUMAN_LIKE', 'True').lower() == 'true'
HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'true'

# ============================================
# CDP (Chrome DevTools Protocol)
# ============================================

USE_CDP = os.getenv('USE_CDP', 'True').lower() == 'true'
CDP_ENDPOINT = os.getenv('CDP_ENDPOINT', 'http://127.0.0.1:9222')
CDP_TIMEOUT = int(os.getenv('CDP_TIMEOUT', '5'))

# ============================================
# 모니터링
# ============================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
ENABLE_ALERTS = os.getenv('ENABLE_ALERTS', 'True').lower() == 'true'
SENTRY_DSN = os.getenv('SENTRY_DSN', '')

# ============================================
# 콘텐츠 설정
# ============================================

BLOG_CATEGORY = os.getenv('BLOG_CATEGORY', '암호화폐')
DEFAULT_TAGS = os.getenv('DEFAULT_TAGS', '비트코인,암호화폐,AI자동매매,투자').split(',')
SEO_KEYWORD_DENSITY = float(os.getenv('SEO_KEYWORD_DENSITY', '1.8'))

# ============================================
# 개발 모드
# ============================================

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ============================================
# 디렉토리 경로
# ============================================

DATA_DIR = PROJECT_ROOT / 'data'
LOGS_DIR = DATA_DIR / 'logs'
IMAGES_DIR = DATA_DIR / 'images'
SESSIONS_DIR = DATA_DIR / 'sessions'
SECRETS_DIR = PROJECT_ROOT / 'secrets'

# 디렉토리 생성
for dir_path in [DATA_DIR, LOGS_DIR, IMAGES_DIR, SESSIONS_DIR, SECRETS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
