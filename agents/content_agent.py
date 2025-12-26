"""
Content Synthesizer Agent
- Claude Haiku 4.5를 통한 고품질 블로그 콘텐츠 생성
- "스마트개미 코인봇" 페르소나 유지
- SEO 최적화 및 자연스러운 홍보 삽입
- Imagen 3를 위한 이미지 프롬프트 생성
"""

from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from loguru import logger
import json

from security.credential_manager import CredentialManager
from utils.cost_optimizer import cost_optimizer, cost_tracker


class ContentAgent:
    """페르소나 기반 블로그 포스트 생성 에이전트"""

    # 페르소나 설정
    PERSONA = {
        "name": "스마트개미 코인봇",
        "occupation": "데이터 분석을 좋아하는 평범한 직장인 투자자",
        "investment_style": "뇌동매매 지양, 시스템 매매 신뢰",
        "tone": "친근한 경어체 (~해요, ~네요)",
        "hook_phrases": [
            "솔직히", "저도 처음엔", "회사 끝나고",
            "오늘 점심 먹다가", "퇴근길에", "저만 그런가요?"
        ],
        "avoid_words": [
            "무조건", "100% 수익", "대박", "강력 추천",
            "절대", "확실한", "보장"
        ]
    }

    # 시스템 프롬프트 템플릿
    SYSTEM_PROMPT = """당신은 네이버 블로그에서 활동하는 3년 차 암호화폐 투자자 '스마트개미 코인봇'입니다.

<페르소나>
- 직업: 데이터 분석을 좋아하는 평범한 직장인 투자자
- 투자 성향: 감정적 뇌동매매를 지양하고 시스템 매매를 신뢰
- 말투: 친근한 경어체 ("~해요", "~네요", "~거든요")
- 특징: 솔직하고 공감을 유도하는 스타일

<글쓰기 원칙>
1. **광고처럼 보이면 안 됩니다**
   - "강력 추천", "100% 수익", "대박" 같은 표현 절대 금지
   - 자연스러운 경험담으로 접근

2. **개인적 경험 중심**
   - "오늘 점심 먹다가", "퇴근길에" 등 구체적 상황 설정
   - "저도 처음엔", "솔직히" 등으로 공감 유도

3. **데이터는 정확하게, 감정은 진솔하게**
   - 수치나 사실은 정확히 언급
   - 감정 표현은 진솔하고 공감 가능하게

4. **투자 권유가 아닌 정보 공유**
   - "~하세요" 대신 "~더라고요", "~같아요" 사용
   - 반드시 투자 주의사항 명시

<블로그 구조>
1. 도입부 (Hook): 시장 상황 + 개인 감정
2. 본론 1 (News): 뉴스 핵심 + 개인 투자자 관점 분석
3. 본론 2 (Experience): AI 자동매매 사용 경험담
4. 결론 (CTA): 투자 주의사항 + 자연스러운 링크

<AI 자동매매 언급 가이드>
- 직접적 홍보 X: "이거 쓰세요" (X)
- 자연스러운 경험담 O: "저는 이런 변동성 장세에서 AI한테 맡겨두고 있어요" (O)
- 구체적 경험: "오늘 아침에 AI가 자동으로 손절해줘서 큰 손실 막았어요"
- 겸손한 톤: "완벽하진 않지만 감정 매매보단 낫더라고요"
"""

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Args:
            credential_manager: 자격증명 관리자
        """
        self.cred_manager = credential_manager or CredentialManager()

        # Anthropic API 클라이언트
        anthropic_key = self.cred_manager.get_api_key("anthropic")

        if not anthropic_key:
            logger.warning(
                "Anthropic API 키가 없습니다. "
                "credential_manager.py를 실행하여 키를 저장하세요."
            )
            self.claude = None
        else:
            self.claude = Anthropic(api_key=anthropic_key)

    def generate_post(
        self,
        research_data: Dict[str, Any],
        target_length: int = 1200,
        include_ai_promo: bool = True,
        use_cache: bool = True,
        model: str = "haiku"  # "haiku" 또는 "sonnet"
    ) -> Dict[str, str]:
        """
        블로그 포스트 생성

        Args:
            research_data: Research Agent의 출력
            target_length: 목표 글자 수
            include_ai_promo: AI 자동매매 홍보 포함 여부

        Returns:
            {
                "title": str,      # 제목
                "content": str,    # 본문 (HTML)
                "tags": List[str], # 태그
                "summary": str     # 요약 (메타 설명용)
            }
        """
        if not self.claude:
            logger.error("Claude API 클라이언트가 초기화되지 않았습니다")
            return self._generate_fallback_post(research_data)

        logger.info(f"블로그 포스트 생성 시작 (모델: {model}, 캐시: {use_cache})")

        # 캐시 확인
        if use_cache:
            cache_key_data = {
                "topic": research_data.get("topic"),
                "sentiment": research_data.get("sentiment"),
                "target_length": target_length
            }
            cached = cost_optimizer.get_cached_response("content", cache_key_data)
            if cached:
                logger.success("캐시된 콘텐츠 사용 (API 호출 비용 절약!)")
                return cached

        try:
            # 모델 선택
            model_id = {
                "haiku": "claude-3-5-haiku-20241022",  # 저렴한 모델 (Sonnet 대비 80% 저렴)
                "sonnet": "claude-sonnet-4-20250514"   # 고품질 모델
            }.get(model, "claude-3-5-haiku-20241022")
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(
                research_data,
                target_length,
                include_ai_promo
            )

            # Claude API 호출 (Prompt Caching 사용)
            response = self.claude.messages.create(
                model=model_id,
                max_tokens=2000,  # 토큰 수 줄임 (비용 절감)
                temperature=0.7,
                system=[
                    {
                        "type": "text",
                        "text": self.SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"}  # 시스템 프롬프트 캐싱!
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # 비용 추적
            usage = response.usage
            cost_tracker.log_usage(
                model=model_id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0),
                cache_write_tokens=getattr(usage, 'cache_creation_input_tokens', 0)
            )

            # 응답 파싱
            content = response.content[0].text

            # 제목, 본문, 태그 추출
            result = self._parse_claude_response(content, research_data)

            # 캐시에 저장
            if use_cache:
                cache_key_data = {
                    "topic": research_data.get("topic"),
                    "sentiment": research_data.get("sentiment"),
                    "target_length": target_length
                }
                cost_optimizer.save_to_cache("content", cache_key_data, result)

            logger.success(f"블로그 포스트 생성 완료 ({len(result['content'])}자)")
            return result

        except Exception as e:
            logger.error(f"Claude API 호출 실패: {e}")
            return self._generate_fallback_post(research_data)

    def _build_user_prompt(
        self,
        research_data: Dict[str, Any],
        target_length: int,
        include_ai_promo: bool
    ) -> str:
        """사용자 프롬프트 구성"""

        sentiment_emoji = {
            "positive": "📈",
            "negative": "📉",
            "neutral": "📊"
        }.get(research_data.get("sentiment", "neutral"), "📊")

        promo_instruction = """

