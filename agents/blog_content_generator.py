"""
블로그 콘텐츠 생성기 v3
- 다양한 주제: 미국주식, 국내주식, 암호화폐, AI, 경제, 핫이슈
- Perplexity 리서치 에이전트 연동 (실시간 데이터)
- 유익한 정보 제공 → 자연스러운 AI 자동매매 유도
- 카카오톡 오픈채팅 링크 필수 포함
"""

import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from anthropic import Anthropic
from loguru import logger

from security.credential_manager import CredentialManager
from agents.research_agent import ResearchAgent


class BlogContentGenerator:
    """다목적 블로그 콘텐츠 생성기"""

    # 카카오톡 오픈채팅 링크
    KAKAO_LINK = "https://open.kakao.com/o/sdl3y8Hh"

    # 주제 카테고리별 키워드
    TOPICS = {
        "us_stock": {
            "name": "미국주식",
            "keywords": [
                "테슬라", "엔비디아", "애플", "마이크로소프트", "아마존",
                "구글", "메타", "나스닥", "S&P500", "다우존스",
                "미국 금리", "연준", "파월", "고용지표", "CPI"
            ],
            "emoji": "🇺🇸"
        },
        "kr_stock": {
            "name": "국내주식",
            "keywords": [
                "삼성전자", "SK하이닉스", "네이버", "카카오", "현대차",
                "코스피", "코스닥", "외국인 매매", "기관 매매", "반도체",
                "2차전지", "바이오", "조선", "방산", "금리"
            ],
            "emoji": "🇰🇷"
        },
        "crypto": {
            "name": "암호화폐",
            "keywords": [
                "비트코인", "이더리움", "리플", "솔라나", "도지코인",
                "알트코인", "김치프리미엄", "반감기", "ETF", "기관투자",
                "업비트", "바이낸스", "채굴", "디파이", "NFT"
            ],
            "emoji": "₿"
        },
        "ai_tech": {
            "name": "AI/기술",
            "keywords": [
                "ChatGPT", "클로드", "생성형AI", "AI반도체", "GPU",
                "자율주행", "로봇", "양자컴퓨터", "메타버스", "빅테크",
                "오픈AI", "AI규제", "AI투자", "AI일자리", "AI혁명"
            ],
            "emoji": "🤖"
        },
        "economy": {
            "name": "경제",
            "keywords": [
                "금리인상", "인플레이션", "환율", "달러", "엔화",
                "유가", "금값", "부동산", "경기침체", "스태그플레이션",
                "중국경제", "일본경제", "유럽경제", "신흥국", "글로벌"
            ],
            "emoji": "💰"
        },
        "hot_issue": {
            "name": "핫이슈",
            "keywords": [
                "트럼프", "미국대선", "중동사태", "러우전쟁", "대만",
                "공급망", "리쇼어링", "탈중국", "K-콘텐츠", "IPO",
                "메가트렌드", "ESG", "그린에너지", "인구절벽", "연금"
            ],
            "emoji": "🔥"
        }
    }

    # 글쓰기 스타일
    WRITING_STYLES = [
        "분석형",      # 데이터와 차트 분석 중심
        "스토리텔링",  # 개인 경험 + 인사이트
        "뉴스해설",    # 뉴스 요약 + 투자 관점
        "전망형",      # 향후 전망 + 대응 전략
        "교육형"       # 개념 설명 + 실전 적용
    ]

    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 투자와 경제 전문 블로거입니다.

<목표>
1. 독자에게 유익한 정보와 인사이트 제공
2. 자연스럽게 AI 기반 투자의 장점 언급
3. 마지막에 카카오톡 오픈채팅으로 유도

<글쓰기 원칙>
1. **가독성 우선**
   - 짧은 문단 (3-4줄)
   - 소제목, 불릿 포인트 활용
   - 이모지 적절히 사용 (과하지 않게)

2. **신뢰감 구축**
   - 구체적인 수치와 데이터 인용
   - "~라고 합니다", "~로 알려졌습니다" 등 객관적 표현
   - 출처 언급 (예: 연준, 블룸버그, 한국은행)

3. **공감과 연결**
   - "많은 분들이 궁금해하시는~"
   - "저도 처음엔~" 식의 공감 유도
   - 독자의 고민을 대변

4. **자연스러운 유도**
   - 글 중간: "이런 복잡한 시장에서 감정을 배제한 투자가 중요해요"
   - 글 중간: "저는 개인적으로 시스템 매매를 병행하고 있는데~"
   - 마지막: AI 자동매매 언급 + 카카오톡 안내

