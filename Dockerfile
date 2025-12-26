# ============================================
# 네이버 블로그 자동화 시스템 - Production Dockerfile
# Multi-stage build for optimized image size
# ============================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 가상환경 생성 및 의존성 설치
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Production
FROM python:3.11-slim AS production

# 메타데이터
LABEL maintainer="mr.joo"
LABEL description="Naver Blog Automation System - Group B"
LABEL version="1.0.0"

# 시스템 패키지 (Playwright 런타임 의존성)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-nanum \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 빌더 스테이지에서 가상환경 복사
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 비root 사용자 생성
RUN groupadd -r blogbot && useradd -r -g blogbot blogbot

# 작업 디렉토리 설정
WORKDIR /app

# Playwright 브라우저 설치 (root로 실행)
RUN playwright install chromium && \
    playwright install-deps chromium

# 애플리케이션 코드 복사
COPY --chown=blogbot:blogbot . .

# 필수 디렉토리 생성
RUN mkdir -p /app/logs /app/generated_images /app/data/cache /app/data/sessions && \
    chown -R blogbot:blogbot /app

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul \
    HEADLESS=True

# 사용자 전환
USER blogbot

# 헬스체크 (30초 간격, 10초 타임아웃)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# dumb-init으로 PID 1 문제 해결
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# 기본 실행 명령어
CMD ["python", "-m", "scheduler.auto_scheduler"]
