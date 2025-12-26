# 💰 API 비용 최적화 가이드

## 🎯 최적화 목표

**기존 비용**: $100-180/월
**최적화 후**: $10-25/월
**절감률**: **85% 이상!**

---

## 📊 비용 구조 변경

### Before (기존)
```
Claude 4.5 Sonnet: $50-100/월  (메인 콘텐츠 생성)
Gemini 3 Pro:      $30-60/월   (이미지 생성)
Perplexity:        $20/월      (리서치)
───────────────────────────────
총계:              $100-180/월
```

### After (최적화)
```
Claude Haiku 3.5:  $8-15/월    (메인 콘텐츠 - 80% 저렴!)
Gemini 3 Pro:      $50-80/월   (이미지 + 추가 콘텐츠 생성 - 크레딧 활용)
Perplexity:        $10/월      (캐싱으로 호출 반감)
───────────────────────────────
총계:              $68-105/월 (실제 지출 $18-25/월, Gemini 크레딧 활용)
```

---

## 🚀 적용된 최적화 전략

### 1️⃣ Claude Haiku 3.5 사용 (80% 비용 절감)

**변경 사항**:
```python
# main.py에서 기본 모델을 Haiku로 변경
content_data = self.content_agent.generate_post(
    research_data=research_data,
    model="haiku"  # ← Sonnet 대신 Haiku 사용!
)
```

**비용 비교**:
| 모델 | Input ($/1M tokens) | Output ($/1M tokens) | 절감률 |
|------|---------------------|----------------------|--------|
| Sonnet 4.5 | $3.00 | $15.00 | - |
| **Haiku 3.5** | **$0.80** | **$4.00** | **73-80%** |

### 2️⃣ Prompt Caching (90% 추가 절감)

**작동 방식**:
- 시스템 프롬프트를 캐시에 저장
- 5분 내 재사용 시 캐시에서 로드
- **캐시 읽기 비용: $0.08/1M tokens (원래의 10%!)**

```python
# 자동으로 적용됨
system=[
    {
        "type": "text",
        "text": self.SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # 캐싱!
    }
]
```

**절감 효과**:
- 첫 호출: 일반 비용
- 2번째 호출 (5분 내): 90% 절감!
- 하루 3회 포스팅 시 2회는 캐시 활용

### 3️⃣ 응답 캐싱 시스템

**작동 방식**:
```python
# 동일 주제는 24시간 동안 캐시된 콘텐츠 재사용
cached = cost_optimizer.get_cached_response("content", cache_key_data)
if cached:
    return cached  # API 호출 0원!
```

**절감 효과**:
- 비슷한 주제 반복 시 API 호출 불필요
- 예상 절감: 월 20-30회 호출 절약 = $5-10 절감

### 4️⃣ Gemini 3 Pro 최대 활용 (140만원 크레딧)

**확장 사용 전략**:

#### A. 콘텐츠 생성에도 Gemini 활용
```python
# Gemini로 초안 생성 → Haiku로 다듬기
# Gemini는 크레딧으로, 최종 다듬기만 Haiku 사용
```

#### B. 이미지 생성 확대
```python
# 기존: 3개 이미지 (썸네일, 증명, 차트)
# 확장: 5-7개 이미지 생성
#   - 썸네일 2종
#   - 본문 이미지 3-4개
#   - 인포그래픽
```

#### C. 멀티모달 분석 활용
```python
# Gemini의 멀티모달 능력 활용
# - 생성된 이미지 품질 자동 검증
# - 이미지-텍스트 정합성 검사
# - 시각적 매력도 점수 계산
```

---

## 🔧 실전 적용 방법

### 기본 사용 (Haiku + 캐싱)
```python
# main.py 실행 시 자동으로 Haiku 사용
python main.py --naver-id YOUR_ID --once
```

### 고품질 필요 시 (Sonnet 사용)
```python
# main.py에서 수동 변경
content_data = self.content_agent.generate_post(
    research_data=research_data,
    model="sonnet",  # 특별히 고품질 필요 시만
    use_cache=False  # 캐시 비활성화
)
```

### Gemini 중심 전략
```python
# 1단계: Gemini로 초안 생성 (무료 - 크레딧)
# 2단계: Haiku로 최소 편집 ($0.01)
# 3단계: Gemini로 이미지 5개 생성 (무료 - 크레딧)
```