5. **분량**
   - 1500~2500자 (충실한 내용)
   - 도입-본론-결론 구조

<금지사항>
- "대박", "확실한 수익", "무조건" 등 과장 표현
- 직접적인 종목 추천 (매수/매도 지시)
- 투자 보장 발언
"""

    def __init__(
        self,
        kakao_link: Optional[str] = None,
        credential_manager: Optional[CredentialManager] = None
    ):
        """
        Args:
            kakao_link: 카카오톡 오픈채팅 링크
            credential_manager: 자격증명 관리자
        """
        self.kakao_link = kakao_link or self.KAKAO_LINK
        self.cred_manager = credential_manager or CredentialManager()

        anthropic_key = self.cred_manager.get_api_key("anthropic")
        if not anthropic_key:
            logger.warning("Anthropic API 키가 없습니다.")
            self.claude = None
        else:
            self.claude = Anthropic(api_key=anthropic_key)

        # Perplexity 리서치 에이전트
        self.research_agent = ResearchAgent(self.cred_manager)

    def generate(
        self,
        topic_category: Optional[str] = None,
        keyword: Optional[str] = None,
        style: Optional[str] = None,
        model: str = "haiku"
    ) -> Dict[str, str]:
        """
        블로그 콘텐츠 생성

        Args:
            topic_category: 주제 카테고리 (us_stock, kr_stock, crypto, ai_tech, economy, hot_issue)
            keyword: 특정 키워드 (없으면 랜덤)
            style: 글쓰기 스타일 (없으면 랜덤)
            model: 모델 선택 (haiku/sonnet)

        Returns:
            {
                "title": str,
                "content": str,
                "tags": List[str],
                "category": str,
                "keyword": str,
                "style": str,
                "image_prompt": str
            }
        """
        # 랜덤 선택
        if not topic_category:
            topic_category = random.choice(list(self.TOPICS.keys()))

        topic = self.TOPICS.get(topic_category, self.TOPICS["economy"])

        if not keyword:
            keyword = random.choice(topic["keywords"])

        if not style:
            style = random.choice(self.WRITING_STYLES)

        logger.info(f"콘텐츠 생성: {topic['name']} / {keyword} / {style}")

        if not self.claude:
            return self._generate_fallback(topic_category, keyword, topic)

        return self._generate_with_claude(topic_category, keyword, topic, style, model)

    def _generate_with_claude(
        self,
        category: str,
        keyword: str,
        topic: Dict,
        style: str,
        model: str
    ) -> Dict[str, str]:
        """Claude로 콘텐츠 생성"""

        model_id = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-sonnet-4-20250514"
        }.get(model, "claude-3-5-haiku-20241022")

        # CTA (Call To Action) - 구분자 없이 본문에 자연스럽게 이어지도록
        cta_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 **더 깊은 이야기가 궁금하시다면?**

저는 요즘 AI 기반 자동매매 시스템을 활용해서 투자하고 있어요.
감정에 휘둘리지 않고, 24시간 시장을 모니터링하면서 기회를 포착하는 게 장점이더라고요.

물론 모든 투자에는 리스크가 있지만,
시스템 매매가 제 투자 스타일에는 잘 맞는 것 같습니다.

관심 있으신 분들은 편하게 카카오톡으로 연락주세요!
실시간으로 시장 이야기도 나누고, AI 자동매매 경험도 공유드릴게요 😊

👉 **카카오톡 오픈채팅**: {self.kakao_link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **투자 유의사항**
본 글은 정보 제공 목적이며 투자 권유가 아닙니다.
투자 판단은 본인의 책임이며, 손실 가능성을 항상 인지하세요.
"""

        user_prompt = f"""다음 조건으로 블로그 글을 작성해주세요:

<주제>
카테고리: {topic['name']} {topic['emoji']}
키워드: {keyword}
스타일: {style}

<글쓰기 가이드>
- **{style}** 스타일로 작성
- 분량: 1500~2500자
- {keyword}에 대한 최신 동향과 투자 관점 분석
- 구체적인 수치나 사례 포함
- 독자가 실제로 활용할 수 있는 인사이트 제공

<구조>
1. 도입 (관심 끌기 + 주제 소개)
2. 본론 1 (핵심 분석/정보)
3. 본론 2 (투자 관점/시사점)
4. 결론 (요약 + 아래 CTA 포함)

<출력 형식>
제목: (이모지 1개 + 40자 이내, 클릭 유도형)
---
(본문 내용)

{cta_section}
---
태그: (7개, 쉼표 구분)
---
이미지프롬프트: (영어, 이 글에 어울리는 썸네일 이미지 설명)

**중요**: 위 CTA 섹션(카카오톡 링크 포함)을 본문 마지막에 반드시 그대로 포함해야 합니다!
"""

        try:
            response = self.claude.messages.create(
                model=model_id,
                max_tokens=4000,
                temperature=0.7,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            content = response.content[0].text
            result = self._parse_response(content, category, keyword, style, topic)

            logger.success(f"콘텐츠 생성 완료: {len(result['content'])}자")
            return result

        except Exception as e:
            logger.error(f"Claude API 오류: {e}")
            return self._generate_fallback(category, keyword, topic)

    def _parse_response(
        self,
        content: str,
        category: str,
        keyword: str,
        style: str,
        topic: Dict
    ) -> Dict[str, str]:
        """Claude 응답 파싱"""
        import re

        # \n---\n 패턴으로 정확하게 분리 (CTA 내부의 ━━━ 구분자는 유지)
        parts = re.split(r'\n---\n', content)

        # 제목 추출
        title_part = parts[0] if parts else ""
        title = title_part.replace("제목:", "").strip()
        title = title.split("\n")[0].strip()
        if not title:
            title = f"{topic['emoji']} {keyword} 분석"

        # 본문 추출 (태그/이미지프롬프트 섹션 제외)
        body = ""
        tags_text = ""
        image_prompt_text = ""

        if len(parts) > 1:
            for i, part in enumerate(parts[1:], 1):
                part_stripped = part.strip()
                if part_stripped.startswith("태그:"):
                    tags_text = part_stripped.replace("태그:", "").strip()
                elif "이미지프롬프트:" in part_stripped or "이미지 프롬프트:" in part_stripped:
                    image_prompt_text = part_stripped.replace("이미지프롬프트:", "").replace("이미지 프롬프트:", "").strip()
                else:
                    # 본문에 추가
                    if body:
                        body += "\n\n" + part_stripped
                    else:
                        body = part_stripped

        if not body:
            body = content

        # 본문에서 마지막에 남아있는 태그/이미지프롬프트 라인 제거
        body_lines = body.split("\n")
        cleaned_lines = []
        for line in body_lines:
            line_stripped = line.strip()
            if line_stripped.startswith("태그:"):
                tags_text = line_stripped.replace("태그:", "").strip()
            elif line_stripped.startswith("이미지프롬프트:") or line_stripped.startswith("이미지 프롬프트:"):
                image_prompt_text = line_stripped.replace("이미지프롬프트:", "").replace("이미지 프롬프트:", "").strip()
            else:
                cleaned_lines.append(line)

        body = "\n".join(cleaned_lines).strip()

        # 태그 파싱
        default_tags = [keyword, topic["name"], "투자", "재테크", "경제", "AI자동매매", "주식"]
        if tags_text:
            parsed = [t.strip() for t in tags_text.split(",") if t.strip()]
            tags = parsed[:10] if len(parsed) >= 3 else default_tags
        else:
            tags = default_tags

        # 이미지 프롬프트
        if image_prompt_text:
            image_prompt = image_prompt_text
        else:
            image_prompt = f"Professional financial blog thumbnail about {keyword}, {topic['name']}, modern design, no text"

        return {
            "title": title,
            "content": body,
            "tags": tags,
            "category": category,
            "keyword": keyword,
            "style": style,
            "image_prompt": image_prompt
        }

    def _generate_fallback(
        self,
        category: str,
        keyword: str,
        topic: Dict
    ) -> Dict[str, str]:
        """폴백 콘텐츠"""

        title = f"{topic['emoji']} {keyword}, 지금 주목해야 하는 이유"

        content = f"""안녕하세요, 오늘은 {keyword}에 대해 이야기해보려고 합니다.

## {keyword}의 현재 상황

최근 {topic['name']} 시장에서 {keyword}가 주목받고 있습니다.
많은 투자자분들이 관심을 가지고 계시죠.

## 투자 관점에서 본 시사점

변동성이 큰 시장에서는 감정적 대응보다
체계적인 시스템이 중요합니다.

## 마무리

저는 개인적으로 AI 자동매매 시스템을 활용하고 있어요.
관심 있으신 분은 카카오톡으로 연락주세요!

👉 카카오톡: {self.kakao_link}

---
※ 본 글은 정보 제공 목적이며 투자 권유가 아닙니다.
"""

        return {
            "title": title,
            "content": content,
            "tags": [keyword, topic["name"], "투자", "재테크"],
            "category": category,
            "keyword": keyword,
            "style": "기본",
            "image_prompt": f"Financial concept about {keyword}, professional illustration"
        }

    async def generate_with_research(
        self,
        topic_category: Optional[str] = None,
        style: Optional[str] = None,
        model: str = "haiku"
    ) -> Dict[str, Any]:
        """
        Perplexity 실시간 데이터를 활용한 콘텐츠 생성

        Args:
            topic_category: 주제 카테고리
            style: 글쓰기 스타일
            model: Claude 모델

        Returns:
            콘텐츠 + 리서치 데이터
        """
        # 카테고리 선택
        if not topic_category:
            topic_category = random.choice(list(self.TOPICS.keys()))

        topic = self.TOPICS.get(topic_category, self.TOPICS["economy"])

        if not style:
            style = random.choice(self.WRITING_STYLES)

        logger.info(f"리서치 기반 콘텐츠 생성: {topic['name']} / {style}")

        # 1. Perplexity로 실시간 리서치
        research_data = await self.research_agent.search_topic(topic_category)

        # 2. 리서치 데이터 기반 콘텐츠 생성
        result = self._generate_with_research_data(
            category=topic_category,
            topic=topic,
            style=style,
            research=research_data,
            model=model
        )

        # 리서치 데이터 첨부
        result["research"] = research_data

        return result

    def _generate_with_research_data(
        self,
        category: str,
        topic: Dict,
        style: str,
        research: Dict[str, Any],
        model: str
    ) -> Dict[str, str]:
        """리서치 데이터 기반으로 Claude 콘텐츠 생성"""

        if not self.claude:
            return self._generate_fallback(category, research.get("topic", "투자"), topic)

        model_id = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-sonnet-4-20250514"
        }.get(model, "claude-3-5-haiku-20241022")

        # 리서치 데이터 포맷팅
        key_points_text = "\n".join([f"  - {p}" for p in research.get("key_points", [])])
        market_data = research.get("market_data", {})

        research_context = f"""
## 오늘의 리서치 데이터 (Perplexity 실시간 수집)

**핵심 주제**: {research.get("topic", "N/A")}

**상세 요약**:
{research.get("summary", "데이터 없음")}

**핵심 포인트**:
{key_points_text}

**시장 데이터**:
- 지수 동향: {market_data.get("indices", "N/A")}
- 주목 종목: {market_data.get("notable_stocks", "N/A")}
- 트렌드: {market_data.get("trend", "N/A")}

**투자 관점**:
{research.get("investment_angle", "N/A")}

**시장 감성**: {research.get("sentiment", "neutral")} ({research.get("sentiment_score", 0)})
"""

        # CTA - 구분자 없이 본문에 자연스럽게 이어지도록
        cta_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 **더 깊은 이야기가 궁금하시다면?**

