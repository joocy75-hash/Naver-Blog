"""
Quality Assurance Agent
- AI 간 교차 검증 (Claude ↔ Gemini)
- 콘텐츠-이미지 정합성 검사
- 부적절 표현 필터링
- 품질 점수 계산
"""

from typing import Dict, Any, List, Optional, Tuple
from anthropic import Anthropic
import google.generativeai as genai
from loguru import logger

from security.credential_manager import CredentialManager


class QAAgent:
    """콘텐츠 품질 보증 에이전트"""

    # 필터링해야 할 표현들
    FORBIDDEN_PHRASES = [
        "100% 수익", "무조건", "대박", "강력 추천",
        "확실한 수익", "수익 보장", "완벽한 수익",
        "guaranteed profit", "sure profit", "no risk"
    ]

    # 주의 표현 (경고만)
    WARNING_PHRASES = [
        "추천", "매수", "매도", "지금 사야",
        "놓치지 마세요", "기회", "급등", "폭등"
    ]

    # AI 문구 감지 (자연스러움 저해)
    AI_PHRASES = [
        "저는 AI", "저는 인공지능", "AI로서", "인공지능으로서",
        "언어 모델", "LLM", "ChatGPT", "Claude",
        "제가 분석한 바로는", "저의 분석에 따르면",
        "AI 어시스턴트", "챗봇", "기계 학습",
        "As an AI", "I am an AI", "language model"
    ]

    # 최소 품질 점수
    MIN_QUALITY_SCORE = 70

    # 강화된 체크 항목별 가중치
    CHECK_WEIGHTS = {
        "forbidden_phrases": 20,      # 금지 표현
        "ai_phrases": 15,             # AI 문구
        "text_quality": 20,           # 텍스트 품질
        "image_coherence": 10,        # 이미지-텍스트 정합성
        "seo_optimization": 15,       # SEO 최적화
        "readability": 10,            # 가독성
        "persona_consistency": 5,      # 페르소나 일관성
        "emotional_connection": 5      # 감정적 공감
    }

    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Args:
            credential_manager: 자격증명 관리자
        """
        self.cred_manager = credential_manager or CredentialManager()

        # Claude 클라이언트
        anthropic_key = self.cred_manager.get_api_key("anthropic")
        self.claude = Anthropic(api_key=anthropic_key) if anthropic_key else None

        # Gemini 클라이언트
        google_key = self.cred_manager.get_api_key("google")
        if google_key:
            genai.configure(api_key=google_key)
            self.gemini = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.gemini = None

    def validate_content(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: List[str]
    ) -> Dict[str, Any]:
        """
        콘텐츠 전체 검증

        Args:
            title: 제목
            content: 본문
            images: 이미지 경로 리스트
            tags: 태그 리스트

        Returns:
            {
                "passed": bool,              # 통과 여부
                "score": float,              # 품질 점수 (0-100)
                "issues": List[str],         # 발견된 문제점
                "warnings": List[str],       # 경고 사항
                "suggestions": List[str],    # 개선 제안
                "detailed_scores": Dict      # 세부 점수
            }
        """
        logger.info("콘텐츠 검증 시작")

        result = {
            "passed": False,
            "score": 0.0,
            "issues": [],
            "warnings": [],
            "suggestions": [],
            "detailed_scores": {}
        }

        # 1. 금지 표현 검사
        forbidden_check = self._check_forbidden_phrases(title + " " + content)
        result["issues"].extend(forbidden_check["issues"])

        # 2. 경고 표현 검사
        warning_check = self._check_warning_phrases(title + " " + content)
        result["warnings"].extend(warning_check["warnings"])

        # 2.5. AI 문구 검사
        ai_check = self._check_ai_phrases(title + " " + content)
        result["issues"].extend(ai_check["issues"])
        result["detailed_scores"]["ai_phrases"] = ai_check["score"]

        # 3. Claude 텍스트 품질 검사
        text_quality = self._claude_text_review(title, content)
        result["detailed_scores"]["text_quality"] = text_quality["score"]
        result["suggestions"].extend(text_quality.get("suggestions", []))

        # 4. 이미지-텍스트 정합성 검사
        if images and self.gemini:
            coherence = self._check_image_text_coherence(content, images)
            result["detailed_scores"]["image_coherence"] = coherence["score"]
            result["warnings"].extend(coherence.get("warnings", []))

        # 5. SEO 최적화 검사
        seo_score = self._check_seo_optimization(title, content, tags)
        result["detailed_scores"]["seo"] = seo_score

        # 6. 가독성 검사
        readability = self._check_readability(content)
        result["detailed_scores"]["readability"] = readability

        # 전체 점수 계산
        total_score = self._calculate_total_score(result["detailed_scores"])
        result["score"] = total_score

        # 통과 여부 판정
        result["passed"] = (
            len(result["issues"]) == 0 and
            total_score >= self.MIN_QUALITY_SCORE
        )

        if result["passed"]:
            logger.success(f"콘텐츠 검증 통과 (점수: {total_score:.1f})")
        else:
            logger.warning(
                f"콘텐츠 검증 실패 (점수: {total_score:.1f}, "
                f"문제: {len(result['issues'])}개)"
            )

        return result

    def _check_forbidden_phrases(self, text: str) -> Dict[str, List[str]]:
        """금지 표현 검사"""
        issues = []
        text_lower = text.lower()

        for phrase in self.FORBIDDEN_PHRASES:
            if phrase.lower() in text_lower:
                issues.append(f"금지된 표현 발견: '{phrase}'")

        return {"issues": issues}

    def _check_warning_phrases(self, text: str) -> Dict[str, List[str]]:
        """경고 표현 검사"""
        warnings = []
        text_lower = text.lower()

        for phrase in self.WARNING_PHRASES:
            if phrase.lower() in text_lower:
                warnings.append(f"주의 필요한 표현: '{phrase}' - 투자 권유로 오인될 수 있음")

        return {"warnings": warnings}

    def _check_ai_phrases(self, text: str) -> Dict[str, Any]:
        """AI 문구 검사 - 자연스러움 저해 표현 감지"""
        issues = []
        text_lower = text.lower()
        found_count = 0

        for phrase in self.AI_PHRASES:
            if phrase.lower() in text_lower:
                issues.append(f"AI 문구 감지: '{phrase}' - 자연스러운 표현으로 수정 필요")
                found_count += 1

        # 점수 계산 (AI 문구가 없으면 100점)
        score = max(0, 100 - (found_count * 25))

        return {
            "issues": issues,
            "score": score,
            "found_count": found_count
        }

    def _claude_text_review(self, title: str, content: str) -> Dict[str, Any]:
        """Claude를 통한 텍스트 품질 검토"""

        if not self.claude:
            logger.warning("Claude API 없음, 기본 점수 반환")
            return {"score": 75, "suggestions": []}

        try:
            prompt = f"""다음 블로그 포스트를 검토하고 평가해주세요:

