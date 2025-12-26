# 네이버 블로그 자동화 봇 - 현재 상황

> 마지막 업데이트: 2025-12-26

---

## 1. 프로젝트 개요

**목표**: AI 기반 네이버 블로그 자동 포스팅 시스템
- 실시간 뉴스/트렌드 수집 → 글 생성 → 이미지 생성 → 자동 발행
- 24시간 무인 운영 가능한 완전 자동화 시스템

**페르소나**: 스마트개미 코인봇
- 암호화폐/투자 전문 블로거
- 카카오톡 오픈채팅 유도

---

## 2. 구현 완료된 기능 ✅

### 2.1 핵심 에이전트

| 에이전트 | 파일 | 상태 | 설명 |
|---------|------|------|------|
| Research Agent | `agents/research_agent.py` | ✅ 완료 | Perplexity API로 실시간 뉴스/트렌드 수집 |
| Content Agent | `agents/content_agent.py` | ✅ 완료 | Claude Haiku/Sonnet으로 블로그 글 생성 |
| Visual Agent | `agents/visual_agent.py` | ✅ 완료 | 이미지 프롬프트 생성 |
| QA Agent | `agents/qa_agent.py` | ✅ 완료 | 콘텐츠 품질 검증 |
| Upload Agent | `agents/upload_agent.py` | ✅ 완료 | 네이버 블로그 업로드 |
| Marketing Content | `agents/marketing_content.py` | ✅ 완료 | 마케팅 템플릿 기반 콘텐츠 |
| Blog Generator | `agents/blog_content_generator.py` | ✅ 완료 | 다목적 블로그 콘텐츠 생성 |

### 2.2 자동화 인프라

| 모듈 | 파일 | 상태 | 설명 |
|------|------|------|------|
| 메인 오케스트레이터 | `main.py` | ✅ 완료 | Research → Content → Visual → QA → Upload 파이프라인 |
| 통합 파이프라인 | `pipeline.py` | ✅ 완료 | 마케팅/리서치/뉴스 기반 파이프라인 |
| 자동 스케줄러 | `scheduler/auto_scheduler.py` | ✅ 완료 | APScheduler 기반 24시간 자동 포스팅 |
| 블로그 포스터 | `auto_post.py` | ✅ 완료 | Playwright 기반 네이버 블로그 발행 |

### 2.3 유틸리티

| 유틸 | 파일 | 상태 | 설명 |
|------|------|------|------|
| Gemini 이미지 | `utils/gemini_image.py` | ✅ 완료 | Imagen 4.0 밈 스타일 이미지 생성 |
| 텔레그램 알림 | `utils/telegram_notifier.py` | ✅ 완료 | 포스팅 성공/실패 알림 |
| 클립보드 입력 | `utils/clipboard_input.py` | ✅ 완료 | 클립보드 기반 텍스트 입력 |
| 인간 행동 시뮬 | `utils/human_behavior.py` | ✅ 완료 | 봇 탐지 회피용 자연스러운 딜레이 |
| 비용 최적화 | `utils/cost_optimizer.py` | ✅ 완료 | API 비용 모니터링 |

### 2.4 보안/설정

| 모듈 | 파일 | 상태 | 설명 |
|------|------|------|------|
| 자격증명 관리 | `security/credential_manager.py` | ✅ 완료 | macOS 키체인 기반 API 키 관리 |
| 세션 관리 | `security/session_manager.py` | ✅ 완료 | 네이버 로그인 세션 저장/로드 |
| 설정 | `config/settings.py` | ✅ 완료 | 환경 변수 및 설정 |
| 인간 타이밍 | `config/human_timing.py` | ✅ 완료 | 딜레이/타이밍 설정 |
| 데이터베이스 | `models/database.py` | ✅ 완료 | SQLite 기반 포스팅 기록 |

### 2.5 최근 개선 사항 (이번 세션)

| 기능 | 상태 | 설명 |
|------|------|------|
| 마크다운 → 네이버 서식 | ✅ 완료 | `##`→소제목, `**`→굵게, `>`→인용구 자동 변환 |
| 밈 스타일 이미지 | ✅ 완료 | 16개 캐릭터 풀, 다양한 액션/배경/스타일 조합 |
| 이미지 다양성 확보 | ✅ 완료 | 랜덤 조합으로 매번 다른 이미지 생성 |
| 주제 연관 이미지 | ✅ 완료 | 키워드 기반 topic_hint 시스템 |
| 취소선 해제 | ✅ 완료 | `se-is-selected` 클래스 감지 및 해제 |

---

## 3. 미구현/개선 필요 사항 ⚠️

### 3.1 자동화 관련 (높은 우선순위)

| 항목 | 현재 상태 | 필요 작업 |
|------|----------|----------|
| **완전 무인 운영** | 부분 구현 | 에러 복구, 세션 갱신, 헬스체크 필요 |
| **다중 계정 관리** | 미구현 | 여러 네이버 계정 순환 포스팅 |
| **중복 주제 방지** | 미구현 | 최근 포스팅 주제와 비교하여 중복 회피 |
| **콘텐츠 다양성** | 부분 구현 | 주제 카테고리 자동 순환 (crypto만 집중되는 문제) |

