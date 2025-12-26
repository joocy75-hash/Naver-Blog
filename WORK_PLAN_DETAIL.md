# 네이버 블로그 자동화 봇 - 상세 작업 계획서

> 작성일: 2025-12-26
> 목표: 완전 자동화 무인 운영 시스템 구축

---

## 목차

1. [Phase 1: 안정성 강화](#phase-1-안정성-강화-필수)
2. [Phase 2: 자동화 완성](#phase-2-자동화-완성-높은-우선순위)
3. [Phase 3: 품질 개선](#phase-3-품질-개선-중간-우선순위)
4. [Phase 4: 모니터링/관리](#phase-4-모니터링관리-낮은-우선순위)
5. [Phase 5: 확장 기능](#phase-5-확장-기능-선택)

---

## Phase 1: 안정성 강화 (필수)

### 1.1 세션 자동 갱신 시스템

**현재 문제**: 네이버 세션 만료 시 수동 개입 필요

**구현 파일**: `security/session_manager.py`, `utils/session_keeper.py` (신규)

**작업 내용**:

```python
# utils/session_keeper.py (신규 생성)

class SessionKeeper:
    """세션 유효성 모니터링 및 자동 갱신"""

    def __init__(self, naver_id: str):
        self.naver_id = naver_id
        self.session_manager = SecureSessionManager()

    async def check_session_valid(self) -> bool:
        """세션 유효성 검사"""
        # 1. 네이버 블로그 접속 시도
        # 2. 로그인 상태 확인
        # 3. 만료 시 False 반환
        pass

    async def refresh_session(self) -> bool:
        """세션 갱신 (쿠키 갱신)"""
        # 1. 저장된 세션으로 메인 페이지 접속
        # 2. 쿠키 자동 갱신 (네이버가 처리)
        # 3. 새 세션 저장
        pass

    async def emergency_relogin(self) -> bool:
        """긴급 재로그인 (수동 개입 요청)"""
        # 1. 텔레그램으로 긴급 알림
        # 2. 대기 상태로 전환
        # 3. 수동 로그인 완료 대기
        pass
```

**테스트 방법**:
```bash
python -c "from utils.session_keeper import SessionKeeper; ..."
```

---

### 1.2 에러 복구 시스템

**현재 문제**: 연속 에러 시 스케줄러 중단

**구현 파일**: `scheduler/auto_scheduler.py`, `utils/error_recovery.py` (신규)

**작업 내용**:

```python
# utils/error_recovery.py (신규 생성)

class ErrorRecoveryManager:
    """에러 복구 관리자"""

    MAX_CONSECUTIVE_ERRORS = 3
    COOLDOWN_MINUTES = 30

    def __init__(self):
        self.consecutive_errors = 0
        self.last_error_time = None
        self.error_history = []

    def record_error(self, error: Exception, context: str):
        """에러 기록"""
        self.consecutive_errors += 1
        self.error_history.append({
            "time": datetime.now(),
            "error": str(error),
            "context": context
        })

    def record_success(self):
        """성공 시 카운터 리셋"""
        self.consecutive_errors = 0

    def should_pause(self) -> bool:
        """일시 중지 필요 여부"""
        return self.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS

    def get_cooldown_end(self) -> datetime:
        """쿨다운 종료 시간"""
        return datetime.now() + timedelta(minutes=self.COOLDOWN_MINUTES)

    async def attempt_recovery(self) -> bool:
        """복구 시도"""
        # 1. 세션 유효성 검사
        # 2. API 연결 테스트
        # 3. 브라우저 재시작
        pass
```

**scheduler/auto_scheduler.py 수정**:

```python
# _post_job 메서드에 추가

async def _post_job(self):
    """실제 포스팅 작업"""

    # 에러 복구 관리자 확인
    if self.error_recovery.should_pause():
        logger.warning("연속 에러로 일시 중지 중...")

        # 복구 시도
        if await self.error_recovery.attempt_recovery():
            logger.info("복구 성공!")
        else:
            await self._send_telegram_notification(
                success=False,
                error="연속 에러 - 수동 확인 필요"
            )
            return

    try:
        # 기존 포스팅 로직
        ...
        self.error_recovery.record_success()

    except Exception as e:
        self.error_recovery.record_error(e, "post_job")
        ...
```

---

### 1.3 헬스체크 시스템

**현재 문제**: 시스템 상태 모니터링 없음

**구현 파일**: `monitoring/health_checker.py` (신규)

**작업 내용**:

```python
# monitoring/health_checker.py (신규 생성)

class HealthChecker:
    """시스템 헬스체크"""

    def __init__(self):
        self.checks = {
            "api_claude": self._check_claude_api,
            "api_perplexity": self._check_perplexity_api,
            "api_gemini": self._check_gemini_api,
            "session_naver": self._check_naver_session,
            "disk_space": self._check_disk_space,
            "database": self._check_database,
        }

    async def run_all_checks(self) -> Dict[str, bool]:
        """모든 헬스체크 실행"""
        results = {}
        for name, check_func in self.checks.items():
            try:
                results[name] = await check_func()
            except Exception as e:
                results[name] = False
                logger.error(f"헬스체크 실패 [{name}]: {e}")
        return results

    async def _check_claude_api(self) -> bool:
        """Claude API 연결 테스트"""
        # 간단한 API 호출 테스트
        pass

    async def _check_naver_session(self) -> bool:
        """네이버 세션 유효성"""
        from utils.session_keeper import SessionKeeper
        keeper = SessionKeeper(self.naver_id)
        return await keeper.check_session_valid()

    async def _check_disk_space(self) -> bool:
        """디스크 공간 확인 (이미지 저장용)"""
        import shutil
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)
        return free_gb > 1.0  # 최소 1GB
```

**스케줄러에 통합**:

```python
# scheduler/auto_scheduler.py

# 헬스체크 작업 추가 (1시간마다)
self.scheduler.add_job(
    self._health_check_job,
    trigger=IntervalTrigger(hours=1),
    id="health_check"
)

async def _health_check_job(self):
    """정기 헬스체크"""
    checker = HealthChecker()
    results = await checker.run_all_checks()

    failed = [k for k, v in results.items() if not v]
    if failed:
        await self._send_telegram_notification(
            success=False,
            error=f"헬스체크 실패: {', '.join(failed)}"
        )
```

---

## Phase 2: 자동화 완성 (높은 우선순위)

### 2.1 중복 주제 방지

**현재 문제**: 같은 주제로 반복 포스팅 가능성

**구현 파일**: `models/database.py`, `agents/content_agent.py`

**작업 내용**:

```python
# models/database.py에 추가

def get_recent_topics(self, session, days: int = 7) -> List[str]:
    """최근 N일간 포스팅 주제 조회"""
    cutoff = datetime.now() - timedelta(days=days)
    posts = session.query(Post).filter(
        Post.created_at >= cutoff
    ).all()
    return [p.title for p in posts]

def is_topic_duplicate(self, session, topic: str, similarity_threshold: float = 0.7) -> bool:
    """주제 중복 확인"""
    from difflib import SequenceMatcher

    recent_topics = self.get_recent_topics(session)
    for recent in recent_topics:
        similarity = SequenceMatcher(None, topic.lower(), recent.lower()).ratio()
        if similarity > similarity_threshold:
            return True
    return False
```

**content_agent.py 수정**:

```python
def generate_post(self, research_data: Dict, ...):
    """포스트 생성 (중복 체크 포함)"""

    # 중복 체크
    db = DatabaseManager()
    with DBSession(db) as session:
        if db.is_topic_duplicate(session, research_data["topic"]):
            logger.warning(f"중복 주제 감지: {research_data['topic']}")
            # 다른 주제 요청 또는 스킵
            return None

    # 기존 로직
    ...
```

---

### 2.2 주제 카테고리 자동 순환

**현재 문제**: 특정 카테고리(crypto)에만 집중

**구현 파일**: `scheduler/topic_rotator.py` (신규)

**작업 내용**:

```python
# scheduler/topic_rotator.py (신규 생성)

class TopicRotator:
    """주제 카테고리 순환 관리"""

    CATEGORIES = ["crypto", "us_stock", "kr_stock", "ai_tech", "economy", "hot_issue"]

    # 카테고리별 가중치 (crypto에 더 높은 가중치)
    WEIGHTS = {
        "crypto": 4,
        "us_stock": 2,
        "kr_stock": 2,
        "ai_tech": 2,
        "economy": 1,
        "hot_issue": 1
    }

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_next_category(self) -> str:
        """다음 포스팅 카테고리 결정"""

        # 최근 포스팅 카테고리 조회
        recent = self._get_recent_categories(hours=24)

        # 가중치 기반 선택 (최근 사용된 카테고리는 가중치 감소)
        weights = dict(self.WEIGHTS)
        for cat in recent[-3:]:  # 최근 3개 카테고리
            if cat in weights:
                weights[cat] = max(1, weights[cat] - 1)

        # 가중치 기반 랜덤 선택
        categories = []
        for cat, weight in weights.items():
            categories.extend([cat] * weight)

        return random.choice(categories)

    def _get_recent_categories(self, hours: int) -> List[str]:
        """최근 N시간 포스팅 카테고리"""
        # DB 조회 로직
        pass
```

**스케줄러에 통합**:

```python
# scheduler/auto_scheduler.py

async def _post_job(self):
    # 카테고리 자동 선택
    rotator = TopicRotator(self.db)
    category = rotator.get_next_category()

    logger.info(f"선택된 카테고리: {category}")

    # 해당 카테고리로 리서치 + 포스팅
    result = await self.pipeline.run_research(
        topic_category=category,
        ...
    )
```

---

### 2.3 다중 계정 관리

**현재 문제**: 단일 계정만 지원

**구현 파일**: `scheduler/account_manager.py` (신규)

**작업 내용**:

```python
# scheduler/account_manager.py (신규 생성)

class AccountManager:
    """다중 네이버 계정 관리"""

    def __init__(self):
        self.accounts = []
        self.current_index = 0
        self._load_accounts()

    def _load_accounts(self):
        """계정 목록 로드"""
        # 환경 변수 또는 설정 파일에서 로드
        # NAVER_ACCOUNTS=id1,id2,id3
        accounts_str = os.getenv("NAVER_ACCOUNTS", "")
        if accounts_str:
            self.accounts = accounts_str.split(",")

    def get_next_account(self) -> str:
        """다음 포스팅 계정 (라운드 로빈)"""
        if not self.accounts:
            raise ValueError("등록된 계정이 없습니다")

        account = self.accounts[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.accounts)
        return account

    def get_account_status(self, naver_id: str) -> Dict:
        """계정 상태 조회"""
        return {
            "naver_id": naver_id,
            "session_valid": self._check_session(naver_id),
            "posts_today": self._get_posts_today(naver_id),
            "last_post": self._get_last_post_time(naver_id)
        }

    def get_best_account(self) -> str:
        """가장 적합한 계정 선택"""
        # 1. 세션 유효한 계정만 필터
        # 2. 오늘 포스팅 수가 적은 계정 우선
        # 3. 마지막 포스팅 후 가장 오래된 계정 우선
        pass
```

---

## Phase 3: 품질 개선 (중간 우선순위)

### 3.1 글 품질 강화

**현재 문제**: 가끔 품질이 낮은 글 발행

**구현 파일**: `agents/qa_agent.py`, `agents/content_agent.py`

**작업 내용**:

```python
# agents/qa_agent.py 개선

class EnhancedQAAgent:
    """강화된 품질 검증 에이전트"""

    # 최소 품질 점수 (이하면 재생성 요청)
    MIN_QUALITY_SCORE = 70

    # 검증 항목
    CHECKS = {
        "length": {"min": 800, "max": 3000, "weight": 0.15},
        "paragraphs": {"min": 4, "weight": 0.10},
        "headings": {"min": 2, "weight": 0.10},
        "no_repetition": {"weight": 0.15},
        "keyword_density": {"min": 0.01, "max": 0.05, "weight": 0.10},
        "readability": {"weight": 0.15},
        "call_to_action": {"weight": 0.10},
        "no_ai_phrases": {"weight": 0.15},  # "저는 AI입니다" 등 제거
    }

    def validate_and_score(self, title: str, content: str) -> Dict:
        """검증 및 점수화"""
        scores = {}
        issues = []

        # 각 항목별 검증
        for check_name, params in self.CHECKS.items():
            score, issue = getattr(self, f"_check_{check_name}")(content, params)
            scores[check_name] = score
            if issue:
                issues.append(issue)

        # 가중 평균 점수
        total_score = sum(
            scores[k] * self.CHECKS[k]["weight"]
            for k in scores
        ) * 100

        return {
            "score": total_score,
            "passed": total_score >= self.MIN_QUALITY_SCORE,
            "details": scores,
            "issues": issues
        }

    def _check_no_ai_phrases(self, content: str, params: Dict) -> Tuple[float, str]:
        """AI 특유 표현 검사"""
        ai_phrases = [
            "저는 AI", "인공지능으로서", "언어 모델",
            "학습 데이터", "2023년 기준", "제 지식으로는"
        ]
        found = [p for p in ai_phrases if p in content]
        if found:
            return 0.0, f"AI 표현 발견: {', '.join(found)}"
        return 1.0, None
```

---

### 3.2 이미지-글 연관성 강화

**현재 문제**: 이미지가 글 내용과 약간 동떨어질 수 있음

**구현 파일**: `agents/content_agent.py`

**작업 내용**:

```python
# agents/content_agent.py 개선

def generate_contextual_image_prompt(
    self,
    title: str,
    content: str,
    keywords: List[str],
    section_index: int = 0  # 본문 내 위치
) -> str:
    """맥락 기반 이미지 프롬프트 생성"""

    # 1. 핵심 키워드 추출
    key_concepts = self._extract_key_concepts(content)

    # 2. 감성 분석
    sentiment = self._analyze_sentiment(content)

    # 3. 섹션별 맥락 파악
    if section_index == 0:
        context = "opening hook, attention grabbing"
    elif section_index == 1:
        context = "main point illustration, data visualization"
    else:
        context = "conclusion, call to action, positive outlook"

    # 4. 키워드 기반 구체적 요소
    visual_elements = self._get_visual_elements(keywords)

    prompt = f"""
    {key_concepts[0]} concept visualization.
    Context: {context}
    Mood: {sentiment}
    Visual elements: {', '.join(visual_elements)}
    Style: crypto meme art, vibrant neon colors, dramatic lighting.
    No text, no words, no letters.
    """

    return prompt.strip()
```

---

### 3.3 SEO 최적화

**현재 문제**: 검색 노출 최적화 없음

**구현 파일**: `agents/seo_optimizer.py` (신규)

**작업 내용**:

```python
# agents/seo_optimizer.py (신규 생성)

class SEOOptimizer:
    """SEO 최적화 에이전트"""

    def optimize_title(self, title: str, keywords: List[str]) -> str:
        """제목 SEO 최적화"""
        # 1. 핵심 키워드 앞쪽 배치
        # 2. 30-60자 사이로 조정
        # 3. 클릭 유도 문구 추가
        pass

    def optimize_content(self, content: str, keywords: List[str]) -> str:
        """본문 SEO 최적화"""
        # 1. 키워드 밀도 조정 (1-3%)
        # 2. 첫 문단에 핵심 키워드 포함
        # 3. 소제목에 키워드 포함
        # 4. 이미지 alt 텍스트 권장사항
        pass

    def generate_meta_description(self, content: str) -> str:
        """메타 설명 생성 (네이버 검색 노출용)"""
        # 150자 이내 요약
        pass

    def suggest_tags(self, content: str, max_tags: int = 10) -> List[str]:
        """태그 추천"""
        # 1. 본문에서 키워드 추출
        # 2. 트렌딩 태그와 매칭
        # 3. 중복 제거 및 정렬
        pass
```

---

## Phase 4: 모니터링/관리 (낮은 우선순위)

### 4.1 웹 대시보드

**현재 문제**: 상태 확인이 불편함

**구현 파일**: `dashboard/` 디렉토리 (신규)

**기술 스택**: FastAPI + React (또는 Streamlit 간소화 버전)

**작업 내용**:

```
dashboard/
├── api/
│   ├── main.py          # FastAPI 앱
│   ├── routes/
│   │   ├── status.py    # 상태 API
│   │   ├── posts.py     # 포스팅 내역
│   │   └── control.py   # 시작/중지 제어
│   └── models/
│       └── schemas.py   # Pydantic 스키마
└── frontend/
    └── index.html       # 간단한 HTML 대시보드
```

**주요 기능**:
- 실시간 스케줄러 상태
- 오늘/이번 주 포스팅 통계
- 에러 로그 조회
- 시작/중지 버튼
- 다음 포스팅 예정 시간

---

### 4.2 텔레그램 원격 제어

**현재 문제**: 알림만 가능, 제어 불가

**구현 파일**: `utils/telegram_controller.py` (신규)

**작업 내용**:

```python
# utils/telegram_controller.py (신규 생성)

from telegram import Update
from telegram.ext import Application, CommandHandler

class TelegramController:
    """텔레그램 봇 명령어 처리"""

    COMMANDS = {
        "/status": "현재 상태 조회",
        "/start": "스케줄러 시작",
        "/stop": "스케줄러 중지",
        "/post": "즉시 포스팅",
        "/stats": "오늘 통계",
        "/health": "헬스체크 실행",
    }

    def __init__(self, bot_token: str, scheduler: AutoPostingScheduler):
        self.scheduler = scheduler
        self.app = Application.builder().token(bot_token).build()
        self._register_handlers()

    def _register_handlers(self):
        """명령어 핸들러 등록"""
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
        self.app.add_handler(CommandHandler("post", self.cmd_post))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("health", self.cmd_health))

    async def cmd_status(self, update: Update, context):
        """상태 조회"""
        status = self.scheduler.get_status()
        message = f"""
📊 현재 상태
━━━━━━━━━━━━━━
🔄 스케줄러: {'실행 중' if status['running'] else '중지'}
📝 오늘 포스팅: {status['posts_today']}/{status['daily_limit']}
📈 총 포스팅: {status['total_posts']}
⚠️ 에러: {status['errors_count']}회
⏰ 마지막 포스팅: {status['last_post_time'] or 'N/A'}
"""
        await update.message.reply_text(message)

    async def cmd_post(self, update: Update, context):
        """즉시 포스팅"""
        await update.message.reply_text("📝 즉시 포스팅 시작...")
        await self.scheduler._post_job()
```

---

### 4.3 통계 리포트

**현재 문제**: 성과 분석 불가

**구현 파일**: `monitoring/reporter.py` (신규)

**작업 내용**:

```python
# monitoring/reporter.py (신규 생성)

class StatisticsReporter:
    """통계 리포트 생성"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_daily_report(self, date: datetime = None) -> Dict:
        """일일 리포트"""
        date = date or datetime.now()

        return {
            "date": date.strftime("%Y-%m-%d"),
            "posts_count": self._count_posts(date),
            "success_rate": self._calculate_success_rate(date),
            "top_categories": self._get_top_categories(date),
            "avg_quality_score": self._get_avg_quality(date),
            "errors": self._get_error_summary(date),
        }

    def generate_weekly_report(self) -> Dict:
        """주간 리포트"""
        pass

    async def send_daily_report(self):
        """텔레그램으로 일일 리포트 발송"""
        report = self.generate_daily_report()

        message = f"""
📊 일일 리포트 ({report['date']})
━━━━━━━━━━━━━━━━━━━━
📝 포스팅: {report['posts_count']}개
✅ 성공률: {report['success_rate']:.1f}%
🏆 인기 카테고리: {', '.join(report['top_categories'][:3])}
⭐ 평균 품질: {report['avg_quality_score']:.1f}점
⚠️ 에러: {len(report['errors'])}건
"""
        notifier = TelegramNotifier()
        await notifier.send_message(message)
```

**스케줄러에 추가**:

```python
# 매일 자정에 일일 리포트 발송
self.scheduler.add_job(
    self._send_daily_report,
    trigger=CronTrigger(hour=0, minute=5),
    id="daily_report"
)
```

---

## Phase 5: 확장 기능 (선택)

### 5.1 A/B 테스트 시스템

**목적**: 어떤 스타일의 글이 더 효과적인지 테스트

**구현 내용**:
- 제목 스타일 변형 (질문형 vs 선언형)
- 이미지 스타일 변형
- CTA 문구 변형
- 결과 추적 및 분석

### 5.2 댓글 자동 대응

**목적**: 댓글에 자동 답변

**구현 내용**:
- 댓글 알림 감지
- Claude로 적절한 답변 생성
- 자동 또는 반자동 답변

### 5.3 다른 플랫폼 확장

**목적**: 네이버 외 플랫폼 지원

**후보**:
- 티스토리
- 브런치
- 미디엄
- 링크드인

---

## 구현 우선순위 요약

| 순위 | 항목 | 예상 작업량 | 중요도 |
|------|------|------------|--------|
| 1 | 세션 자동 갱신 | 중 | 🔴 필수 |
| 2 | 에러 복구 시스템 | 중 | 🔴 필수 |
| 3 | 헬스체크 시스템 | 소 | 🔴 필수 |
| 4 | 중복 주제 방지 | 소 | 🟠 높음 |
| 5 | 주제 카테고리 순환 | 소 | 🟠 높음 |
| 6 | 다중 계정 관리 | 중 | 🟠 높음 |
| 7 | 글 품질 강화 | 중 | 🟡 중간 |
| 8 | 이미지-글 연관성 | 중 | 🟡 중간 |
| 9 | SEO 최적화 | 중 | 🟡 중간 |
| 10 | 텔레그램 원격 제어 | 중 | 🟢 낮음 |
| 11 | 웹 대시보드 | 대 | 🟢 낮음 |
| 12 | 통계 리포트 | 소 | 🟢 낮음 |

---

## 실행 계획

### Week 1: 안정성 확보
- [ ] 세션 자동 갱신 시스템 구현
- [ ] 에러 복구 시스템 구현
- [ ] 헬스체크 시스템 구현
- [ ] 통합 테스트

### Week 2: 자동화 완성
- [ ] 중복 주제 방지 구현
- [ ] 주제 카테고리 순환 구현
- [ ] 24시간 운영 테스트

### Week 3: 품질 개선
- [ ] QA Agent 강화
- [ ] 이미지-글 연관성 개선
- [ ] SEO 최적화 기본 구현

### Week 4: 모니터링
- [ ] 텔레그램 원격 제어
- [ ] 통계 리포트
- [ ] 최종 안정화

---

## 주의사항

1. **네이버 봇 탐지**: 인간 딜레이 유지, 과도한 포스팅 자제
2. **API 비용**: Claude Haiku 우선 사용, Sonnet은 필요시만
3. **세션 관리**: 정기적 세션 갱신으로 만료 방지
4. **백업**: 세션 파일, DB 정기 백업
5. **로그**: 상세 로그로 문제 추적 가능하게

---

> 이 문서는 프로젝트 진행에 따라 업데이트됩니다.
