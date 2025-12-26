"""
블로그 포스팅 통합 파이프라인 v2
- Perplexity: 실시간 리서치
- Claude Haiku/Sonnet: 글 작성 + 이미지 프롬프트 생성
- Gemini Imagen: 이미지 생성
- Playwright: 네이버 블로그 발행
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from loguru import logger

from agents.marketing_content import MarketingContentGenerator
from agents.content_agent import ContentAgent
from agents.blog_content_generator import BlogContentGenerator
from utils.gemini_image import GeminiImageGenerator
from auto_post import NaverBlogPoster


class BlogPostPipeline:
    """
    통합 블로그 포스팅 파이프라인

    사용 예시:
        pipeline = BlogPostPipeline(naver_id="your_id")

        # 마케팅 콘텐츠 발행
        result = await pipeline.run_marketing(
            template_type="trading_mistake",
            keyword="거래량 매매"
        )

        # 뉴스 기반 콘텐츠 발행
        result = await pipeline.run_news(
            research_data={"topic": "비트코인 상승", ...}
        )
    """

    def __init__(
        self,
        naver_id: str,
        model: str = "haiku",  # "haiku" 또는 "sonnet"
        output_dir: str = "./generated_images"
    ):
        """
        Args:
            naver_id: 네이버 계정 ID
            model: 글쓰기 모델 ("haiku"=빠르고 저렴, "sonnet"=고품질)
            output_dir: 이미지 저장 디렉토리
        """
        self.naver_id = naver_id
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 에이전트 초기화
        self.marketing_generator = MarketingContentGenerator()
        self.content_agent = ContentAgent()
        self.blog_generator = BlogContentGenerator()  # 다목적 콘텐츠 생성기
        self.image_generator = None
        self.poster = None

        self._init_image_generator()

    def _init_image_generator(self):
        """이미지 생성기 초기화 (lazy loading)"""
        try:
            self.image_generator = GeminiImageGenerator()
            logger.info("Imagen 4.0 이미지 생성기 초기화 완료")
        except Exception as e:
            logger.warning(f"이미지 생성기 초기화 실패: {e}")
            self.image_generator = None

    async def run_marketing(
        self,
        template_type: Optional[str] = None,
        keyword: Optional[str] = None,
        generate_image: bool = True,
        num_images: int = 4,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        마케팅 콘텐츠 파이프라인 실행

        Args:
            template_type: 템플릿 유형
                - "trading_mistake": 매매 실수/함정
                - "market_analysis": 시장 분석
                - "investment_tip": 투자 팁
                - "psychology": 투자 심리
            keyword: 주제 키워드 (없으면 랜덤)
            generate_image: 이미지 생성 여부
            num_images: 생성할 이미지 개수 (기본 4개)
            dry_run: True면 발행 없이 미리보기만

        Returns:
            {
                "success": bool,
                "title": str,
                "content": str,
                "images": list,
                "url": str or None (발행 시)
            }
        """
        logger.info("=" * 50)
        logger.info("📝 마케팅 콘텐츠 파이프라인 시작")
        logger.info("=" * 50)

        # 1단계: 콘텐츠 생성
        logger.info("1️⃣ 콘텐츠 생성 중...")
        content = self.marketing_generator.generate_content(
            template_type=template_type,
            keyword=keyword,
            min_length=2000,
            max_length=3000,
            model="sonnet" if self.model == "sonnet" else "haiku"
        )

        logger.success(f"   제목: {content['title']}")
        logger.success(f"   글자 수: {len(content['content'])}자")

        # 2단계: 이미지 프롬프트 생성 (Claude)
        images = []
        if generate_image and self.content_agent.claude:
            logger.info("2️⃣ 이미지 프롬프트 생성 중...")
            image_prompts = self._generate_image_prompt_for_marketing(
                content['template'],
                content['keyword'],
                content['content']
            )

            # 3단계: 다중 이미지 생성 (Imagen)
            if self.image_generator and image_prompts:
                logger.info(f"3️⃣ 이미지 {num_images}개 생성 중...")
                # 썸네일 + 본문 이미지 프롬프트 모음
                all_prompts = [image_prompts.get('thumbnail_prompt', '')]
                all_prompts.extend(image_prompts.get('content_prompts', []))
                images = self._generate_multiple_images(all_prompts, num_images)

        # 폴백: 기존 이미지 사용
        if not images:
            latest = self._get_latest_image()
            if latest:
                images = [latest]

        logger.info(f"   생성된 이미지: {len(images)}개")

        # 4단계: 발행 또는 미리보기
        if dry_run:
            logger.info("4️⃣ DRY RUN 모드 - 발행 스킵")
            return self._dry_run_result(content, images[0] if images else None)

        logger.info("4️⃣ 네이버 블로그 발행 중...")
        return await self._publish(content, images=images)

    async def run_research(
        self,
        topic_category: Optional[str] = None,
        style: Optional[str] = None,
        generate_image: bool = True,
        num_images: int = 4,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Perplexity 리서치 기반 콘텐츠 파이프라인 (권장)

        Args:
            topic_category: 주제 카테고리
                - "us_stock": 미국주식
                - "kr_stock": 국내주식
                - "crypto": 암호화폐
                - "ai_tech": AI/기술
                - "economy": 경제
                - "hot_issue": 핫이슈
            style: 글쓰기 스타일 (분석형, 스토리텔링, 뉴스해설, 전망형, 교육형)
            generate_image: 이미지 생성 여부
            num_images: 생성할 이미지 개수 (기본 4개)
            dry_run: True면 발행 없이 미리보기만

        Returns:
            {
                "success": bool,
                "title": str,
                "content": str,
                "images": list,
                "research": Dict,  # Perplexity 리서치 데이터
                "url": str or None
            }
        """
        logger.info("=" * 50)
        logger.info("🔍 Perplexity 리서치 기반 파이프라인 시작")
        logger.info("=" * 50)

        # 1단계: Perplexity 리서치 + 콘텐츠 생성
        logger.info("1️⃣ 리서치 및 콘텐츠 생성 중...")
        result = await self.blog_generator.generate_with_research(
            topic_category=topic_category,
            style=style,
            model=self.model
        )

        logger.success(f"   제목: {result['title']}")
        logger.success(f"   글자 수: {len(result['content'])}자")
        logger.success(f"   리서치 주제: {result.get('research', {}).get('topic', 'N/A')}")

        # 2단계: 다중 이미지 생성
        images = []
        if generate_image and self.image_generator:
            logger.info(f"2️⃣ 이미지 {num_images}개 생성 중 (Gemini Imagen)...")
            image_prompt = result.get('image_prompt', '')

            # 주제 기반으로 다양한 프롬프트 생성
            topic_name = result.get('research', {}).get('topic', 'investment')
            base_prompts = [
                image_prompt,
                f"Professional {topic_name} analysis visualization, data charts, modern design, no text",
                f"Success and growth concept for {topic_name}, upward trends, golden colors, no text",
                f"Technology and AI automation for {topic_name}, futuristic design, blue gradients, no text"
            ]
            images = self._generate_multiple_images(base_prompts, num_images)

        if not images:
            latest = self._get_latest_image()
            if latest:
                images = [latest]

        logger.info(f"   생성된 이미지: {len(images)}개")

        # 3단계: 발행 또는 미리보기
        content = {
            "title": result['title'],
            "content": result['content'],
            "tags": result.get('tags', [])
        }

        if dry_run:
            logger.info("3️⃣ DRY RUN 모드 - 발행 스킵")
            dry_result = self._dry_run_result(content, images[0] if images else None)
            dry_result['research'] = result.get('research', {})
            dry_result['images'] = images
            return dry_result

        logger.info("3️⃣ 네이버 블로그 발행 중...")
        publish_result = await self._publish(content, images=images)
        publish_result['research'] = result.get('research', {})
        return publish_result

    async def run_news(
        self,
        research_data: Dict[str, Any],
        generate_image: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        뉴스/리서치 기반 콘텐츠 파이프라인 실행

        Args:
            research_data: Research Agent 출력
                {
                    "topic": str,
                    "summary": str,
                    "sentiment": str,
                    "keywords": List[str]
                }
            generate_image: 이미지 생성 여부
            dry_run: True면 발행 없이 미리보기만

        Returns:
            {
                "success": bool,
                "title": str,
                "content": str,
                "image_path": str or None,
                "url": str or None
            }
        """
        logger.info("=" * 50)
        logger.info("📰 뉴스 기반 콘텐츠 파이프라인 시작")
        logger.info("=" * 50)

        # 1단계: 포스트 + 이미지 프롬프트 생성
        logger.info("1️⃣ 포스트 생성 중 (Claude Haiku)...")
        post_result = self.content_agent.generate_post_with_images(
            research_data=research_data,
            target_length=1200,
            include_ai_promo=True,
            num_images=1
        )

        logger.success(f"   제목: {post_result['title']}")
        logger.success(f"   글자 수: {len(post_result['content'])}자")

        # 2단계: 이미지 생성
        image_path = None
        if generate_image and self.image_generator:
            logger.info("2️⃣ 이미지 생성 중 (Imagen 4.0)...")
            image_prompts = post_result.get('image_prompts', {})
            thumbnail_prompt = image_prompts.get('thumbnail_prompt', '')

            if thumbnail_prompt:
                image_path = self._generate_image(thumbnail_prompt)

        # 폴백: 기존 이미지 사용
        if not image_path:
            image_path = self._get_latest_image()

        # 3단계: 발행 또는 미리보기
        content = {
            "title": post_result['title'],
            "content": post_result['content'],
            "tags": post_result['tags']
        }

        if dry_run:
            logger.info("3️⃣ DRY RUN 모드 - 발행 스킵")
            return self._dry_run_result(content, image_path)

        logger.info("3️⃣ 네이버 블로그 발행 중...")
        return await self._publish(content, image_path)

    def _generate_image_prompt_for_marketing(
        self,
        template_type: str,
        keyword: str,
        content: str
    ) -> Optional[Dict[str, str]]:
        """마케팅 콘텐츠용 이미지 프롬프트 생성"""

        # 템플릿별 기본 프롬프트
        template_prompts = {
            "trading_mistake": f"Warning concept for {keyword} trading mistake, red alert signs with caution symbols, professional financial illustration, stock market crash visualization, no text",
            "market_analysis": f"Professional {keyword} market analysis dashboard, financial charts and data visualization, blue and green corporate colors, modern fintech design, no text",
            "investment_tip": f"Investment success and {keyword} concept, golden coins with upward arrows, wealth growth visualization, professional financial art, no text",
            "psychology": f"Trading psychology and {keyword} mental concept, brain visualization with market charts, calm blue meditation colors, mindfulness illustration, no text"
        }

        base_prompt = template_prompts.get(
            template_type,
            f"Professional investment concept for {keyword}, modern financial illustration, no text"
        )

        # Claude로 프롬프트 개선 시도
        if self.content_agent.claude:
            try:
                improved = self.content_agent.generate_image_prompts(
                    post_title=keyword,
                    post_content=content[:500],
                    keywords=[keyword],
                    sentiment="neutral",
                    num_images=1
                )
                if improved.get('thumbnail_prompt'):
                    return improved
            except Exception as e:
                logger.debug(f"프롬프트 개선 실패, 기본 사용: {e}")

        return {"thumbnail_prompt": base_prompt, "content_prompts": [], "style_guide": ""}

    def _generate_image(self, prompt: str) -> Optional[str]:
        """Imagen으로 이미지 생성"""
        if not self.image_generator:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"blog_{timestamp}.png"

            path = self.image_generator.generate_image(
                prompt=prompt,
                filename=filename,
                style="digital-art"
            )

            if path:
                logger.success(f"   이미지 생성 완료: {path}")
                return path

        except Exception as e:
            logger.error(f"   이미지 생성 실패: {e}")

        return None

    def _generate_multiple_images(self, prompts: list, num_images: int = 4) -> list:
        """
        여러 이미지 생성 (본문 삽입용)

        Args:
            prompts: 이미지 프롬프트 리스트
            num_images: 생성할 이미지 개수 (기본 4개)

        Returns:
            생성된 이미지 경로 리스트
        """
        if not self.image_generator:
            return []

        images = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 프롬프트가 부족하면 기본 프롬프트로 보충
        base_prompts = [
            "Professional cryptocurrency trading concept, digital finance visualization, blue gradient, modern design, no text",
            "Investment success and wealth growth, golden coins with upward arrows, professional financial art, no text",
            "AI technology and automation concept, futuristic digital art, circuit patterns, blue and purple colors, no text",
            "Data analysis dashboard, financial charts and graphs, modern fintech design, clean interface, no text"
        ]

        # 프롬프트 리스트 확장
        all_prompts = list(prompts) if prompts else []
        while len(all_prompts) < num_images:
            all_prompts.append(base_prompts[len(all_prompts) % len(base_prompts)])

        for i in range(min(num_images, len(all_prompts))):
            try:
                filename = f"blog_{timestamp}_{i+1}.png"
                path = self.image_generator.generate_image(
                    prompt=all_prompts[i],
                    filename=filename,
                    style="digital-art"
                )

                if path:
                    images.append(path)
                    logger.success(f"   이미지 {i+1}/{num_images} 생성 완료")
                else:
                    logger.warning(f"   이미지 {i+1}/{num_images} 생성 실패")

            except Exception as e:
                logger.error(f"   이미지 {i+1} 생성 오류: {e}")

        return images

    def _get_latest_image(self) -> Optional[str]:
        """최신 생성 이미지 가져오기 (폴백)"""
        try:
            images = list(self.output_dir.glob("*.png"))
            if images:
                latest = max(images, key=lambda x: x.stat().st_mtime)
                logger.info(f"   기존 이미지 사용: {latest.name}")
                return str(latest)
        except Exception:
            pass
        return None

    async def _publish(
        self,
        content: Dict[str, Any],
        image_path: Optional[str] = None,
        images: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        네이버 블로그 발행

        Args:
            content: 콘텐츠 딕셔너리
            image_path: 단일 이미지 경로 (하위 호환)
            images: 다중 이미지 경로 리스트
        """
        try:
            if not self.poster:
                self.poster = NaverBlogPoster(self.naver_id)

            # 다중 이미지 우선, 없으면 단일 이미지
            result = await self.poster.post(
                title=content['title'],
                content=content['content'],
                image_path=image_path,
                images=images
            )

            if result.get('success'):
                logger.success(f"✅ 발행 완료: {result.get('url', '')}")
                return {
                    "success": True,
                    "title": content['title'],
                    "content": content['content'],
                    "images": images or ([image_path] if image_path else []),
                    "url": result.get('url')
                }
            else:
                logger.error(f"❌ 발행 실패: {result.get('error', '')}")
                return {
                    "success": False,
                    "title": content['title'],
                    "content": content['content'],
                    "images": images or ([image_path] if image_path else []),
                    "error": result.get('error')
                }

        except Exception as e:
            logger.error(f"❌ 발행 오류: {e}")
            return {
                "success": False,
                "title": content['title'],
                "content": content['content'],
                "images": images or ([image_path] if image_path else []),
                "error": str(e)
            }

    def _dry_run_result(
        self,
        content: Dict[str, Any],
        image_path: Optional[str]
    ) -> Dict[str, Any]:
        """Dry run 결과 반환"""
        print("\n" + "=" * 60)
        print("📋 DRY RUN 결과")
        print("=" * 60)
        print(f"제목: {content['title']}")
        print(f"글자 수: {len(content['content'])}자")
        print(f"이미지: {image_path or '없음'}")
        print("-" * 60)
        print(content['content'][:500] + "...")
        print("=" * 60)

        return {
            "success": True,
            "dry_run": True,
            "title": content['title'],
            "content": content['content'],
            "image_path": image_path
        }

    def list_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록"""
        return self.marketing_generator.get_available_templates()

    def list_keywords(self, template_type: str) -> List[str]:
        """템플릿별 키워드 목록"""
        return self.marketing_generator.get_keywords_for_template(template_type)


# ============================================
# CLI 실행
# ============================================

async def main():
    """CLI 메인 함수"""
    import sys

    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print("""
블로그 포스팅 통합 파이프라인 v2

사용법:
  python pipeline.py [모드] [옵션]

모드:
  research [카테고리] [스타일]  🔥 Perplexity 실시간 리서치 기반 (권장)
  marketing [템플릿] [키워드]   마케팅 콘텐츠 생성/발행
  news                         뉴스 기반 콘텐츠 (테스트 데이터)
  templates                    사용 가능한 템플릿 목록
  categories                   리서치 카테고리 목록

옵션:
  --dry                        발행 없이 미리보기만
  --no-image                   이미지 생성 스킵

카테고리 (research 모드):
  us_stock   - 미국주식
  kr_stock   - 국내주식
  crypto     - 암호화폐
  ai_tech    - AI/기술
  economy    - 경제
  hot_issue  - 핫이슈

스타일:
  분석형, 스토리텔링, 뉴스해설, 전망형, 교육형

예시:
  python pipeline.py research --dry                      # 🔥 랜덤 리서치 기반 (권장)
  python pipeline.py research crypto 분석형 --dry       # 암호화폐 분석형
  python pipeline.py research us_stock --dry            # 미국주식 랜덤 스타일
  python pipeline.py marketing --dry                    # 마케팅 콘텐츠
  python pipeline.py categories                         # 카테고리 목록
        """)
        return

    pipeline = BlogPostPipeline(naver_id="wncksdid0750", model="haiku")

    if args[0] == "templates":
        print("\n📚 사용 가능한 템플릿:\n")
        for template in pipeline.list_templates():
            keywords = pipeline.list_keywords(template)
            print(f"  {template}")
            print(f"    키워드: {', '.join(keywords[:4])}...")
        return

    if args[0] == "categories":
        print("\n📂 리서치 카테고리:\n")
        categories = pipeline.blog_generator.get_categories()
        for cat in categories:
            topic = pipeline.blog_generator.TOPICS.get(cat, {})
            print(f"  {topic.get('emoji', '')} {cat}: {topic.get('name', '')}")
            keywords = topic.get('keywords', [])[:4]
            print(f"      키워드: {', '.join(keywords)}...")
        return

    dry_run = "--dry" in args
    no_image = "--no-image" in args

    if args[0] == "research":
        # research [카테고리] [스타일] [--dry] [--no-image]
        valid_categories = ["us_stock", "kr_stock", "crypto", "ai_tech", "economy", "hot_issue"]
        valid_styles = ["분석형", "스토리텔링", "뉴스해설", "전망형", "교육형"]

        topic_category = None
        style = None

        for arg in args[1:]:
            if arg.startswith("--"):
                continue
            if topic_category is None and arg in valid_categories:
                topic_category = arg
            elif style is None and arg in valid_styles:
                style = arg

        await pipeline.run_research(
            topic_category=topic_category,
            style=style,
            generate_image=not no_image,
            dry_run=dry_run
        )

    elif args[0] == "marketing":
        # marketing [템플릿] [키워드] [--dry] [--no-image]
        template_type = None
        keyword = None

        for arg in args[1:]:
            if arg.startswith("--"):
                continue
            if template_type is None and arg in pipeline.list_templates():
                template_type = arg
            elif keyword is None:
                keyword = arg

        await pipeline.run_marketing(
            template_type=template_type,
            keyword=keyword,
            generate_image=not no_image,
            dry_run=dry_run
        )

    elif args[0] == "news":
        # 테스트용 뉴스 데이터
        test_research = {
            "topic": "비트코인 10만 달러 돌파, 역사적 신고가",
            "summary": "비트코인이 처음으로 10만 달러를 돌파하며 역사적인 순간을 맞이했습니다.",
            "sentiment": "positive",
            "keywords": ["비트코인", "10만달러", "신고가", "ETF", "기관투자"]
        }

        await pipeline.run_news(
            research_data=test_research,
            generate_image=not no_image,
            dry_run=dry_run
        )

    else:
        print(f"알 수 없는 명령: {args[0]}")
        print("--help로 도움말을 확인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
