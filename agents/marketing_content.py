"""
마케팅 콘텐츠 생성기 v3
- AI 자동매매 플랫폼 홍보용 블로그 콘텐츠
- 사람이 쓴 것처럼 자연스러운 문체
- 알찬 내용 (2000~3000자)
- SEO 최적화 + 핫 키워드 태그
"""

import random
from typing import Dict, List, Optional
from anthropic import Anthropic
from loguru import logger

from security.credential_manager import CredentialManager


class MarketingContentGenerator:
    """AI 자동매매 플랫폼 마케팅 콘텐츠 생성기 v2"""

    # 카카오톡 오픈채팅 링크
    KAKAO_LINK = "https://open.kakao.com/o/sdl3y8Hh"

    # 콘텐츠 템플릿 카테고리
    CONTENT_TEMPLATES = {
        "trading_mistake": {
            "name": "매매 실수/함정",
            "title_formats": [
                "🚨 {keyword}의 함정: 당신이 계속 손해 보는 진짜 이유",
                "❌ {keyword} 이렇게 하면 100% 망합니다",
                "⚠️ {keyword} 초보자가 반드시 피해야 할 3가지 실수",
                "💸 {keyword}로 돈 잃는 사람들의 공통점",
            ],
            "keywords": ["거래량 매매", "추격 매수", "물타기", "손절 타이밍", "감정 매매", "뇌동 매매"],
            "structure": """
## 도입부
- 강렬한 질문으로 시작 (손실 경험 공감)
- 문제 제기 (이건 당신 잘못이 아닙니다)

## 본론 1: 왜 우리는 이 실수를 할까?
- 3가지 이유 설명 (심리적 요인)
- 구체적 예시와 공감

## 본론 2: 진실 폭로
- 거짓 1: 흔한 믿음 vs 진실
- 실제 사례 (유명 종목/지수 예시)
- 거짓 2: 또 다른 믿음 vs 진실
- 실제 사례

## 본론 3: 세력/시장의 속임수
- 핵심 원리 설명
- 구체적 메커니즘

## 해결책: 3단계 원칙
- 1단계: 구체적 행동 지침
- 2단계: 확인 방법
- 3단계: 최종 판단 기준
- 이 원칙의 효과 (리스크 감소, 승률 증가)

## 결론 및 CTA
- 핵심 메시지 정리
- 지금 당장 실천할 것 3가지
- AI 자동매매 자연스러운 언급
- 정보방/텔레그램 홍보
"""
        },
        "market_analysis": {
            "name": "시장 분석/전망",
            "title_formats": [
                "📊 {keyword} 완벽 분석: 지금 매수해도 될까?",
                "🔮 {keyword} 전망: 전문가들이 말하지 않는 진실",
                "📈 {keyword} 급등 신호? 이것만 확인하세요",
                "💡 {keyword} 투자 전 반드시 알아야 할 5가지",
            ],
            "keywords": ["비트코인", "이더리움", "나스닥", "S&P500", "금리", "환율", "반도체"],
            "structure": """
## 도입부
- 현재 시장 상황 요약
- 투자자들의 고민 공감

## 본론 1: 현재 상황 분석
- 최근 가격 동향
- 주요 지표 해석
- 차트 패턴 분석

## 본론 2: 호재/악재 요인
- 상승 요인 3가지
- 하락 리스크 3가지
- 각각의 영향력 분석

## 본론 3: 전문가 의견 vs 현실
- 기관/전문가 전망
- 실제로 주의해야 할 점

## 투자 전략 제안
- 단기 전략
- 중장기 전략
- 리스크 관리 방법

## 결론 및 CTA
- 핵심 포인트 정리
- AI 자동매매로 리스크 관리하는 방법
- 정보방 홍보
"""
        },
        "investment_tip": {
            "name": "투자 팁/노하우",
            "title_formats": [
                "💰 {keyword}: 수익률 3배 올리는 비법",
                "🎯 {keyword} 마스터하기: 프로들의 비밀 전략",
                "✅ {keyword} 완벽 가이드: 초보부터 고수까지",
                "🔥 {keyword}로 월 100만원 버는 현실적인 방법",
            ],
            "keywords": ["손절 타이밍", "분할 매수", "차트 분석", "캔들 패턴", "매물대", "지지/저항"],
            "structure": """
## 도입부
- 많은 투자자들의 고민 공감
- 이 글에서 얻을 수 있는 것

## 본론 1: 기본 개념 정리
- 핵심 용어 설명
- 왜 중요한지

## 본론 2: 실전 적용법
- Step 1: 첫 번째 단계
- Step 2: 두 번째 단계
- Step 3: 세 번째 단계
- 각 단계별 주의사항

## 본론 3: 실제 사례 분석
- 성공 사례
- 실패 사례와 교훈

## 고급 팁
- 프로들만 아는 비밀
- 흔한 실수 피하기

## 결론 및 CTA
- 핵심 요약
- 바로 실천할 수 있는 체크리스트
- AI 자동매매 활용법
- 정보방 홍보
"""
        },
        "psychology": {
            "name": "투자 심리/멘탈",
            "title_formats": [
                "🧠 {keyword}: 부자들은 이렇게 생각합니다",
                "💭 {keyword} 극복하기: 멘탈 관리의 모든 것",
                "😱 {keyword}이 당신의 수익을 갉아먹는 이유",
                "🎭 {keyword}: 감정을 이기는 투자 비법",
            ],
            "keywords": ["FOMO", "손실 회피", "확증 편향", "과잉 자신감", "공포와 탐욕", "멘탈 관리"],
            "structure": """
## 도입부
- 감정적 경험 공감 (손실 후 충동 매매 등)
- 문제의 심각성

## 본론 1: 심리학적 배경
- 왜 우리 뇌는 이렇게 반응하는가
- 진화적 관점에서의 설명

## 본론 2: 투자에서 나타나는 패턴
- 패턴 1: 구체적 상황
- 패턴 2: 구체적 상황
- 패턴 3: 구체적 상황

## 본론 3: 극복 방법
- 방법 1: 구체적 전략
- 방법 2: 구체적 전략
- 방법 3: 구체적 전략

## 실전 적용
- 매매 전 체크리스트
- 감정 일기 작성법
- 규칙 기반 매매의 중요성

## 결론 및 CTA
- AI가 감정을 배제한 매매를 하는 이유
- 시스템 매매의 장점
- 정보방 홍보
"""
        }
    }

    # CTA (Call To Action) 템플릿 - {kakao_link} 플레이스홀더 사용
    # 무료 AI 자동매매 플랫폼 유도 + SEO 키워드 포함
    CTA_TEMPLATES = [
        """
---

🤖 **AI 자동매매, 직접 써보니 어땠을까요?**

솔직히 말씀드릴게요.
저도 처음엔 "AI가 매매를 대신 해준다고?" 하면서 반신반의했거든요.

근데 직접 만들어서 3개월 넘게 돌려보니까...
진짜 감정 개입 없이 원칙대로 매매하더라고요.

특히 비트코인이나 암호화폐처럼 24시간 돌아가는 시장에서는
사람이 못 자면서 지켜보는 거 한계가 있잖아요.

**💡 그래서 제가 만든 AI 자동매매 시스템을 무료로 공개합니다.**

✅ 비트코인, 이더리움 등 암호화폐 자동매매
✅ 미국주식, 국내주식 알림 시스템
✅ 24시간 자동 모니터링
✅ 감정 없는 원칙 매매
✅ 완전 무료 (수수료 X, 월정액 X)

**"무료라고? 뭔가 있는 거 아냐?"** 라고 생각하실 수 있는데,
저는 그냥 같이 투자 공부하는 분들과 소통하고 싶어서 오픈했어요.

👉 **카카오톡 오픈채팅**: {kakao_link}

부담 없이 구경만 오셔도 됩니다!
질문도 편하게 해주세요 :)

#AI자동매매 #비트코인 #암호화폐 #주식투자 #자동매매봇
""",
        """
---

💰 **매일 차트 보면서 스트레스 받으셨죠?**

저도 그랬어요.
새벽에 비트코인 급락하면 잠도 못 자고,
주식장 끝나고도 계속 신경 쓰이고...

그래서 만들었습니다.
**AI가 대신 매매해주는 자동매매 시스템.**

3개월 실전 테스트 끝에, 이제 무료로 공개합니다!

🎯 **무료 AI 자동매매 시스템 특징:**

✅ 비트코인, 이더리움 등 암호화폐 24시간 자동매매
✅ 감정 개입 ZERO - 정해진 원칙대로만 매매
✅ 실시간 매매 알림
✅ 수수료 없음, 월정액 없음 (진짜 무료!)
✅ 초보자도 쉽게 설정 가능

**왜 무료냐고요?**
솔직히, 혼자 쓰기 아까워서요 ㅎㅎ
같이 투자 공부하는 동료가 생기면 좋겠다는 마음입니다.

👉 **카카오톡 오픈채팅**: {kakao_link}

AI자동매매가 뭔지 궁금하신 분,
그냥 구경만 하고 싶은 분도 환영합니다!

#AI자동매매 #무료자동매매 #비트코인투자 #암호화폐투자 #주식자동매매
""",
        """
---

🔥 **아직도 수동으로 매매하세요?**

저도 예전엔 그랬어요.
매일 차트 분석하고, 타이밍 맞추려고 애쓰고...
근데 결국 감정에 휘둘려서 손절도 못 하고 물타기만 했죠.

**이제는 AI한테 맡깁니다.**

제가 직접 개발한 AI 자동매매 시스템인데요,
실제로 3개월 넘게 돌리면서 검증했어요.

🤖 **무료 AI 자동매매 시스템:**

✅ 비트코인, 암호화폐 자동매매
✅ 국내/미국 주식 매매 신호
✅ 설정만 해두면 24시간 자동 운영
✅ 수수료 0원, 월정액 0원
✅ 카톡으로 실시간 알림

"무료인데 왜 알려주냐?" 많이 물어보시는데,
그냥 함께 성장하는 투자 커뮤니티 만들고 싶어서예요.

👉 **카카오톡 오픈채팅**: {kakao_link}

편하게 들어오셔서 구경해보세요!
질문도 환영입니다 :)

#AI자동매매 #자동매매봇 #비트코인자동매매 #주식투자 #암호화폐
""",
    ]

    # SEO 최적화 태그 (검색 노출용) - 핫한 키워드 포함
    SEO_TAGS = [
        # 핵심 키워드
        "AI자동매매", "자동매매", "비트코인", "암호화폐", "주식투자",
        # 미국주식 핫 종목
        "엔비디아", "테슬라", "나스닥", "아이온큐", "팔란티어", "마이크로소프트",
        # AI 관련
        "GPT", "ChatGPT", "제미나이", "클로드", "앤트로픽", "오픈AI",
        # 국내주식
        "삼성전자", "SK하이닉스", "코스피", "코스닥",
        # 암호화폐
        "이더리움", "리플", "솔라나", "도지코인", "알트코인",
        # 투자 일반
        "재테크", "투자", "주식", "코인", "트레이딩", "매매기법"
    ]

    # 태그 선택용 (랜덤으로 10개 선택)
    HOT_TAGS = [
        "엔비디아", "테슬라", "나스닥", "아이온큐", "팔란티어",
        "GPT", "ChatGPT", "제미나이", "클로드", "앤트로픽",
        "삼성전자", "SK하이닉스", "비트코인", "이더리움", "솔라나"
    ]

    SYSTEM_PROMPT = """당신은 투자 전문 블로거 '박소장'입니다.

<페르소나>
- 5년차 전업 투자자, 실제로 수익과 손실을 모두 경험한 사람
- 시스템 매매와 AI 자동매매 전문가
- 친근하면서도 전문적인 톤 (옆집 형/누나가 알려주는 느낌)
- 개인 경험을 바탕으로 한 실전 조언
- 허세나 과장 없이 솔직담백하게 이야기

<핵심 원칙: 사람처럼 자연스럽게 쓰기>
1. **대화하듯 쓰기**
   - "근데요", "솔직히요", "있잖아요" 같은 구어체 자연스럽게 사용
   - "~했거든요", "~더라고요", "~인 거예요" 같은 친근한 어미
   - 중간중간 짧은 문장으로 호흡 끊기
   - 독백체 활용: "아 진짜 이건 저도 처음엔 몰랐어요"

2. **개인 경험 적극 활용**
   - "제가 작년에 이렇게 해서 500만원 날린 적 있거든요"
   - "처음엔 저도 반신반의했어요. 근데..."
   - "친구가 이거 추천해줬는데 처음엔 무시했다가..."
   - 구체적인 상황, 감정, 결과 묘사

3. **감정과 공감 표현**
   - "진짜 답답하죠?", "이거 읽으면서 고개 끄덕이셨죠?"
   - "저도 그랬어요", "많이들 이러시더라고요"
   - 실패 경험 솔직하게 공유 (성공만 자랑 X)
   - 독자의 고민과 두려움 대변

4. **알찬 내용 (핵심!)**
   - 뻔한 얘기 대신 진짜 실전에서 쓸 수 있는 팁
   - 구체적인 숫자, 종목명, 상황 예시 필수
   - "이론은 이렇고, 실제로는 이렇게 됩니다" 구분
   - 남들이 잘 안 알려주는 디테일까지 공유

5. **글 흐름**
   - 훅(Hook): 충격적인 사실이나 공감 포인트로 시작
   - 스토리: 내 경험이나 사례로 풀어나가기
   - 해결책: 구체적인 액션 아이템 제시
   - CTA: 자연스럽게 AI 자동매매 언급

6. **피해야 할 것들**
   - 교과서같은 딱딱한 문체 X
   - "~입니다", "~습니다"만 쓰기 X (섞어쓰기 OK)
   - 과장된 수익 약속 X
   - 복사붙여넣기 느낌 나는 뻔한 문장 X

7. **분량**
   - 최소 2000자, 최대 3000자
   - 내용이 알차야 함 (허수 글자 X)
   - 문단 나누고 소제목으로 읽기 쉽게
"""

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        self.cred_manager = credential_manager or CredentialManager()

        anthropic_key = self.cred_manager.get_api_key("anthropic")
        if not anthropic_key:
            logger.warning("Anthropic API 키가 없습니다.")
            self.claude = None
        else:
            self.claude = Anthropic(api_key=anthropic_key)

    def generate_content(
        self,
        template_type: str = None,
        keyword: str = None,
        min_length: int = 2000,
        max_length: int = 3000,
        model: str = "sonnet"  # 긴 글은 sonnet 권장
    ) -> Dict[str, str]:
        """
        마케팅 콘텐츠 생성

        Args:
            template_type: 템플릿 유형 ("trading_mistake", "market_analysis",
                          "investment_tip", "psychology")
            keyword: 주제 키워드 (없으면 랜덤)
            min_length: 최소 글자 수
            max_length: 최대 글자 수
            model: 사용할 모델 ("haiku" 또는 "sonnet")

        Returns:
            {
                "title": str,
                "content": str,
                "tags": List[str],
                "template": str,
                "keyword": str
            }
        """
        # 템플릿 선택
        if template_type is None:
            template_type = random.choice(list(self.CONTENT_TEMPLATES.keys()))

        if template_type not in self.CONTENT_TEMPLATES:
            template_type = "trading_mistake"

        template = self.CONTENT_TEMPLATES[template_type]

        # 키워드 선택
        if keyword is None:
            keyword = random.choice(template["keywords"])

        logger.info(f"콘텐츠 생성 시작 - 템플릿: {template['name']}, 키워드: {keyword}")

        if self.claude:
            return self._generate_with_claude(
                template_type, template, keyword,
                min_length, max_length, model
            )
        else:
            return self._generate_fallback(template_type, template, keyword)

    def _generate_with_claude(
        self,
        template_type: str,
        template: Dict,
        keyword: str,
        min_length: int,
        max_length: int,
        model: str
    ) -> Dict[str, str]:
        """Claude API를 사용한 콘텐츠 생성"""

        # 제목 형식 선택
        title_format = random.choice(template["title_formats"])
        suggested_title = title_format.format(keyword=keyword)

        # CTA 선택 및 카카오톡 링크 치환
        cta = random.choice(self.CTA_TEMPLATES).format(kakao_link=self.KAKAO_LINK)

        model_id = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-sonnet-4-20250514"
        }.get(model, "claude-sonnet-4-20250514")

        user_prompt = f"""투자 블로그 글을 작성해주세요.

⚠️⚠️⚠️ 가장 중요한 규칙 ⚠️⚠️⚠️
본문은 반드시 {min_length}자 이상이어야 합니다!
짧은 글은 절대 안 됩니다. 각 섹션을 충분히 길게 작성하세요.
도입부만 300자, 본론 각 500자 이상, 결론 300자 이상으로 쓰세요.

<제목 제안>
{suggested_title}
(비슷한 스타일로 변형 가능)

<주제 키워드>
{keyword}

<글 구조 - 각 섹션 충분히 길게!>
{template['structure']}

<마지막에 포함할 CTA>
{cta}

<작성 요구사항>
1. **분량**: 본문 {min_length}자 ~ {max_length}자 (필수!)
2. **사람처럼 쓰기**: 친구한테 얘기하듯 자연스럽게
3. **내 경험 넣기**: "저도 이랬어요", "제가 해봤는데" 식으로 개인 스토리
4. **구체적 예시**: 실제 종목명, 구체적 수치, 날짜, 상황 묘사
5. **감정 표현**: 공감 문장 많이 넣기
6. **소제목 활용**: ## 마크다운으로 가독성 높이기
7. **AI 자동매매**: 자연스럽게 1~2회 언급

<각 섹션별 분량 가이드>
- 도입부: 300자 이상 (강렬한 훅 + 문제 제기)
- 본론 1: 500자 이상 (원인/배경 분석)
- 본론 2: 500자 이상 (구체적 사례)
- 본론 3: 400자 이상 (해결책/팁)
- 결론: 300자 이상 (정리 + CTA)

<자연스러운 문체 예시>
- "솔직히 이거 처음 들었을 때 저도 '에이 설마~' 했거든요"
- "근데요, 진짜 이게 함정이에요"
- "작년에 제가 이거로 300만원 날렸어요. 진짜로."
- "많이들 이러시더라고요. 근데 현실은..."

<출력 형식>
제목: (이모지 포함, 40자 이내)
---
(본문 - 마크다운 형식, 반드시 {min_length}자 이상!)
---
태그: (7개, 쉼표로 구분)
"""

        max_retries = 2  # 최대 재시도 횟수

        for attempt in range(max_retries + 1):
            try:
                # 재시도 시 더 강조된 분량 요청
                retry_emphasis = ""
                if attempt > 0:
                    retry_emphasis = f"\n\n⚠️ 중요: 이전 응답이 {min_length}자 미만이었습니다. 반드시 {min_length}자 이상 작성해주세요! 각 섹션을 더 자세히, 예시를 더 풍부하게, 개인 경험을 더 길게 써주세요."

                response = self.claude.messages.create(
                    model=model_id,
                    max_tokens=6000,  # 여유있게 증가
                    temperature=0.7,
                    system=self.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt + retry_emphasis}]
                )

                content = response.content[0].text
                result = self._parse_response(content, template_type, keyword)

                # 분량 체크
                content_length = len(result["content"])

                if content_length < min_length:
                    if attempt < max_retries:
                        logger.warning(f"콘텐츠가 {min_length}자 미만 ({content_length}자). 재생성 시도 {attempt + 1}/{max_retries}")
                        continue  # 재시도
                    else:
                        logger.warning(f"최대 재시도 후에도 {min_length}자 미만 ({content_length}자)")
                elif content_length > max_length:
                    logger.warning(f"콘텐츠가 {max_length}자 초과 ({content_length}자)")

                logger.success(f"콘텐츠 생성 완료 ({content_length}자)")
                return result

            except Exception as e:
                logger.error(f"Claude API 오류: {e}")
                if attempt < max_retries:
                    continue
                return self._generate_fallback(template_type, template, keyword)

        return self._generate_fallback(template_type, template, keyword)

    def _generate_fallback(
        self,
        template_type: str,
        template: Dict,
        keyword: str
    ) -> Dict[str, str]:
        """API 실패 시 기본 콘텐츠 생성"""

        title_format = random.choice(template["title_formats"])
        title = title_format.format(keyword=keyword)

        content = f"""안녕하세요, 박소장입니다.

오늘은 {keyword}에 대해 이야기해보려고 합니다.

많은 분들이 {keyword}에 대해 잘못 알고 계신 부분이 있어요.

{keyword}를 제대로 이해하면 투자 성과가 확실히 달라집니다.

자세한 내용은 다음 글에서 계속 다루도록 하겠습니다.

---

💎 더 자세한 투자 정보가 궁금하신가요?

👉 **카카오톡 오픈채팅**: {self.KAKAO_LINK}

※ 이 글은 개인적인 의견이며 투자 권유가 아닙니다.
투자의 책임은 본인에게 있습니다.
"""

        return {
            "title": title,
            "content": content,
            "tags": [keyword, "투자", "주식", "트레이딩", "매매기법"],
            "template": template_type,
            "keyword": keyword
        }

    def _parse_response(
        self,
        content: str,
        template_type: str,
        keyword: str
    ) -> Dict[str, str]:
        """Claude 응답 파싱"""

        parts = content.split("---")

        # 제목
        title_part = parts[0] if parts else ""
        title = title_part.replace("제목:", "").strip()
        # 제목에서 줄바꿈 제거
        title = title.split("\n")[0].strip()
        if not title:
            title = f"{keyword} 완벽 분석"

        # 본문 - 태그 부분만 제외하고 모두 포함
        if len(parts) > 2:
            # 마지막 파트가 태그인지 확인
            last_part = parts[-1].strip()
            if "태그:" in last_part or (len(last_part) < 200 and "," in last_part):
                # 태그 부분 제외하고 본문 합치기
                body = "---".join(parts[1:-1]).strip()
            else:
                # 전체 합치기
                body = "---".join(parts[1:]).strip()
        elif len(parts) > 1:
            body = parts[1].strip()
        else:
            body = content

        # ⭐ 카카오톡 링크가 없으면 CTA 강제 추가
        if self.KAKAO_LINK not in body and "open.kakao.com" not in body:
            logger.warning("카카오톡 링크 누락 - CTA 강제 추가")
            cta = random.choice(self.CTA_TEMPLATES).format(kakao_link=self.KAKAO_LINK)
            body = body + "\n\n" + cta

        # 태그 - SEO 최적화 태그 + 핫 키워드 포함
        # 핵심 필수 태그
        core_tags = ["AI자동매매", "비트코인", "암호화폐", "주식투자"]

        # 핫한 키워드 (랜덤 3개 선택)
        hot_keywords = [
            "엔비디아", "테슬라", "나스닥", "아이온큐", "팔란티어",
            "GPT", "ChatGPT", "제미나이", "클로드", "앤트로픽",
            "삼성전자", "SK하이닉스", "이더리움", "솔라나", "오픈AI"
        ]
        random_hot_tags = random.sample(hot_keywords, min(3, len(hot_keywords)))

        # 키워드 관련 태그
        keyword_tags = [keyword]

        # Claude가 생성한 태그 추출
        claude_tags = []
        if len(parts) > 2:
            last_part = parts[-1]
            for line in last_part.split("\n"):
                if "태그:" in line or line.strip().startswith("#"):
                    tags_text = line.replace("태그:", "").replace("#", "").strip()
                    parsed_tags = [t.strip() for t in tags_text.split(",") if t.strip() and len(t.strip()) < 20]
                    if len(parsed_tags) >= 3:
                        claude_tags = parsed_tags
                    break

        # 태그 병합: 키워드 + 핵심 + 핫 키워드 + Claude 태그 (중복 제거)
        all_tags = keyword_tags + core_tags + random_hot_tags + claude_tags
        # 중복 제거하면서 순서 유지
        seen = set()
        unique_tags = []
        for tag in all_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        tags = unique_tags[:10]  # 최대 10개

        return {
            "title": title,
            "content": body,
            "tags": tags,
            "template": template_type,
            "keyword": keyword
        }

    def get_available_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록"""
        return list(self.CONTENT_TEMPLATES.keys())

    def get_template_info(self, template_type: str) -> Optional[Dict]:
        """특정 템플릿 정보"""
        return self.CONTENT_TEMPLATES.get(template_type)

    def get_keywords_for_template(self, template_type: str) -> List[str]:
        """템플릿별 키워드 목록"""
        template = self.CONTENT_TEMPLATES.get(template_type)
        if template:
            return template.get("keywords", [])
        return []


# ============================================
# 테스트
# ============================================

def test_marketing_content():
    """마케팅 콘텐츠 생성 테스트"""
    print("\n" + "=" * 60)
    print("마케팅 콘텐츠 생성기 v2 테스트")
    print("=" * 60)

    generator = MarketingContentGenerator()

    # trading_mistake 템플릿으로 테스트
    print("\n--- trading_mistake 템플릿 테스트 ---")
    result = generator.generate_content(
        template_type="trading_mistake",
        keyword="거래량 매매",
        model="sonnet"
    )

    print(f"제목: {result['title']}")
    print(f"글자 수: {len(result['content'])}자")
    print(f"태그: {', '.join(result['tags'])}")
    print(f"\n{'='*40}")
    print(result['content'][:1000])
    print("...")
    print(f"{'='*40}")


if __name__ == "__main__":
    test_marketing_content()