<AI 자동매매 사용 경험 필수 포함>
- 본론 2에서 자연스럽게 AI 자동매매 사용 경험 언급
- 오늘 시장 상황과 연결하여 "이런 날 AI가 도움됐다" 식으로 작성
- 구체적 경험: 예) "아침에 AI가 자동으로 익절/손절 해줘서..."
- 겸손한 톤 유지: "완벽하진 않지만", "저한테는 맞더라고요"
""" if include_ai_promo else "\n<AI 자동매매 언급하지 않기>\n"

        prompt = f"""다음 암호화폐 뉴스를 바탕으로 고품질 블로그 포스트를 작성해주세요:

<뉴스 정보>
주제: {research_data.get('topic', '암호화폐 시장 동향')}
요약: {research_data.get('summary', '')}
감성: {research_data.get('sentiment', 'neutral')} {sentiment_emoji}
키워드: {', '.join(research_data.get('keywords', []))}

<작성 요구사항>

1. **목표 분량**: 약 {target_length}자 (1500자 이상 권장)

2. **글 구조** (반드시 마크다운 서식 사용!):

   **도입부 (Hook)** - 독자의 관심을 끄는 시작
   - 충격적인 수치나 질문으로 시작
   - 예: "어제 비트코인이 단 4시간 만에 5% 급등했어요. 여러분은 이 무빙, 잡으셨나요?"
   - 예: "솔직히 말씀드리면, 저도 이번 상승장은 못 탔어요 ㅠㅠ"

   **## 소제목1: 무슨 일이 있었나?** (뉴스 핵심)
   - 뉴스의 핵심 내용을 쉽게 풀어서 설명
   - 구체적인 수치와 날짜 포함
   - **중요한 키워드**는 굵게 표시

   **## 소제목2: 왜 이런 일이?** (분석)
   - 개인 투자자 관점에서 분석
   - 전문 용어는 쉽게 풀어서 설명
   - > 인용구로 핵심 포인트 강조

   **## 소제목3: 그래서 어떻게?** (대응 전략){promo_instruction}
   - 실제 경험담 공유
   - 구체적인 대응 방법 제시

   **마무리**
   - 투자 주의사항 (필수)
   - 따뜻한 마무리 인사