---

## 📈 예상 비용 시뮬레이션

### 시나리오 1: 하루 3회 포스팅 (Haiku + 캐싱)

```
일일 비용:
- Research (Perplexity): $0.015
- Content (Haiku + Cache): $0.12
- Visual (Gemini): $0.00 (크레딧)
- QA (Haiku): $0.03
───────────────────────
합계: $0.165/일 = $4.95/월

Gemini 크레딧 소진 후:
- Visual (Gemini): $1.50/일
- 합계: $1.665/일 = $50/월
```

### 시나리오 2: 하루 5회 포스팅 (적극 활용)

```
일일 비용:
- Research: $0.025
- Content (Haiku): $0.20
- Visual (Gemini): $0.00 (크레딧)
- QA: $0.05
───────────────────────
합계: $0.275/일 = $8.25/월

Gemini 크레딧 소진 후:
- 합계: $2.775/일 = $83/월
```

### Gemini 크레딧 지속 기간

```
크레딧: 140만원
일일 사용 (5회 포스팅): $2.50
───────────────────────
지속 기간: 약 15-18개월!
```

---

## 🎁 추가 최적화 팁

### 1. 캐시 활용 극대화
```bash
# 캐시 정리 (만료된 것만)
python -c "from utils.cost_optimizer import cost_optimizer; cost_optimizer.cleanup_expired_cache()"
```

### 2. 비용 추적
```bash
# 월간 비용 확인
python -c "from utils.cost_optimizer import cost_tracker; print(cost_tracker.get_total_cost(30))"
```

### 3. 모델 선택 가이드

| 상황 | 권장 모델 | 이유 |
|------|-----------|------|
| 일반 포스팅 | **Haiku** | 비용 최적, 품질 충분 |
| 중요 발표 | Sonnet | 최고 품질 필요 |
| 이미지 생성 | **Gemini** | 크레딧 활용 |
| 간단한 편집 | Haiku | 최저 비용 |

---

## 🔍 비용 모니터링

### 실시간 비용 확인
```python
# main.py 실행 후 로그 확인
tail -f data/logs/cost_log.json
```

### 주간 리포트
```python
from utils.cost_optimizer import cost_tracker

# 지난 7일 비용
report = cost_tracker.get_total_cost(days=7)
print(f"주간 총 비용: ${report['total']:.2f}")
```

---

## ✅ 체크리스트

최적화 적용 확인:

- [x] content_agent.py에 Haiku 모델 추가
- [x] Prompt Caching 활성화
- [x] 응답 캐싱 시스템 구현
- [x] 비용 추적 시스템 구현
- [x] Gemini 크레딧 최대 활용 전략 수립

---

## 🎯 최종 권장 설정

### .env 파일 설정
```bash
# 비용 최적화 모드
USE_COST_OPTIMIZATION=True
DEFAULT_MODEL=haiku
ENABLE_CACHING=True
CACHE_TTL_HOURS=24

# Gemini 적극 활용
GEMINI_IMAGES_PER_POST=5  # 기본 3개 → 5개
GEMINI_USE_FOR_DRAFT=True  # 초안 생성에도 사용
```

### 실행
```bash
# 최적화 모드로 실행
python main.py --naver-id YOUR_ID --once

# 크레딧 확인
python -c "from utils.cost_optimizer import cost_tracker; cost_tracker.get_total_cost(30)"
```

---

## 💡 결론

### 비용 절감 효과

| 항목 | 기존 | 최적화 후 | 절감률 |
|------|------|-----------|--------|
| Claude | $50-100 | $8-15 | **85%** |
| Perplexity | $20 | $10 | **50%** |
| Gemini | $30-60 | $0* | **100%*** |
| **총계** | **$100-180** | **$18-25*** | **80-90%** |

*Gemini 크레딧 소진 전 기준

### 실질 비용 (Gemini 크레딧 고려)
- **첫 15-18개월**: 월 $18-25 (Gemini 무료)
- **크레딧 소진 후**: 월 $68-105 (여전히 기존 대비 30-40% 저렴)

**축하합니다! 비용을 80% 이상 절감하면서도 품질은 유지합니다!** 🎉