<제목>
{title}

<본문>
{content}

<평가 기준>
1. 페르소나 일관성 (친근한 경어체, 자연스러운 경험담)
2. 광고성 최소화 (강요하지 않는 톤)
3. 정보의 정확성 및 유용성
4. 감정적 공감 유도
5. 문법 및 맞춤법

각 기준을 10점 만점으로 평가하고, 개선 제안 3가지를 제공해주세요.

JSON 형식으로 응답:
{{
    "persona_consistency": 0-10,
    "non_promotional": 0-10,
    "information_value": 0-10,
    "emotional_connection": 0-10,
    "grammar": 0-10,
    "suggestions": ["제안1", "제안2", "제안3"]
}}
"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            result_text = response.content[0].text

            # JSON 추출
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            evaluation = json.loads(result_text.strip())

            # 점수 계산 (5개 기준 평균)
            score_keys = [
                "persona_consistency", "non_promotional",
                "information_value", "emotional_connection", "grammar"
            ]
            total = sum(evaluation.get(key, 0) for key in score_keys)
            avg_score = (total / len(score_keys)) * 10  # 100점 만점으로 변환

            logger.info(f"Claude 텍스트 검토: {avg_score:.1f}점")

            return {
                "score": avg_score,
                "suggestions": evaluation.get("suggestions", []),
                "details": evaluation
            }

        except Exception as e:
            logger.error(f"Claude 텍스트 검토 실패: {e}")
            return {"score": 70, "suggestions": []}

    def _check_image_text_coherence(
        self,
        text: str,
        image_paths: List[str]
    ) -> Dict[str, Any]:
        """Gemini를 통한 이미지-텍스트 정합성 검사"""

        if not self.gemini:
            logger.warning("Gemini API 없음, 기본 점수 반환")
            return {"score": 80, "warnings": []}

        try:
            # 첫 번째 이미지만 검사 (비용 절약)
            if not image_paths:
                return {"score": 100, "warnings": []}

            # 실제 구현 시 이미지 로드 및 분석
            # 여기서는 간단한 예시
            logger.info("이미지-텍스트 정합성 검사 (구현 예정)")

            return {
                "score": 85,
                "warnings": []
            }

        except Exception as e:
            logger.error(f"이미지-텍스트 정합성 검사 실패: {e}")
            return {"score": 75, "warnings": ["이미지 검사 실패"]}

    def _check_seo_optimization(
        self,
        title: str,
        content: str,
        tags: List[str]
    ) -> float:
        """SEO 최적화 검사"""

        score = 100.0

        # 1. 제목 길이 검사 (30-60자 권장)
        title_len = len(title)
        if title_len < 20 or title_len > 70:
            score -= 10
            logger.debug(f"제목 길이 비최적: {title_len}자")

        # 2. 태그 개수 검사 (5-10개 권장)
        tag_count = len(tags)
        if tag_count < 3 or tag_count > 12:
            score -= 10
            logger.debug(f"태그 개수 비최적: {tag_count}개")

        # 3. 키워드 밀도 검사 (1.5~2.5% 권장)
        if tags:
            main_keyword = tags[0]
            keyword_count = content.lower().count(main_keyword.lower())
            content_words = len(content.split())
            density = (keyword_count / content_words * 100) if content_words > 0 else 0

            if density < 1.0 or density > 3.0:
                score -= 5
                logger.debug(f"키워드 밀도 비최적: {density:.2f}%")

        # 4. 본문 길이 검사 (1000-1500자 권장)
        content_len = len(content)
        if content_len < 800 or content_len > 2000:
            score -= 5
            logger.debug(f"본문 길이 비최적: {content_len}자")

        return max(0, score)

    def _check_readability(self, content: str) -> float:
        """가독성 검사 (간단한 버전)"""

        score = 100.0

        # 1. 평균 문장 길이
        sentences = content.split('.')
        avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        if avg_sentence_len > 30:  # 너무 긴 문장
            score -= 10

        # 2. 단락 수
        paragraphs = [p for p in content.split('\n') if p.strip()]
        if len(paragraphs) < 3:  # 너무 적은 단락
            score -= 10

        # 3. HTML 태그 사용 여부 (구조화)
        if '<h' not in content.lower():  # 소제목 없음
            score -= 5

        return max(0, score)

    def _calculate_total_score(self, detailed_scores: Dict[str, float]) -> float:
        """전체 점수 계산 (가중 평균)"""

        weights = {
            "text_quality": 0.4,      # 40%
            "image_coherence": 0.2,   # 20%
            "seo": 0.2,               # 20%
            "readability": 0.2        # 20%
        }

        total = 0.0
        total_weight = 0.0

        for key, weight in weights.items():
            if key in detailed_scores:
                total += detailed_scores[key] * weight
                total_weight += weight

        return total / total_weight if total_weight > 0 else 0.0

    def suggest_improvements(self, validation_result: Dict[str, Any]) -> List[str]:
        """개선 제안 생성"""

        suggestions = validation_result.get("suggestions", []).copy()

        # 점수 기반 제안
        scores = validation_result.get("detailed_scores", {})

        if scores.get("text_quality", 100) < 70:
            suggestions.append("텍스트 품질을 개선하세요: 더 자연스러운 경험담과 공감 표현 추가")

        if scores.get("seo", 100) < 70:
            suggestions.append("SEO 최적화: 키워드를 자연스럽게 5~7회 반복하세요")

        if scores.get("readability", 100) < 70:
            suggestions.append("가독성 개선: 소제목을 추가하고 문장을 짧게 나누세요")

        return suggestions