3. **마크다운 서식 규칙** (중요!):
   - 소제목: `## 소제목 텍스트` (반드시 ## 사용)
   - 강조: `**강조할 텍스트**` (굵게)
   - 인용: `> 인용할 문장` (인용구)
   - 줄바꿈: 문단 사이에 빈 줄 2개

4. **SEO 키워드 자연스럽게 7~10회 반복**:
   {', '.join(research_data.get('keywords', [])[:3])}

5. **문체**:
   - 친근한 경어체 ("~해요", "~네요", "~거든요")
   - 공감 유도 ("저도", "솔직히", "사실", "진짜")
   - 구체적 상황 ("오늘 점심 먹다가", "퇴근길에", "아침에 눈 떠보니")
   - 이모지 적절히 사용 (과하지 않게 1~3개)

6. **금지 사항**:
   - 광고성 표현 ("강력 추천", "100% 수익", "대박", "떡상")
   - 단정적 표현 ("무조건", "확실한", "절대")
   - 직접적 투자 권유

<출력 형식>
제목: (40자 이내, 호기심 유발, SEO 키워드 포함)
---
(본문 - 마크다운 서식 사용)
---
태그: (쉼표로 구분, 7~10개)
---
요약: (100자 이내, 메타 설명용)
"""

        return prompt

    def _parse_claude_response(
        self,
        content: str,
        research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Claude 응답 파싱"""

        lines = content.split("---")

        # 제목 추출
        title_section = lines[0] if len(lines) > 0 else ""
        title = title_section.replace("제목:", "").strip()

        # 본문 추출
        body = lines[1].strip() if len(lines) > 1 else content

        # 태그 추출
        tags_section = lines[2] if len(lines) > 2 else ""
        tags_text = tags_section.replace("태그:", "").strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        # 요약 추출
        summary = lines[3].strip() if len(lines) > 3 else research_data.get("summary", "")[:100]

        # 기본 태그 추가
        default_tags = ["암호화폐", "비트코인", "투자"]
        for tag in default_tags:
            if tag not in tags and len(tags) < 10:
                tags.append(tag)

        return {
            "title": title,
            "content": body,
            "tags": tags,
            "summary": summary
        }

    def _generate_fallback_post(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Claude API 실패 시 기본 포스트 생성"""

        topic = research_data.get("topic", "암호화폐 시장 동향")
        summary = research_data.get("summary", "")

        title = f"{topic} - 오늘의 시장 분석"

        content = f"""
<p>안녕하세요, 스마트개미 코인봇입니다.</p>

<h2>{topic}</h2>

<p>{summary}</p>

<p>오늘도 시장이 많이 움직이네요. 이럴 때일수록 감정적으로 대응하기보다는
시스템적으로 접근하는 게 중요한 것 같아요.</p>

<p>저는 개인적으로 AI 자동매매 시스템을 활용하고 있는데요,
이런 변동성 장세에서 감정에 휘둘리지 않고 대응할 수 있어서 좋더라고요.</p>

<h3>투자 주의사항</h3>

<p>이 글은 개인적인 의견이며 투자 권유가 아닙니다.
투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.</p>

<p>오늘도 현명한 투자 되세요!</p>
"""

        return {
            "title": title,
            "content": content,
            "tags": research_data.get("keywords", []) + ["암호화폐", "투자"],
            "summary": summary[:100]
        }

    def refine_content(
        self,
        original_content: str,
        feedback: str
    ) -> str:
        """
        QA Agent의 피드백을 반영하여 콘텐츠 개선

        Args:
            original_content: 원본 콘텐츠
            feedback: 개선 피드백

        Returns:
            개선된 콘텐츠
        """
        if not self.claude:
            logger.warning("Claude API 없음, 원본 반환")
            return original_content

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": f"""다음 블로그 콘텐츠를 개선해주세요:

<원본 콘텐츠>
{original_content}

<개선 피드백>
{feedback}

페르소나와 글쓰기 원칙을 유지하면서 피드백을 반영하여 개선된 버전을 작성해주세요.
"""
                    }
                ]
            )

            refined = response.content[0].text
            logger.success("콘텐츠 개선 완료")
            return refined

        except Exception as e:
            logger.error(f"콘텐츠 개선 실패: {e}")
            return original_content

    def generate_image_prompts(
        self,
        post_title: str,
        post_content: str,
        keywords: List[str],
        sentiment: str = "neutral",
        num_images: int = 2
    ) -> Dict[str, Any]:
        """
        블로그 콘텐츠 기반 Imagen 3용 이미지 프롬프트 생성

        Args:
            post_title: 포스트 제목
            post_content: 포스트 본문
            keywords: SEO 키워드 리스트
            sentiment: 감성 (positive/negative/neutral)
            num_images: 생성할 본문 이미지 수

        Returns:
            {
                "thumbnail_prompt": str,      # 썸네일 프롬프트
                "content_prompts": List[str], # 본문 이미지 프롬프트들
                "style_guide": str            # 스타일 가이드
            }
        """
        if not self.claude:
            logger.warning("Claude API 없음, 기본 프롬프트 반환")
            return self._generate_fallback_prompts(post_title, keywords)

        logger.info("이미지 프롬프트 생성 시작")

        # ═══════════════════════════════════════════════════════════════
        # 확장된 밈 기반 크립토 아트 스타일 풀
        # 매번 다양한 조합 + 글 주제/키워드 반영
        # ═══════════════════════════════════════════════════════════════
        import random

        # 확장된 캐릭터 풀 (16가지)
        meme_characters = [
            # 클래식 밈 동물
            "a cool cartoon frog with laser eyes and diamond hands",
            "a Shiba Inu dog astronaut with golden helmet",
            "a powerful muscular bull in luxury suit",
            "a wise cartoon cat with cyber glowing eyes",
            "a cartoon gorilla with diamond fists",
            "a majestic lion with golden crown and neon mane",
            "a clever fox trader with holographic monocle",
            "a penguin in tuxedo holding golden briefcase",
            # 로봇/AI
            "a sleek humanoid robot with holographic brain",
            "a massive mech warrior with trading screens",
            "a cute AI assistant robot with LED heart eyes",
            # 판타지
            "a dragon breathing golden flames",
            "a phoenix rising with golden wings",
            "a unicorn with rainbow neon mane",
            # 캐릭터
            "a samurai warrior with digital katana",
            "a superhero with cape made of golden coins",
        ]

        # 감성별 확장 액션 풀
        meme_actions = {
            "positive": [
                "riding a blazing rocket to the moon",
                "surfing on massive green candlestick wave",
                "breaking through resistance wall with explosive power",
                "standing on golden mountain of coins victoriously",
                "flying upward with jet boots and fire trail",
                "punching through ceiling with diamond fist",
                "celebrating with confetti and fireworks",
                "holding giant green arrow pointing to sky",
            ],
            "negative": [
                "defending with glowing energy shield",
                "analyzing red falling charts with focused eyes",
                "standing firm in digital thunderstorm",
                "meditating calmly amid market chaos",
                "building fortress of stacked coins",
                "wearing armor against red arrows",
            ],
            "neutral": [
                "commanding holographic trading screens",
                "standing at crossroads of bull and bear",
                "balancing on scale between profit and loss",
                "studying ancient crypto scrolls",
                "operating futuristic command center",
                "floating in digital meditation pose",
            ]
        }

        # 감성별 확장 배경 풀
        background_styles = {
            "positive": [
                "space with giant moon and Earth, stars everywhere",
                "golden city skyline with fireworks",
                "mountain peak above clouds at sunrise",
                "stadium with cheering crowd and confetti",
                "volcano erupting golden lava",
                "rainbow bridge to golden gates",
            ],
            "negative": [
                "dark stormy sky with lightning",
                "deep sea with bioluminescent creatures",
                "foggy battlefield with warning lights",
                "abandoned futuristic city at night",
                "ice cave with blue crystals",
            ],
            "neutral": [
                "cyberpunk neon city with rain",
                "futuristic trading floor with floating screens",
                "matrix digital rain environment",
                "zen garden with holographic trees",
                "space station orbiting Earth",
                "abstract geometric dimension",
            ]
        }

        # 확장된 아트 스타일 풀 (12가지)
        style_keywords = [
            "cinematic 3D render, Pixar quality, dramatic lighting",
            "cyberpunk neon art, high contrast, vibrant",
            "anime style, dynamic pose, vibrant colors",
            "comic book art, bold outlines, action scene",
            "retro 80s synthwave, neon grid, sunset",
            "vaporwave aesthetic, pink and blue, dreamy",
            "pixel art 16-bit, retro gaming style",
            "oil painting style, dramatic brushstrokes",
            "graffiti street art, urban, bold colors",
            "low-poly 3D geometric, modern minimal",
            "holographic iridescent, futuristic glow",
            "watercolor digital, soft edges, artistic",
        ]

        # 감성별 색상 팔레트
        color_moods = {
            "positive": [
                "golden glow, vibrant green neon",
                "orange fire, yellow explosion",
                "pink and gold luxury",
                "emerald green, diamond sparkle",
            ],
            "negative": [
                "cool blue, purple tones",
                "dark red, black dramatic",
                "silver, ice blue",
                "deep ocean blue, teal",
            ],
            "neutral": [
                "blue and purple neon balance",
                "silver and cyan tech",
                "white and rainbow gradient",
                "monochrome with neon accents",
            ]
        }

        # 랜덤 요소 선택
        selected_character = random.choice(meme_characters)
        selected_action = random.choice(meme_actions.get(sentiment, meme_actions["neutral"]))
        selected_background = random.choice(background_styles.get(sentiment, background_styles["neutral"]))
        selected_color = random.choice(color_moods.get(sentiment, color_moods["neutral"]))
        selected_style = random.choice(style_keywords)

        # 키워드 기반 주제 힌트 생성
        topic_hint = ""
        keyword_lower = " ".join(keywords[:3]).lower()
        if "비트코인" in keyword_lower or "bitcoin" in keyword_lower or "btc" in keyword_lower:
            topic_hint = "Bitcoin symbol, orange B coin"
        elif "이더리움" in keyword_lower or "ethereum" in keyword_lower or "eth" in keyword_lower:
            topic_hint = "Ethereum diamond symbol, purple glow"
        elif "솔라나" in keyword_lower or "solana" in keyword_lower or "sol" in keyword_lower:
            topic_hint = "Solana gradient colors, fast movement"
        elif "리플" in keyword_lower or "xrp" in keyword_lower:
            topic_hint = "XRP wave pattern, blue ripples"
        elif "도지" in keyword_lower or "doge" in keyword_lower:
            topic_hint = "Doge meme style, fun and playful"
        elif "ai" in keyword_lower or "인공지능" in keyword_lower:
            topic_hint = "AI brain, neural network visualization"
        elif "etf" in keyword_lower:
            topic_hint = "institutional finance, Wall Street aesthetic"
        else:
            topic_hint = "generic crypto coins and blockchain"

        image_prompt_system = f"""당신은 크립토/밈 아트 전문 이미지 프롬프트 생성 전문가입니다.
트렌디하고 강렬한 밈 스타일의 크립토 아트 이미지 프롬프트를 생성합니다.

<핵심 스타일: 밈 기반 크립토 아트>
- Cinematic digital illustration (영화 같은 디지털 일러스트)
- Cyberpunk aesthetic (사이버펑크 스타일)
- Crypto meme art (크립토 밈 아트)
- Vibrant neon colors (강렬한 네온 컬러)
- Dramatic lighting, high contrast (극적인 조명, 높은 대비)

<사용 가능한 요소들>
1. 캐릭터: {selected_character}
2. 액션/상황: {selected_action}
3. 배경: {selected_background}
4. 색상/분위기: {selected_color}
5. 스타일: {selected_style}

<프롬프트 작성 원칙>
1. 영어로 작성 (50-100단어)
2. 위 요소들을 조합하여 강렬한 이미지 묘사
3. 텍스트/글자 절대 포함 금지 ("no text, no words, no letters" 필수)
4. 저작권 문제 없는 일반적 동물/로봇 캐릭터 사용
5. 16:9 비율, 4K 고품질

<출력 형식>
반드시 아래 JSON 형식으로만 응답하세요:
{{
    "thumbnail_prompt": "썸네일용 영어 프롬프트 (강렬한 밈 스타일)",
    "content_prompts": ["본문 이미지1 프롬프트", "본문 이미지2 프롬프트"],
    "styles_used": ["사용된 스타일들"],
    "style_guide": "전체적인 스타일 설명"
}}
"""

        # 감성별 밈 스타일 가이드
        sentiment_guide = {
            "positive": "BULLISH energy, rocket to the moon, golden glow, green upward arrows, victory pose, explosive success, laser eyes effect",
            "negative": "cautious bear market mood, red warning lights, defensive stance, protective imagery, cool blue tones, analytical feel",
            "neutral": "balanced crypto trading vibe, holographic charts, professional trader aesthetic, blue and purple neons, tech-forward look"
        }.get(sentiment, "balanced crypto aesthetic")

        user_prompt = f"""다음 블로그 포스트에 어울리는 강렬한 밈 스타일 크립토 아트 이미지 프롬프트를 생성해주세요:

<포스트 정보>
제목: {post_title}
키워드: {', '.join(keywords[:5])}
감성: {sentiment}
주제 힌트: {topic_hint}

<이번에 사용할 요소 (반드시 포함!)>
- 캐릭터: {selected_character}
- 액션: {selected_action}
- 배경: {selected_background}
- 색상 분위기: {selected_color}
- 스타일: {selected_style}

<분위기 가이드>
{sentiment_guide}

<본문 요약>
{post_content[:300]}...

<요청사항>
1. 썸네일: 블로그 대표 이미지 - 강렬한 임팩트!
   - 위 캐릭터 + 액션 + 배경 조합
   - 주제 힌트({topic_hint}) 시각적으로 반영
   - 밈 스타일의 과감한 비주얼
   - "no text, no words, no letters, no watermarks, no human faces" 필수

2. 본문 이미지 {num_images}개: 각각 다른 느낌으로
   - 썸네일과 다른 캐릭터/상황 사용
   - 주제 힌트와 연관된 비주얼
   - 다양한 구도와 스타일

3. 공통 규칙:
   - 특정 암호화폐 로고 대신 일반적인 코인/차트 심볼 사용
   - 실제 인물 얼굴 없음 (캐릭터/로봇만)
   - 고품질, 4K, 선명한 이미지

JSON 형식으로만 응답해주세요.
"""

        try:
            response = self.claude.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1000,
                temperature=0.7,
                system=image_prompt_system,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # 응답 파싱
            content = response.content[0].text

            # JSON 추출 (마크다운 코드블록 처리)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            logger.success("이미지 프롬프트 생성 완료")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return self._generate_fallback_prompts(post_title, keywords)
        except Exception as e:
            logger.error(f"이미지 프롬프트 생성 실패: {e}")
            return self._generate_fallback_prompts(post_title, keywords)

    def _generate_fallback_prompts(
        self,
        title: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """폴백 이미지 프롬프트 생성"""
        keywords_en = "cryptocurrency, bitcoin, trading, investment, digital assets"

        return {
            "thumbnail_prompt": f"Modern cryptocurrency trading concept art, {keywords_en}, professional blog header, blue and gold color scheme, abstract digital visualization, no text",
            "content_prompts": [
                f"Financial data visualization, {keywords_en}, clean infographic style, modern design, no text or numbers",
                f"Abstract blockchain technology concept, {keywords_en}, futuristic digital art, gradient colors, no text"
            ],
            "style_guide": "Professional, modern, tech-focused imagery with blue/gold color palette"
        }

    def generate_post_with_images(
        self,
        research_data: Dict[str, Any],
        target_length: int = 1200,
        include_ai_promo: bool = True,
        num_images: int = 2
    ) -> Dict[str, Any]:
        """
        블로그 포스트와 이미지 프롬프트를 함께 생성

        Args:
            research_data: Research Agent의 출력
            target_length: 목표 글자 수
            include_ai_promo: AI 자동매매 홍보 포함 여부
            num_images: 본문 이미지 수

        Returns:
            {
                "title": str,
                "content": str,
                "tags": List[str],
                "summary": str,
                "image_prompts": {
                    "thumbnail_prompt": str,
                    "content_prompts": List[str],
                    "style_guide": str
                }
            }
        """
        # 1. 포스트 생성
        post_result = self.generate_post(
            research_data=research_data,
            target_length=target_length,
            include_ai_promo=include_ai_promo,
            model="haiku"  # Haiku 4.5 사용
        )

        # 2. 이미지 프롬프트 생성
        image_prompts = self.generate_image_prompts(
            post_title=post_result["title"],
            post_content=post_result["content"],
            keywords=research_data.get("keywords", []),
            sentiment=research_data.get("sentiment", "neutral"),
            num_images=num_images
        )

        # 결과 합치기
        post_result["image_prompts"] = image_prompts

        logger.success("포스트 + 이미지 프롬프트 생성 완료")
        return post_result


# ============================================
# 테스트 코드
# ============================================

def test_content_agent():
    """Content Agent 테스트"""
    print("\n=== Content Agent 테스트 ===\n")

    # 테스트 리서치 데이터
    test_research = {
        "topic": "비트코인 6만 달러 돌파, 기관 투자 급증",
        "summary": "비트코인이 6만 달러를 돌파하며 신고가를 경신했습니다. "
                   "블랙록, 피델리티 등 기관 투자자들의 ETF 매수세가 강하게 유입되고 있습니다.",
        "sentiment": "positive",
        "sentiment_score": 0.8,
        "keywords": ["비트코인", "ETF", "기관투자", "신고가"],
        "source_urls": ["https://example.com"]
    }

    agent = ContentAgent()
    result = agent.generate_post(test_research)

    print(f"제목: {result['title']}\n")
    print(f"본문:\n{result['content']}\n")
    print(f"태그: {', '.join(result['tags'])}\n")
    print(f"요약: {result['summary']}")


if __name__ == "__main__":
    test_content_agent()