### 3.2 안정성 관련

| 항목 | 현재 상태 | 필요 작업 |
|------|----------|----------|
| **세션 자동 갱신** | 미구현 | 세션 만료 감지 및 자동 재로그인 |
| **에러 복구** | 부분 구현 | 연속 실패 시 자동 복구 로직 |
| **헬스체크** | 미구현 | 시스템 상태 모니터링 및 알림 |
| **로그 관리** | 기본 구현 | 로그 로테이션, 오래된 로그 삭제 |

### 3.3 품질 관련

| 항목 | 현재 상태 | 필요 작업 |
|------|----------|----------|
| **글 품질 점수** | 기본 구현 | QA Agent 점수 기반 발행 여부 결정 강화 |
| **이미지-글 연관성** | 부분 구현 | 글 내용과 더 정확히 매칭되는 이미지 |
| **SEO 최적화** | 미구현 | 키워드 최적화, 메타 태그 |

### 3.4 모니터링/관리

| 항목 | 현재 상태 | 필요 작업 |
|------|----------|----------|
| **대시보드** | 미구현 | 웹 기반 상태 모니터링 UI |
| **통계 리포트** | 부분 구현 | 일일/주간 포스팅 통계 |
| **원격 제어** | 미구현 | 텔레그램 명령어로 시작/중지/상태 확인 |

---

## 4. 파일 구조

```
네이버블로그봇/
├── main.py                      # 메인 오케스트레이터
├── pipeline.py                  # 통합 파이프라인
├── auto_post.py                 # 네이버 블로그 포스팅
├── manual_login.py              # 수동 로그인 (세션 저장용)
├── manual_login_clipboard.py    # 클립보드 로그인
│
├── agents/                      # AI 에이전트
│   ├── research_agent.py        # 리서치 (Perplexity)
│   ├── content_agent.py         # 콘텐츠 생성 (Claude)
│   ├── visual_agent.py          # 비주얼 생성
│   ├── qa_agent.py              # 품질 검증
│   ├── upload_agent.py          # 업로드
│   ├── marketing_content.py     # 마케팅 콘텐츠
│   └── blog_content_generator.py # 다목적 생성기
│
├── scheduler/                   # 스케줄링
│   └── auto_scheduler.py        # 24시간 자동 스케줄러
│
├── utils/                       # 유틸리티
│   ├── gemini_image.py          # Imagen 이미지 생성
│   ├── telegram_notifier.py     # 텔레그램 알림
│   ├── clipboard_input.py       # 클립보드 입력
│   ├── human_behavior.py        # 인간 행동 시뮬
│   └── cost_optimizer.py        # 비용 최적화
│
├── security/                    # 보안
│   ├── credential_manager.py    # API 키 관리 (키체인)
│   └── session_manager.py       # 세션 관리
│
├── config/                      # 설정
│   ├── settings.py              # 환경 설정
│   └── human_timing.py          # 타이밍 설정
│
├── models/                      # 데이터
│   └── database.py              # SQLite DB
│
├── monitoring/                  # 모니터링 (미사용)
│
├── tests/                       # 테스트 (미사용)
│
└── generated_images/            # 생성된 이미지 저장소
```

---

## 5. API 키 현황

| API | 용도 | 상태 |
|-----|------|------|
| Claude (Anthropic) | 글 생성 | ✅ 키체인 저장됨 |
| Perplexity | 실시간 리서치 | ✅ 키체인 저장됨 |
| Google (Gemini) | 이미지 생성 | ✅ 키체인 저장됨 |
| Telegram Bot | 알림 | ✅ 환경변수 설정됨 |
| Naver Session | 블로그 발행 | ✅ 세션 파일 저장됨 |

---

## 6. 실행 방법

### 6.1 1회 포스팅 테스트

```bash
# 리서치 기반 (권장)
python pipeline.py research --dry

# 마케팅 기반
python pipeline.py marketing --dry

# 실제 발행 (--dry 제거)
python pipeline.py research
```

### 6.2 24시간 자동 포스팅

```bash
# 기본 실행 (1-2시간 간격, 일일 12개)
python -m scheduler.auto_scheduler

# 커스텀 설정
python -m scheduler.auto_scheduler --interval 1.5 2.5 --limit 10
```

### 6.3 테스트 스크립트

```bash
# 마크다운 서식 테스트
python test_post_with_telegram.py

# 이미지 생성 테스트
python test_multi_image_post.py
```

---

## 7. 알려진 이슈

1. **세션 만료**: 네이버 세션이 만료되면 수동으로 `manual_login.py` 실행 필요
2. **이미지 생성 실패**: Imagen API 제한으로 가끔 실패 → 기존 이미지로 폴백
3. **봇 탐지**: 과도한 포스팅 시 네이버 봇 탐지 가능성 → 인간 딜레이로 대응

---

## 8. 다음 단계

**즉시 필요**:
1. 완전 무인 운영을 위한 에러 복구 로직
2. 세션 자동 갱신 시스템
3. 다중 주제 카테고리 순환

**중기 목표**:
1. 웹 대시보드
2. 텔레그램 원격 제어
3. 다중 계정 관리

자세한 작업 계획은 `WORK_PLAN_DETAIL.md` 참조.