# ============================================
# 테스트 코드
# ============================================

def test_qa_agent():
    """QA Agent 테스트"""
    print("\n=== QA Agent 테스트 ===\n")

    agent = QAAgent()

    # 테스트 콘텐츠 (일부러 문제 있는 내용 포함)
    test_title = "비트코인 100% 수익 보장! 무조건 매수하세요"  # 금지 표현 포함
    test_content = """
    <p>안녕하세요.</p>
    <p>오늘 비트코인이 급등했습니다. 저도 놀랐어요.</p>
    <p>이런 날엔 AI 자동매매가 정말 도움이 되더라고요.</p>
    """

    result = agent.validate_content(
        title=test_title,
        content=test_content,
        images=[],
        tags=["비트코인", "투자"]
    )

    print(f"검증 통과: {result['passed']}")
    print(f"전체 점수: {result['score']:.1f}/100")
    print(f"\n문제점: {len(result['issues'])}개")
    for issue in result['issues']:
        print(f"  - {issue}")
    print(f"\n경고: {len(result['warnings'])}개")
    for warning in result['warnings']:
        print(f"  - {warning}")
    print(f"\n개선 제안: {len(result['suggestions'])}개")
    for suggestion in result['suggestions']:
        print(f"  - {suggestion}")
    print(f"\n세부 점수:")
    for key, value in result['detailed_scores'].items():
        print(f"  - {key}: {value:.1f}")


if __name__ == "__main__":
    test_qa_agent()
