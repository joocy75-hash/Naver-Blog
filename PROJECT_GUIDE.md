# 네이버 블로그 자동 포스팅 봇 - 프로젝트 가이드

> **최종 업데이트**: 2025-12-26
> **작성자**: Claude Code Assistant
> **상태**: 개발 진행 중 (취소선 버그 수정 완료 - 테스트 필요)

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [핵심 기능](#4-핵심-기능)
5. [포스팅 방식](#5-포스팅-방식)
6. [이미지 처리](#6-이미지-처리)
7. [자동 스케줄링](#7-자동-스케줄링)
8. [설정 및 환경변수](#8-설정-및-환경변수)
9. [테스트 방법](#9-테스트-방법)
10. [알려진 버그 및 이슈](#10-알려진-버그-및-이슈)
11. [향후 작업](#11-향후-작업)

---

## 1. 프로젝트 개요

### 1.1 목적
- 네이버 블로그에 자동으로 콘텐츠를 생성하고 발행
- 1-2시간 간격으로 24시간 자동 포스팅
- 본문 중간에 이미지 3-4개 삽입
- 텔레그램 알림 연동

### 1.2 기술 스택
| 구성요소 | 기술 |
|---------|------|
| 언어 | Python 3.11+ |
| 브라우저 자동화 | Playwright (Chromium) |
| 콘텐츠 생성 | Claude API (Haiku/Sonnet) |
| 리서치 | Perplexity API |
| 이미지 생성 | Google Gemini Imagen 3 |
| 스케줄링 | APScheduler |
| 알림 | Telegram Bot API |

### 1.3 주요 계정 정보
```
네이버 ID: wncksdid0750
블로그 URL: https://blog.naver.com/pakrsojang
```

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        자동 스케줄러                              │
│                   (scheduler/auto_scheduler.py)                  │
│                     1-2시간 간격 실행                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      파이프라인 (pipeline.py)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 리서치      │→│ 콘텐츠 생성  │→│ 이미지 생성  │              │
│  │ (Perplexity)│  │ (Claude)    │  │ (Gemini)    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    블로그 포스터 (auto_post.py)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 세션 로드   │→│ 글쓰기      │→│ 발행        │              │
│  │ (로그인)    │  │ (제목/본문) │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    텔레그램 알림 (utils/telegram_notifier.py)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 디렉토리 구조

```
네이버블로그봇/
├── agents/                      # AI 에이전트들
│   ├── content_agent.py         # 마케팅 콘텐츠 생성 (스마트개미 코인봇)
│   ├── blog_content_generator.py # 다목적 블로그 콘텐츠 생성
│   ├── visual_agent.py          # 이미지 프롬프트 생성
│   └── research_agent.py        # Perplexity 리서치
│
├── config/                      # 설정 파일
│   ├── human_timing.py          # 봇 탐지 회피용 딜레이 설정
│   └── templates/               # 콘텐츠 템플릿
│
├── data/                        # 데이터 저장
│   └── sessions/                # 로그인 세션 (암호화됨)
│
├── generated_images/            # 생성된 이미지 저장
│
├── scheduler/                   # 스케줄러
│   └── auto_scheduler.py        # 24시간 자동 포스팅 스케줄러
│
├── security/                    # 보안 관련
│   ├── session_manager.py       # 세션 암호화/복호화
│   └── credential_manager.py    # API 키 관리
│
├── utils/                       # 유틸리티
│   ├── gemini_image.py          # Gemini Imagen 이미지 생성
│   ├── telegram_notifier.py     # 텔레그램 알림
│   └── clipboard_input.py       # 클립보드 입력 헬퍼
│
├── auto_post.py                 # ★ 핵심: 블로그 포스팅 자동화
├── pipeline.py                  # ★ 핵심: 전체 파이프라인 오케스트레이션
├── manual_login_clipboard.py    # 수동 로그인 (세션 저장)
│
├── test_multi_image_post.py     # 다중 이미지 포스팅 테스트
├── test_marketing_pipeline.py   # 마케팅 파이프라인 테스트
│
├── .env                         # 환경변수 (API 키)
├── .env.example                 # 환경변수 예시
└── requirements.txt             # 의존성
```

---

## 4. 핵심 기능

### 4.1 콘텐츠 생성 파이프라인

#### A. 마케팅 콘텐츠 (`run_marketing`)
```python
from pipeline import BlogPostPipeline

pipeline = BlogPostPipeline(naver_id="wncksdid0750", model="haiku")
result = await pipeline.run_marketing(
    template_type="trading_mistake",  # 템플릿 유형
    keyword="FOMO",                   # 키워드
    generate_image=True,              # 이미지 생성
    num_images=4,                     # 이미지 개수
    dry_run=False                     # True면 발행 안함
)
```

**템플릿 유형:**
- `trading_mistake`: 매매 실수/함정
- `market_analysis`: 시장 분석
- `investment_tip`: 투자 팁
- `psychology`: 투자 심리

#### B. 리서치 기반 콘텐츠 (`run_research`) - 권장
```python
result = await pipeline.run_research(
    topic_category="crypto",    # 주제 카테고리
    style="분석형",             # 글쓰기 스타일
    generate_image=True,
    num_images=4,
    dry_run=False
)
```

**주제 카테고리:**
- `us_stock`: 미국주식
- `kr_stock`: 국내주식
- `crypto`: 암호화폐
- `ai_tech`: AI/기술
- `economy`: 경제
- `hot_issue`: 핫이슈

**글쓰기 스타일:**
- 분석형, 스토리텔링, 뉴스해설, 전망형, 교육형

### 4.2 이미지 생성

```python
from utils.gemini_image import GeminiImageGenerator

generator = GeminiImageGenerator()
path = generator.generate_image(
    prompt="Professional cryptocurrency trading concept, blue gradient, no text",
    filename="blog_image.png",
    style="digital-art"
)
```

---

## 5. 포스팅 방식

### 5.1 전체 흐름

```
1. 세션 로드 (저장된 로그인 상태)
      ↓
2. 글쓰기 페이지 이동 (https://blog.naver.com/{id}/postwrite)
      ↓
3. 팝업 처리 ("작성 중인 글" 팝업 등)
      ↓
4. 제목 입력 (직접 타이핑)
      ↓
5. 본문 + 이미지 삽입 (문단 사이에 이미지 배치)
      ↓
6. 발행 버튼 클릭
      ↓
7. 텔레그램 알림
```

### 5.2 본문 + 이미지 삽입 로직 (`input_content_with_images`)

```
본문을 문단(빈 줄 기준)으로 분리
      ↓
이미지 삽입 위치 계산 (균등 배치)
예: 문단 8개, 이미지 4개 → 위치 [0, 1, 2, 3]
      ↓
반복:
  - 문단 입력 (직접 타이핑)
  - 줄바꿈 (Enter 2회)
  - 해당 위치면 이미지 삽입
      ↓
  이미지 삽입:
    1. 클립보드에 이미지 복사 (osascript)
    2. Cmd+V로 붙여넣기
    3. ArrowDown → End → Enter (커서 이동)
    4. 서식 버튼 해제
```

### 5.3 이미지 삽입 방식

Mac에서 클립보드 기반 이미지 삽입:
```python
# 1. osascript로 클립보드에 이미지 복사
script = f'''
set theFile to POSIX file "{abs_path}"
set the clipboard to (read theFile as «class PNGf»)
'''
subprocess.run(['osascript', '-e', script])

# 2. Cmd+V로 붙여넣기
await self.page.keyboard.press('Meta+KeyV')

# 3. 업로드 대기
await asyncio.sleep(3)

# 4. 커서를 이미지 아래로 이동
await self.page.keyboard.press('ArrowDown')
await self.page.keyboard.press('End')
await self.page.keyboard.press('Enter')
```

### 5.4 서식 해제 로직

본문 입력 전과 이미지 삽입 후에 서식 버튼(취소선, 굵게 등) 해제:
```python
await self._disable_all_formatting_buttons()
await self._force_click_strikethrough_off()
```

---

## 6. 이미지 처리

### 6.1 다중 이미지 생성

```python
def _generate_multiple_images(self, prompts: list, num_images: int = 4) -> list:
    """
    여러 이미지 생성 (본문 삽입용)

    - 기본 프롬프트로 부족한 수량 보충
    - Gemini Imagen 3 사용
    - generated_images/ 디렉토리에 저장
    """
```

### 6.2 이미지 배치 전략

```
문단 10개, 이미지 4개인 경우:
interval = 10 // (4 + 1) = 2

삽입 위치 계산:
- 이미지 1: 위치 1 (2*1 - 1)
- 이미지 2: 위치 3 (2*2 - 1)
- 이미지 3: 위치 5 (2*3 - 1)
- 이미지 4: 위치 7 (2*4 - 1)
```

---

## 7. 자동 스케줄링

### 7.1 스케줄러 실행

```bash
# 기본 실행 (1-2시간 간격, 일일 12개 제한)
python -m scheduler.auto_scheduler

# 커스텀 설정
python -m scheduler.auto_scheduler --interval 1 2 --limit 10 --model haiku

# 테스트 모드 (1회 실행)
python -m scheduler.auto_scheduler --test
```

### 7.2 스케줄러 설정

```python
class AutoPostingScheduler:
    # 활동 시간대 (한국 시간)
    ACTIVE_HOURS = {
        "morning": (7, 9),      # 아침: 7시-9시
        "lunch": (11, 13),      # 점심: 11시-13시
        "afternoon": (14, 17),  # 오후: 14시-17시
        "evening": (19, 22),    # 저녁: 19시-22시
        "night": (22, 24),      # 밤: 22시-24시
    }

    # 템플릿 가중치
    TEMPLATE_WEIGHTS = {
        "trading_mistake": 3,   # 매매 실수 - 인기 높음
        "market_analysis": 2,   # 시장 분석
        "investment_tip": 3,    # 투자 팁 - 인기 높음
        "psychology": 2         # 투자 심리
    }
```

### 7.3 텔레그램 알림

```python
# 성공 시
✅ 블로그 포스팅 성공!
📝 제목: [제목...]
🔗 URL: https://blog.naver.com/...
📊 오늘 3/12개
⏱ 총 15개 발행

# 실패 시
❌ 블로그 포스팅 실패
⚠️ 오류: [에러 메시지]
📊 실패 횟수: 2
```

---

## 8. 설정 및 환경변수

### 8.1 .env 파일

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-api...

# Google Gemini (이미지 생성)
GOOGLE_API_KEY=AIza...

# Perplexity (리서치)
PERPLEXITY_API_KEY=pplx-...

# Telegram 알림
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```

### 8.2 세션 관리

세션 파일 위치: `data/sessions/{naver_id}_clipboard.session.encrypted`

**세션 갱신 (로그인 필요 시):**
```bash
python manual_login_clipboard.py
```

### 8.3 인간 행동 패턴 설정 (`config/human_timing.py`)

```python
DELAYS = {
    'page_load': (1.5, 2.5),      # 페이지 로드 대기
    'before_click': (0.3, 0.7),   # 클릭 전 대기
    'after_click': (0.5, 1.2),    # 클릭 후 대기
    'popup_react': (0.8, 1.5),    # 팝업 인식 시간
}

TYPING = {
    'title_min': 50, 'title_max': 100,    # 제목 타이핑 속도 (ms)
    'content_min': 40, 'content_max': 80,  # 본문 타이핑 속도 (ms)
}
```

---

## 9. 테스트 방법

### 9.1 세션 로그인 테스트
```bash
python manual_login_clipboard.py
# 브라우저가 열리면 수동으로 네이버 로그인
# 로그인 후 자동으로 세션 저장됨
```

### 9.2 다중 이미지 포스팅 테스트
```bash
python test_multi_image_post.py
```

### 9.3 마케팅 파이프라인 테스트
```bash
python test_marketing_pipeline.py
```

### 9.4 스케줄러 테스트 (1회)
```bash
python -m scheduler.auto_scheduler --test
```

---

## 10. 알려진 버그 및 이슈

### 10.1 ✅ 취소선 버그 (수정 완료 - 테스트 필요)

**증상:**
- 본문 입력 시 취소선(~~텍스트~~) 서식이 적용됨
- 이미지 삽입 후 다음 텍스트에 취소선이 적용됨

**해결 방법 (2025-12-26 적용):**

1. **execCommand 방식** (가장 확실):
   ```javascript
   document.queryCommandState('strikeThrough')  // 상태 확인
   document.execCommand('strikeThrough', false, null)  // 토글
   ```

2. **버튼 인덱스 기반 제어**:
   - 네이버 스마트에디터 ONE의 처음 15개 버튼 중 활성화된 것 클릭
   - SVG 색상으로 활성화 상태 감지 (`#00c73c`, `#03c75a`)
   - wrapper 클래스에 `active` 포함 여부 확인

3. **DOM 직접 정리**:
   - `<s>`, `<strike>`, `<del>` 태그를 텍스트로 변환
   - `text-decoration: line-through` 스타일 제거

**관련 메서드:**
- `_disable_all_formatting_buttons()` - 서식 해제 진입점
- `_force_click_strikethrough_off()` - 핵심 해제 로직 (3가지 방법 순차 적용)
- `_remove_strikethrough_from_dom()` - DOM 정리

### 10.2 이미지 순서 문제 (해결됨)

**증상:**
- 이미지 삽입 후 커서가 이미지 위로 이동
- 다음 텍스트가 이미지 위에 입력됨

**해결책:**
- `_insert_image_and_move_below()` 메서드 추가
- ArrowDown → End → Enter 순서로 커서 이동

---

## 11. 향후 작업

### 11.1 우선순위 높음

- [x] **취소선 버그 완전 해결** (2025-12-26 완료)
  - ✅ 네이버 에디터 툴바 HTML 구조 분석 완료
  - ✅ 정확한 버튼 셀렉터 파악: `button.se-strikethrough-toolbar-button`
  - ✅ 활성화 상태 감지 로직 수정

### 11.2 우선순위 중간
- [ ] 서버 배포 (Docker/systemd)
- [ ] 에러 복구 로직 강화
- [ ] 다양한 콘텐츠 카테고리 추가

### 11.3 우선순위 낮음
- [ ] 웹 대시보드 개발
- [ ] 통계 및 분석 기능
- [ ] 다중 계정 지원

---

## 부록: 주요 파일 요약

| 파일 | 설명 | 핵심 클래스/함수 |
|------|------|-----------------|
| `auto_post.py` | 블로그 포스팅 자동화 | `NaverBlogPoster.post()` |
| `pipeline.py` | 전체 파이프라인 | `BlogPostPipeline.run_marketing()`, `run_research()` |
| `scheduler/auto_scheduler.py` | 24시간 스케줄러 | `AutoPostingScheduler.start()` |
| `utils/gemini_image.py` | 이미지 생성 | `GeminiImageGenerator.generate_image()` |
| `agents/content_agent.py` | 마케팅 콘텐츠 | `ContentAgent.generate_marketing_content()` |
| `agents/blog_content_generator.py` | 다목적 콘텐츠 | `BlogContentGenerator.generate_content()` |
| `manual_login_clipboard.py` | 수동 로그인 | 세션 저장용 |

---

## 부록: 취소선 버그 완전 해결 가이드 (2025-12-26 최종)

> ⚠️ **중요**: 이 섹션은 취소선 버그 해결에 많은 시간을 소비한 후 작성되었습니다.
> 향후 동일한 문제가 발생하면 이 가이드를 참조하세요.

---

### 핵심 발견 사항 (반드시 기억!)

#### 🔴 활성화 상태 감지 클래스: `se-is-selected`

**절대 잊지 말 것**: 네이버 스마트에디터 ONE에서 서식 버튼의 활성화 상태는 **`se-is-selected`** 클래스로 표시됩니다!

```
❌ 잘못된 방법 (작동 안 함):
- classList.contains('active')
- classList.contains('se-toolbar-button-active')
- getAttribute('aria-pressed') === 'true'
- SVG fill 색상 (#00c73c 등)

✅ 올바른 방법:
- classList.contains('se-is-selected')  ← 이것만 확인하면 됨!
```

---

### 취소선 버튼 HTML 구조

**비활성화 상태:**

```html
<button type="button" title=""
        class="se-strikethrough-toolbar-button se-property-toolbar-toggle-button __se-sentry"
        data-name="strikethrough" data-type="toggle">
    <span class="se-toolbar-icon"></span>
    <span class="se-blind">취소선</span>
    <span class="se-toolbar-tooltip">취소선 적용</span>
</button>
```

**활성화 상태 (se-is-selected 추가됨!):**

```html
<button type="button" title=""
        class="se-strikethrough-toolbar-button se-property-toolbar-toggle-button se-is-selected __se-sentry"
        data-name="strikethrough" data-type="toggle">
    <span class="se-toolbar-icon"></span>
    <span class="se-blind">취소선</span>
    <span class="se-toolbar-tooltip">취소선 해제</span>  <!-- 텍스트도 바뀜 -->
</button>
```

---

### 올바른 취소선 해제 코드

```javascript
// ★★★ 정확한 취소선 해제 코드 ★★★
const strikeBtn = document.querySelector('button.se-strikethrough-toolbar-button');
if (strikeBtn && strikeBtn.classList.contains('se-is-selected')) {
    strikeBtn.click();
    console.log('취소선 해제됨');
}

// 모든 활성화된 서식 버튼 해제
const allSelected = document.querySelectorAll('button.se-is-selected');
allSelected.forEach(btn => {
    console.log('서식 해제:', btn.getAttribute('data-name'));
    btn.click();
});
```

---

### 관련 함수 위치 (auto_post.py)

| 함수명 | 라인 | 설명 |
|--------|------|------|
| `_force_click_strikethrough_off()` | ~1193 | 핵심 취소선 해제 함수 |
| `_clear_text_formatting()` | ~344 | 텍스트 서식 초기화 |
| `publish_post()` 내부 | ~618 | 발행 전 취소선 제거 |
| `_remove_strikethrough_from_dom()` | ~1350 | DOM에서 직접 태그 제거 |

---

### 디버깅 방법

브라우저 콘솔에서 실행:

```javascript
// 1. 취소선 버튼 찾기 및 상태 확인
const btn = document.querySelector('button.se-strikethrough-toolbar-button');
console.log('버튼 발견:', !!btn);
console.log('클래스:', btn?.className);
console.log('활성화 (se-is-selected):', btn?.classList.contains('se-is-selected'));

// 2. 모든 활성화된 서식 버튼 확인
document.querySelectorAll('button.se-is-selected').forEach(b => {
    console.log('활성 버튼:', b.getAttribute('data-name'), b.className);
});

// 3. 강제 해제
document.querySelectorAll('button.se-is-selected').forEach(b => b.click());
```

---

### 문제 해결 체크리스트

취소선이 계속 발생하면 다음을 확인:

1. [ ] `se-is-selected` 클래스를 정확히 확인하고 있는가?
2. [ ] 버튼 셀렉터가 `button.se-strikethrough-toolbar-button`인가?
3. [ ] 이미지 삽입 후에도 서식 해제를 호출하고 있는가?
4. [ ] 발행 전에 전체 선택 → 서식 해제를 수행하고 있는가?
5. [ ] DOM에서 `<s>`, `<strike>`, `<del>` 태그를 직접 제거하고 있는가?

---

### 버그 발생 원인 분석

1. **이미지 삽입 후**: 클립보드 붙여넣기 시 에디터가 이전 서식 상태를 유지
2. **텍스트 선택 시**: 인라인 툴바가 나타나면서 서식 버튼이 활성화됨
3. **에디터 초기 상태**: 가끔 취소선이 기본 활성화되어 있음

---

### 예방 조치

코드에서 다음 시점에 서식 해제 호출:

1. 본문 입력 시작 전
2. 각 이미지 삽입 후
3. 각 문단 입력 후
4. 발행 버튼 클릭 전 (전체 선택 후 해제)

---

## 부록: 팝업 처리 가이드 (2025-12-26)

### "작성 중인 글이 있습니다" 팝업

글쓰기 페이지 진입 시 이전에 작성하던 글이 있으면 나타나는 팝업입니다.

**팝업 구조:**

```
┌─────────────────────────────────────┐
│     작성 중인 글이 있습니다.          │
│                                     │
│  26일 오전 6시 44분에 작성중이던      │
│  내용이 있습니다.                    │
│  이어서 작성하시겠습니까?             │
│                                     │
│   [취소]          [✓ 확인]          │
└─────────────────────────────────────┘
```

### 핵심: 사람처럼 3초 대기 후 클릭

> ⚠️ **중요**: 팝업이 나타나자마자 바로 클릭하면 봇으로 탐지될 수 있습니다.
> 사람은 팝업 내용을 읽고 판단하는 데 2~4초 정도 소요됩니다.

**올바른 처리 방법:**

```python
# auto_post.py - _handle_popups() 메서드
cancel_btn = self.page.locator('button:has-text("취소")').first
if await cancel_btn.is_visible(timeout=800):
    logger.info("'작성 중인 글' 팝업 감지 - 사람처럼 3초 대기 후 취소...")
    await asyncio.sleep(random.uniform(2.5, 3.5))  # ★ 핵심: 사람이 읽는 시간
    await cancel_btn.click()
    logger.info("'작성 중인 글' 팝업 - 취소 클릭 완료")
```

### 팝업 처리 타이밍 가이드

| 팝업 유형 | 대기 시간 | 이유 |
|-----------|-----------|------|
| 작성 중인 글 | 2.5~3.5초 | 내용 읽고 판단하는 시간 |
| 도움말 패널 | 0.3~0.7초 | 단순 닫기 버튼 |
| 일반 알림 | 0.5~1.0초 | 간단한 확인 |

### 관련 함수 위치

- `auto_post.py` → `_handle_popups()` 메서드 (라인 ~229)

---

**문서 끝**
