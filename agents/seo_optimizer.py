"""
SEO 최적화 에이전트
- 제목 최적화
- 콘텐츠 SEO 분석
- 태그 추천
- Claude Haiku 사용으로 비용 최적화
"""

import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
    logger.warning("anthropic 패키지가 설치되지 않았습니다")


class SEOOptimizer:
    """SEO 최적화 에이전트"""

    # 비용 최적화를 위해 Haiku 모델 사용
    MODEL = "claude-3-haiku-20240307"

    # 최적 제목 길이
    OPTIMAL_TITLE_LENGTH = (30, 60)

    # 최적 키워드 밀도 (%)
    OPTIMAL_KEYWORD_DENSITY = (1.0, 3.0)

    # SEO 체크 항목별 가중치
    SEO_WEIGHTS = {
        "title_length": 15,
        "title_keywords": 20,
        "meta_description": 10,
        "keyword_density": 15,
        "heading_structure": 10,
        "content_length": 10,
        "internal_links": 5,
        "image_alt": 10,
        "readability": 5
    }

    def __init__(self):
        """초기화"""
        self.client = None
        if Anthropic:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = Anthropic(api_key=api_key)
                logger.info("SEOOptimizer 초기화 완료 (Claude Haiku)")
            else:
                logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다")

    async def optimize_title(self, original_title: str, keywords: List[str]) -> Dict[str, Any]:
        """
        제목 SEO 최적화

        Args:
            original_title: 원본 제목
            keywords: 타겟 키워드 목록

        Returns:
            최적화된 제목 및 분석 결과
        """
        result = {
            "original": original_title,
            "optimized": original_title,
            "suggestions": [],
            "score": 0
        }

        # 1. 길이 체크
        title_length = len(original_title)
        if title_length < self.OPTIMAL_TITLE_LENGTH[0]:
            result["suggestions"].append(f"제목이 너무 짧습니다 ({title_length}자). 30자 이상 권장")
        elif title_length > self.OPTIMAL_TITLE_LENGTH[1]:
            result["suggestions"].append(f"제목이 너무 깁니다 ({title_length}자). 60자 이하 권장")
        else:
            result["score"] += 20

        # 2. 키워드 포함 체크
        title_lower = original_title.lower()
        keywords_found = [kw for kw in keywords if kw.lower() in title_lower]

        if keywords_found:
            result["score"] += 30
        else:
            result["suggestions"].append(f"핵심 키워드를 제목에 포함하세요: {', '.join(keywords[:3])}")

        # 3. 숫자/특수문자 체크 (클릭률 향상)
        if re.search(r'\d+', original_title):
            result["score"] += 10
        else:
            result["suggestions"].append("숫자를 포함하면 클릭률이 향상됩니다 (예: '5가지 방법')")

        # 4. AI를 통한 제목 개선 (클라이언트가 있을 때만)
        if self.client and result["score"] < 50:
            try:
                optimized = await self._ai_optimize_title(original_title, keywords)
                if optimized:
                    result["optimized"] = optimized
                    result["ai_improved"] = True
            except Exception as e:
                logger.warning(f"AI 제목 최적화 실패: {e}")

        return result

    async def _ai_optimize_title(self, title: str, keywords: List[str]) -> Optional[str]:
        """AI를 사용한 제목 최적화"""
        if not self.client:
            return None

        prompt = f"""다음 블로그 제목을 SEO 최적화해주세요.

원본 제목: {title}
타겟 키워드: {', '.join(keywords)}

요구사항:
1. 30-60자 사이
2. 키워드를 자연스럽게 포함
3. 클릭을 유도하는 매력적인 제목
4. 숫자나 특수 표현 활용

최적화된 제목만 출력하세요."""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"AI 제목 최적화 오류: {e}")
            return None

    async def analyze_seo_score(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        콘텐츠 SEO 점수 분석

        Args:
            content: 콘텐츠 정보 (title, body, keywords, images 등)

        Returns:
            SEO 분석 결과
        """
        title = content.get("title", "")
        body = content.get("body", "")
        keywords = content.get("keywords", [])
        images = content.get("images", [])

        scores = {}
        issues = []
        suggestions = []

        # 1. 제목 길이
        title_len = len(title)
        if self.OPTIMAL_TITLE_LENGTH[0] <= title_len <= self.OPTIMAL_TITLE_LENGTH[1]:
            scores["title_length"] = self.SEO_WEIGHTS["title_length"]
        else:
            scores["title_length"] = self.SEO_WEIGHTS["title_length"] * 0.5
            issues.append(f"제목 길이 부적절 ({title_len}자)")

        # 2. 제목 키워드
        title_lower = title.lower()
        if any(kw.lower() in title_lower for kw in keywords):
            scores["title_keywords"] = self.SEO_WEIGHTS["title_keywords"]
        else:
            scores["title_keywords"] = 0
            issues.append("제목에 핵심 키워드 없음")

        # 3. 콘텐츠 길이
        content_length = len(body)
        if content_length >= 1500:
            scores["content_length"] = self.SEO_WEIGHTS["content_length"]
        elif content_length >= 800:
            scores["content_length"] = self.SEO_WEIGHTS["content_length"] * 0.7
        else:
            scores["content_length"] = self.SEO_WEIGHTS["content_length"] * 0.3
            issues.append(f"콘텐츠 길이 부족 ({content_length}자)")

        # 4. 키워드 밀도
        if keywords and body:
            keyword_count = sum(body.lower().count(kw.lower()) for kw in keywords)
            word_count = len(body.split())
            density = (keyword_count / max(word_count, 1)) * 100

            if self.OPTIMAL_KEYWORD_DENSITY[0] <= density <= self.OPTIMAL_KEYWORD_DENSITY[1]:
                scores["keyword_density"] = self.SEO_WEIGHTS["keyword_density"]
            elif density < self.OPTIMAL_KEYWORD_DENSITY[0]:
                scores["keyword_density"] = self.SEO_WEIGHTS["keyword_density"] * 0.5
                suggestions.append("키워드 밀도를 높이세요")
            else:
                scores["keyword_density"] = self.SEO_WEIGHTS["keyword_density"] * 0.3
                issues.append(f"키워드 과다 사용 ({density:.1f}%)")
        else:
            scores["keyword_density"] = 0

        # 5. 헤딩 구조
        heading_pattern = r'<h[1-6][^>]*>.*?</h[1-6]>'
        headings = re.findall(heading_pattern, body, re.IGNORECASE | re.DOTALL)
        if len(headings) >= 3:
            scores["heading_structure"] = self.SEO_WEIGHTS["heading_structure"]
        elif len(headings) >= 1:
            scores["heading_structure"] = self.SEO_WEIGHTS["heading_structure"] * 0.5
        else:
            scores["heading_structure"] = 0
            suggestions.append("H2, H3 등 소제목을 추가하세요")

        # 6. 이미지 alt 텍스트
        if images:
            images_with_alt = sum(1 for img in images if img.get("alt_text"))
            alt_ratio = images_with_alt / len(images)
            scores["image_alt"] = self.SEO_WEIGHTS["image_alt"] * alt_ratio
            if alt_ratio < 1:
                suggestions.append("모든 이미지에 alt 텍스트를 추가하세요")
        else:
            scores["image_alt"] = self.SEO_WEIGHTS["image_alt"] * 0.5
            suggestions.append("관련 이미지를 추가하면 SEO에 도움됩니다")

        # 7. 가독성 (문장 길이 기반 간단한 체크)
        sentences = re.split(r'[.!?]', body)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if 10 <= avg_sentence_length <= 25:
            scores["readability"] = self.SEO_WEIGHTS["readability"]
        else:
            scores["readability"] = self.SEO_WEIGHTS["readability"] * 0.5

        # 총점 계산
        total_score = sum(scores.values())
        max_score = sum(self.SEO_WEIGHTS.values())
        percentage = (total_score / max_score) * 100

        return {
            "total_score": round(total_score, 1),
            "max_score": max_score,
            "percentage": round(percentage, 1),
            "grade": self._get_grade(percentage),
            "scores": scores,
            "issues": issues,
            "suggestions": suggestions
        }

    def _get_grade(self, percentage: float) -> str:
        """점수를 등급으로 변환"""
        if percentage >= 90:
            return "A+"
        elif percentage >= 80:
            return "A"
        elif percentage >= 70:
            return "B"
        elif percentage >= 60:
            return "C"
        elif percentage >= 50:
            return "D"
        else:
            return "F"

    async def suggest_tags(self, title: str, content: str, max_tags: int = 10) -> List[str]:
        """
        SEO 최적화 태그 추천

        Args:
            title: 제목
            content: 본문
            max_tags: 최대 태그 수

        Returns:
            추천 태그 목록
        """
        if not self.client:
            # AI 없이 기본 태그 추출
            return self._extract_basic_tags(title, content, max_tags)

        prompt = f"""다음 블로그 글에 적합한 SEO 태그를 {max_tags}개 추천해주세요.

제목: {title}
내용 (일부): {content[:500]}...

요구사항:
1. 검색량이 높은 키워드 우선
2. 롱테일 키워드 포함
3. 한글 태그 위주
4. 각 태그는 쉼표로 구분

태그만 출력하세요."""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            tags_str = response.content[0].text.strip()
            tags = [tag.strip() for tag in tags_str.split(",")]
            return tags[:max_tags]
        except Exception as e:
            logger.error(f"태그 추천 오류: {e}")
            return self._extract_basic_tags(title, content, max_tags)

    def _extract_basic_tags(self, title: str, content: str, max_tags: int) -> List[str]:
        """기본 태그 추출 (AI 없이)"""
        # 제목에서 키워드 추출
        words = re.findall(r'[가-힣]+', title + " " + content[:200])
        word_freq = {}
        for word in words:
            if len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        # 빈도순 정렬
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_tags]]


# ============================================
# 테스트 코드
# ============================================

async def test_seo_optimizer():
    """SEOOptimizer 테스트"""
    print("\n=== SEOOptimizer 테스트 ===\n")

    optimizer = SEOOptimizer()

    # 제목 최적화 테스트
    test_title = "비트코인 상승"
    test_keywords = ["비트코인", "암호화폐", "투자"]

    print("제목 최적화 테스트:")
    result = await optimizer.optimize_title(test_title, test_keywords)
    print(f"  원본: {result['original']}")
    print(f"  점수: {result['score']}")
    print(f"  제안: {result['suggestions']}")

    # SEO 분석 테스트
    test_content = {
        "title": "비트코인 10만 달러 돌파! 2024년 암호화폐 시장 전망",
        "body": """
        <h2>비트코인의 역사적인 순간</h2>
        <p>비트코인이 드디어 10만 달러를 돌파했습니다. 이는 암호화폐 역사상
        가장 중요한 이정표 중 하나입니다.</p>
        <h2>전문가들의 전망</h2>
        <p>많은 전문가들이 비트코인의 추가 상승을 예측하고 있습니다...</p>
        """ * 10,  # 충분한 길이
        "keywords": ["비트코인", "암호화폐", "투자"],
        "images": [{"url": "test.jpg", "alt_text": "비트코인 차트"}]
    }

    print("\nSEO 분석 테스트:")
    analysis = await optimizer.analyze_seo_score(test_content)
    print(f"  총점: {analysis['total_score']}/{analysis['max_score']} ({analysis['percentage']}%)")
    print(f"  등급: {analysis['grade']}")
    print(f"  이슈: {analysis['issues']}")
    print(f"  제안: {analysis['suggestions']}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_seo_optimizer())
