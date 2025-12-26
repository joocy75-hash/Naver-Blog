"""
Research Orchestrator Agent
- Perplexity Sonar Pro를 통한 실시간 시장 분석
- RSS 피드 파싱 및 뉴스 수집
- 다양한 주제: 미국주식, 국내주식, 암호화폐, AI, 경제, 핫이슈
"""

import asyncio
import feedparser
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI  # Perplexity는 OpenAI 호환 API 사용

from security.credential_manager import CredentialManager


class ResearchAgent:
    """실시간 시장 인사이트 수집 에이전트 (다양한 주제 지원)"""

    # 주제별 RSS 피드
    RSS_FEEDS_BY_CATEGORY = {
        "crypto": [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
        ],
        "us_stock": [
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US",
        ],
        "kr_stock": [
            "https://www.hankyung.com/feed/stock",
        ],
        "economy": [
            "https://www.hankyung.com/feed/economy",
        ],
    }

    # 기본 RSS (암호화폐)
    RSS_FEEDS = RSS_FEEDS_BY_CATEGORY["crypto"]

    # 주제별 검색 쿼리 (Perplexity용)
    SEARCH_QUERIES = {
        "us_stock": "미국 주식 시장 오늘 뉴스 나스닥 S&P500 주요 이슈",
        "kr_stock": "한국 주식 시장 오늘 뉴스 코스피 코스닥 주요 이슈",
        "crypto": "암호화폐 비트코인 이더리움 오늘 뉴스 시세 전망",
        "ai_tech": "AI 인공지능 빅테크 오늘 뉴스 ChatGPT 엔비디아",
        "economy": "경제 금리 환율 인플레이션 오늘 뉴스",
        "hot_issue": "오늘 핫이슈 경제 투자 관련 뉴스",
    }

    # 감성 분석 키워드
    POSITIVE_KEYWORDS = [
        "상승", "급등", "호재", "긍정", "랠리", "돌파", "신고가",
        "bullish", "surge", "rally", "breakout", "all-time high"
    ]

    NEGATIVE_KEYWORDS = [
        "하락", "급락", "악재", "부정", "폭락", "붕괴", "우려",
        "bearish", "crash", "plunge", "collapse", "concern", "fear"
    ]

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Args:
            credential_manager: 자격증명 관리자 (None이면 자동 생성)
        """
        self.cred_manager = credential_manager or CredentialManager()

        # Perplexity API 클라이언트 설정
        perplexity_key = self.cred_manager.get_api_key("perplexity")

        if not perplexity_key:
            logger.warning(
                "Perplexity API 키가 없습니다. "
                "credential_manager.py를 실행하여 키를 저장하세요."
            )
            self.perplexity_client = None
        else:
            self.perplexity_client = OpenAI(
                api_key=perplexity_key,
                base_url="https://api.perplexity.ai"
            )

    async def search_topic(self, category: str) -> Dict[str, Any]:
        """
        Perplexity로 특정 주제에 대한 실시간 정보 검색

        Args:
            category: 주제 카테고리 (us_stock, kr_stock, crypto, ai_tech, economy, hot_issue)

        Returns:
            {
                "category": str,
                "topic": str,
                "summary": str,
                "key_points": List[str],
                "market_data": Dict,
                "investment_angle": str,
                "sources": List[str],
                "timestamp": str
            }
        """
        if category not in self.SEARCH_QUERIES:
            logger.warning(f"알 수 없는 카테고리: {category}, 기본값 사용")
            category = "hot_issue"

        query = self.SEARCH_QUERIES[category]
        logger.info(f"Perplexity 검색 시작: {category} - {query}")

        if not self.perplexity_client:
            logger.error("Perplexity API 클라이언트가 없습니다")
            return self._get_fallback_research(category)

        try:
            prompt = f"""
당신은 한국 투자자를 위한 금융/투자 리서치 전문가입니다.

검색 주제: {query}

다음 형식의 JSON으로 응답해주세요:
{{
    "topic": "오늘의 핵심 주제 (한 문장)",
    "summary": "300-500자 분량의 상세 요약. 구체적인 수치, 기업명, 이벤트 포함",
    "key_points": [
        "핵심 포인트 1",
        "핵심 포인트 2",
        "핵심 포인트 3"
    ],
    "market_data": {{
        "indices": "관련 지수 동향 (예: 나스닥 +1.2%)",
        "notable_stocks": "주목할 종목들",
        "trend": "상승/하락/보합"
    }},
    "investment_angle": "개인 투자자가 주목해야 할 포인트와 시사점 (AI 자동매매 관점에서)",
    "sources": ["출처1", "출처2"]
}}

