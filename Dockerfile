# ============================================
# 네이버 블로그 자동화 시스템 - Production Dockerfile
# Playwright 공식 이미지 기반
# ============================================

# Playwright 공식 이미지 사용 (모든 브라우저 의존성 포함)
# 2025-12-28: v1.57.0으로 업데이트 (브라우저 시작 오류 해결)
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

# 메타데이터
LABEL maintainer="mr.joo"
LABEL description="Naver Blog Automation System - Group B"
LABEL version="1.0.0"

# 추가 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치 (먼저 복사하여 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 필수 디렉토리 생성
RUN mkdir -p /app/logs /app/generated_images /app/data/cache /app/data/sessions

# 환경 변수 설정
# - HEADLESS: 브라우저 헤드리스 모드 (True 권장)
# - USE_CDP: Chrome DevTools Protocol 사용 여부 (Docker에서는 False 권장)
# - CDP_TIMEOUT: CDP 연결 타임아웃 초 (기본 3초)
# - SESSION_MAX_AGE_DAYS: 세션 최대 유효 기간 일수 (기본 7일)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul \
    HEADLESS=True \
    USE_CDP=False \
    CDP_TIMEOUT=3 \
    SESSION_MAX_AGE_DAYS=7

# 헬스체크 (30초 간격, 10초 타임아웃)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# dumb-init으로 PID 1 문제 해결
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# 기본 실행 명령어
CMD ["python", "-m", "scheduler.auto_scheduler"]