저는 요즘 AI 기반 자동매매 시스템을 활용해서 투자하고 있어요.
감정에 휘둘리지 않고, 24시간 시장을 모니터링하면서 기회를 포착하는 게 장점이더라고요.

물론 모든 투자에는 리스크가 있지만,
시스템 매매가 제 투자 스타일에는 잘 맞는 것 같습니다.

관심 있으신 분들은 편하게 카카오톡으로 연락주세요!
실시간으로 시장 이야기도 나누고, AI 자동매매 경험도 공유드릴게요 😊

👉 **카카오톡 오픈채팅**: {self.kakao_link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **투자 유의사항**
본 글은 정보 제공 목적이며 투자 권유가 아닙니다.
투자 판단은 본인의 책임이며, 손실 가능성을 항상 인지하세요.
"""

        user_prompt = f"""다음 리서치 데이터를 바탕으로 블로그 글을 작성해주세요:

{research_context}

<작성 조건>
카테고리: {topic['name']} {topic['emoji']}
스타일: {style}
분량: 1500~2500자

<작성 가이드>
1. 위 리서치 데이터의 **구체적인 수치와 정보**를 적극 활용
2. 독자가 "오늘 무슨 일이 있었는지" 한눈에 파악할 수 있게
3. {style} 스타일로 작성
4. 자연스럽게 AI 투자/자동매매의 필요성 언급
5. 마지막에 아래 CTA 반드시 포함

<출력 형식>
제목: (이모지 1개 + 40자 이내, 오늘 날짜/이슈 반영)
---
(본문 내용)

{cta_section}
---
태그: (7개, 쉼표 구분)
---
이미지프롬프트: (영어, 이 글에 어울리는 썸네일 이미지 설명)

**중요**: 위 CTA 섹션(카카오톡 링크 포함)을 본문 마지막에 반드시 그대로 포함해야 합니다!
"""

        try:
            response = self.claude.messages.create(
                model=model_id,
                max_tokens=4000,
                temperature=0.7,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            content = response.content[0].text
            keyword = research.get("topic", topic["keywords"][0])[:20]
            result = self._parse_response(content, category, keyword, style, topic)

            logger.success(f"리서치 기반 콘텐츠 생성 완료: {len(result['content'])}자")
            return result

        except Exception as e:
            logger.error(f"Claude API 오류: {e}")
            return self._generate_fallback(category, research.get("topic", "투자"), topic)

    def get_categories(self) -> List[str]:
        """사용 가능한 카테고리 목록"""
        return list(self.TOPICS.keys())

    def get_keywords(self, category: str) -> List[str]:
        """카테고리별 키워드 목록"""
        topic = self.TOPICS.get(category)
        return topic["keywords"] if topic else []

    def set_kakao_link(self, link: str):
        """카카오톡 링크 설정"""
        self.kakao_link = link
        logger.info(f"카카오톡 링크 설정: {link}")


# ============================================
# 테스트
# ============================================

async def test_blog_content_with_research():
    """Perplexity 리서치 연동 테스트"""
    print("\n" + "=" * 60)
    print("📝 블로그 콘텐츠 생성기 v3 + Perplexity 테스트")
    print("=" * 60)

    generator = BlogContentGenerator()

    # 랜덤 주제로 리서치 기반 생성
    result = await generator.generate_with_research(model="haiku")

    print(f"\n📌 카테고리: {result['category']}")
    print(f"🔑 키워드: {result['keyword']}")
    print(f"✍️ 스타일: {result['style']}")

    # 리서치 데이터 출력
    research = result.get("research", {})
    print(f"\n🔍 리서치 주제: {research.get('topic', 'N/A')}")
    print(f"📊 시장 감성: {research.get('sentiment', 'N/A')} ({research.get('sentiment_score', 0)})")

    print(f"\n📰 제목: {result['title']}")
    print(f"📊 글자 수: {len(result['content'])}자")
    print(f"🏷️ 태그: {', '.join(result['tags'][:5])}...")
    print(f"\n🖼️ 이미지 프롬프트:\n   {result['image_prompt'][:100]}...")
    print(f"\n{'─' * 60}")
    print(result['content'][:1500])
    print("...")
    print(f"{'─' * 60}")

    # 카카오톡 링크 포함 확인
    if "kakao" in result['content'].lower() or "카카오" in result['content']:
        print("✅ 카카오톡 링크 포함됨")
    else:
        print("⚠️ 카카오톡 링크 없음!")

    return result


def test_blog_content():
    """블로그 콘텐츠 생성 테스트 (기본)"""
    print("\n" + "=" * 60)
    print("📝 블로그 콘텐츠 생성기 v3 테스트 (기본)")
    print("=" * 60)

    generator = BlogContentGenerator()

    # 랜덤 주제로 테스트
    result = generator.generate(model="haiku")

    print(f"\n📌 카테고리: {result['category']}")
    print(f"🔑 키워드: {result['keyword']}")
    print(f"✍️ 스타일: {result['style']}")
    print(f"\n📰 제목: {result['title']}")
    print(f"📊 글자 수: {len(result['content'])}자")
    print(f"🏷️ 태그: {', '.join(result['tags'][:5])}...")
    print(f"\n🖼️ 이미지 프롬프트:\n   {result['image_prompt'][:100]}...")
    print(f"\n{'─' * 60}")
    print(result['content'][:1000])
    print("...")
    print(f"{'─' * 60}")

    # 카카오톡 링크 포함 확인
    if "kakao" in result['content'].lower() or "카카오" in result['content']:
        print("✅ 카카오톡 링크 포함됨")
    else:
        print("⚠️ 카카오톡 링크 없음!")


if __name__ == "__main__":
    # Perplexity 연동 테스트 (권장)
    asyncio.run(test_blog_content_with_research())