최신 정보를 기반으로 구체적이고 유용한 인사이트를 제공해주세요.
"""

            response = self.perplexity_client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 금융 시장 분석 전문가입니다. 항상 JSON 형식으로만 응답합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )

            # JSON 파싱
            import json
            result_text = response.choices[0].message.content

            # 마크다운 코드 블록 제거
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result["category"] = category
            result["timestamp"] = datetime.now().isoformat()

            # 감성 분석 추가
            sentiment = self._analyze_sentiment(result.get("summary", ""))
            result.update(sentiment)

            logger.success(f"Perplexity 검색 완료: {result['topic']}")
            return result

        except Exception as e:
            logger.error(f"Perplexity 검색 실패: {e}")
            return self._get_fallback_research(category)

    def _get_fallback_research(self, category: str) -> Dict[str, Any]:
        """Perplexity 실패 시 기본 응답"""
        fallback_topics = {
            "us_stock": "미국 증시 동향과 투자 전략",
            "kr_stock": "국내 증시 동향과 투자 전략",
            "crypto": "암호화폐 시장 동향과 전망",
            "ai_tech": "AI 기술 발전과 투자 기회",
            "economy": "경제 동향과 투자 시사점",
            "hot_issue": "오늘의 핫이슈와 투자 관점"
        }

        return {
            "category": category,
            "topic": fallback_topics.get(category, "투자 시장 동향"),
            "summary": "실시간 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.",
            "key_points": ["데이터 수집 중"],
            "market_data": {"indices": "N/A", "notable_stocks": "N/A", "trend": "N/A"},
            "investment_angle": "AI 자동매매 시스템으로 시장 변동성에 대응하세요.",
            "sources": [],
            "timestamp": datetime.now().isoformat(),
            "sentiment": "neutral",
            "sentiment_score": 0.0
        }

    async def get_trending_topic(self) -> Dict[str, Any]:
        """
        오늘의 트렌딩 암호화폐 주제 찾기

        Returns:
            {
                "topic": str,           # 주제
                "summary": str,         # 요약
                "sentiment": str,       # 감성 (positive/negative/neutral)
                "sentiment_score": float,  # 감성 점수 (-1 ~ 1)
                "source_urls": List[str],  # 출처 URL
                "keywords": List[str],     # 핵심 키워드
                "timestamp": str           # 수집 시간
            }
        """
        logger.info("트렌딩 토픽 수집 시작")

        # 1. RSS 피드에서 최신 뉴스 수집
        news_items = await self._fetch_rss_news()

        # 2. Perplexity로 심층 분석
        if self.perplexity_client and news_items:
            analysis = await self._analyze_with_perplexity(news_items)
        else:
            # Perplexity 없으면 기본 분석
            analysis = self._basic_analysis(news_items)

        # 3. 감성 분석
        sentiment_result = self._analyze_sentiment(
            analysis.get("summary", "") + " " + analysis.get("topic", "")
        )

        result = {
            **analysis,
            **sentiment_result,
            "timestamp": datetime.now().isoformat()
        }

        logger.success(f"트렌딩 토픽 수집 완료: {result['topic']}")
        return result

    async def _fetch_rss_news(self, hours_ago: int = 24) -> List[Dict[str, Any]]:
        """
        RSS 피드에서 최신 뉴스 수집

        Args:
            hours_ago: 몇 시간 전까지의 뉴스를 가져올지

        Returns:
            뉴스 아이템 리스트
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_ago)
        all_news = []

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_single_feed(session, feed_url)
                for feed_url in self.RSS_FEEDS
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_news.extend(result)

        # 시간 필터링 및 정렬
        filtered_news = [
            item for item in all_news
            if item.get("published_date", datetime.min) > cutoff_time
        ]

        filtered_news.sort(key=lambda x: x.get("published_date", datetime.min), reverse=True)

        logger.info(f"RSS 뉴스 {len(filtered_news)}개 수집")
        return filtered_news[:20]  # 최근 20개만

    async def _fetch_single_feed(
        self,
        session: aiohttp.ClientSession,
        feed_url: str
    ) -> List[Dict[str, Any]]:
        """단일 RSS 피드 파싱"""
        try:
            async with session.get(feed_url, timeout=10) as response:
                content = await response.text()

            feed = feedparser.parse(content)
            items = []

            for entry in feed.entries[:10]:  # 피드당 최대 10개
                # 발행 시간 파싱
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                items.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published_date": published or datetime.now(),
                    "source": feed.feed.get("title", feed_url)
                })

            logger.debug(f"RSS 피드 파싱 완료: {feed_url} ({len(items)}개)")
            return items

        except Exception as e:
            logger.error(f"RSS 피드 파싱 실패 ({feed_url}): {e}")
            return []

    async def _analyze_with_perplexity(
        self,
        news_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perplexity로 뉴스 심층 분석"""
        try:
            # 뉴스 요약 텍스트 생성
            news_text = "\n\n".join([
                f"[{item['source']}] {item['title']}\n{item['summary'][:200]}"
                for item in news_items[:10]
            ])

            # Perplexity 프롬프트
            prompt = f"""
다음은 최근 24시간 동안의 암호화폐 관련 뉴스입니다:

{news_text}

이 뉴스들을 분석하여 다음을 제공해주세요:

1. 가장 트렌딩하는 하나의 주제 (한 문장)
2. 해당 주제에 대한 300자 이내의 요약
3. 핵심 키워드 5개 (쉼표로 구분)
4. 개인 투자자들이 가장 관심 가질 만한 포인트

JSON 형식으로 응답해주세요:
{{
    "topic": "주제",
    "summary": "요약",
    "keywords": ["키워드1", "키워드2", ...],
    "investor_insight": "투자자 관심 포인트"
}}
"""

            # API 호출
            response = self.perplexity_client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 암호화폐 시장 분석 전문가입니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )

            # 응답 파싱
            import json
            result_text = response.choices[0].message.content

            # JSON 추출 (마크다운 코드 블록 제거)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())

            # 출처 URL 추가
            result["source_urls"] = [item["link"] for item in news_items[:5]]

            logger.success("Perplexity 분석 완료")
            return result

        except Exception as e:
            logger.error(f"Perplexity 분석 실패: {e}")
            return self._basic_analysis(news_items)

    def _basic_analysis(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기본 뉴스 분석 (Perplexity 없을 때)"""
        if not news_items:
            return {
                "topic": "암호화폐 시장 동향",
                "summary": "최신 뉴스를 확인할 수 없습니다.",
                "keywords": ["비트코인", "암호화폐"],
                "source_urls": []
            }

        # 가장 최신 뉴스를 주제로
        latest = news_items[0]

        return {
            "topic": latest["title"],
            "summary": latest["summary"][:300],
            "keywords": self._extract_keywords(latest["title"] + " " + latest["summary"]),
            "source_urls": [item["link"] for item in news_items[:5]]
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """간단한 키워드 추출"""
        common_crypto_terms = [
            "비트코인", "Bitcoin", "BTC", "이더리움", "Ethereum", "ETH",
            "알트코인", "Altcoin", "DeFi", "NFT", "Web3", "블록체인",
            "Blockchain", "암호화폐", "Crypto", "거래소", "Exchange"
        ]

        found_keywords = [
            term for term in common_crypto_terms
            if term.lower() in text.lower()
        ]

        return found_keywords[:5] if found_keywords else ["암호화폐", "시장"]

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        텍스트 감성 분석

        Returns:
            {
                "sentiment": "positive" | "negative" | "neutral",
                "sentiment_score": float (-1 ~ 1)
            }
        """
        text_lower = text.lower()

        # 긍정/부정 키워드 카운트
        positive_count = sum(
            1 for keyword in self.POSITIVE_KEYWORDS
            if keyword.lower() in text_lower
        )

        negative_count = sum(
            1 for keyword in self.NEGATIVE_KEYWORDS
            if keyword.lower() in text_lower
        )

        # 점수 계산
        total = positive_count + negative_count
        if total == 0:
            sentiment = "neutral"
            score = 0.0
        else:
            score = (positive_count - negative_count) / total

            if score > 0.2:
                sentiment = "positive"
            elif score < -0.2:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        logger.info(f"감성 분석: {sentiment} (점수: {score:.2f})")
        return {
            "sentiment": sentiment,
            "sentiment_score": round(score, 2)
        }


# ============================================
# 테스트 코드
# ============================================

async def test_research_agent():
    """Research Agent 테스트"""
    print("\n=== Research Agent 테스트 ===\n")

    agent = ResearchAgent()
    result = await agent.get_trending_topic()

    print(f"주제: {result['topic']}")
    print(f"\n요약:\n{result['summary']}")
    print(f"\n감성: {result['sentiment']} ({result['sentiment_score']})")
    print(f"\n키워드: {', '.join(result.get('keywords', []))}")
    print(f"\n출처: {len(result['source_urls'])}개")


if __name__ == "__main__":
    asyncio.run(test_research_agent())
