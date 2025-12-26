"""
메인 오케스트레이터
- 전체 파이프라인 제어
- Research → Content → Visual → QA → Upload
- 에러 핸들링 및 로깅
"""

import asyncio
import argparse
from datetime import datetime
from loguru import logger

from config import settings
from security.credential_manager import CredentialManager
from agents.research_agent import ResearchAgent
from agents.content_agent import ContentAgent
from agents.visual_agent import VisualAgent
from agents.qa_agent import QAAgent
from agents.upload_agent import UploadAgent
from models.database import DatabaseManager, DBSession


class BlogAutomationOrchestrator:
    """블로그 자동화 메인 오케스트레이터"""

    def __init__(
        self,
        naver_id: str,
        test_mode: bool = False
    ):
        """
        Args:
            naver_id: 네이버 ID
            test_mode: 테스트 모드 (실제 업로드 안 함)
        """
        self.naver_id = naver_id
        self.test_mode = test_mode or settings.TEST_MODE

        # 공통 자격증명 관리자
        self.cred_manager = CredentialManager()

        # 에이전트 초기화
        self.research_agent = ResearchAgent(self.cred_manager)
        self.content_agent = ContentAgent(self.cred_manager)
        self.visual_agent = VisualAgent(self.cred_manager)
        self.qa_agent = QAAgent(self.cred_manager)
        self.upload_agent = UploadAgent(
            self.cred_manager,
            headless=settings.HEADLESS
        )

        # 데이터베이스
        self.db = DatabaseManager(settings.DATABASE_URL)
        self.db.create_tables()

        logger.info(f"오케스트레이터 초기화 완료 (테스트 모드: {self.test_mode})")

    async def run_pipeline(self) -> dict:
        """
        전체 파이프라인 실행

        Returns:
            실행 결과 딕셔너리
        """
        logger.info("=" * 60)
        logger.info("블로그 자동화 파이프라인 시작")
        logger.info("=" * 60)

        result = {
            "success": False,
            "post_url": "",
            "error": None,
            "steps": {}
        }

        try:
            # Step 1: Research (뉴스 수집 및 분석)
            logger.info("\n[Step 1/5] Research: 트렌딩 토픽 수집")
            research_data = await self.research_agent.get_trending_topic()
            result["steps"]["research"] = research_data

            # 데이터베이스에 저장
            with DBSession(self.db) as session:
                news = self.db.create_news(
                    session,
                    topic=research_data["topic"],
                    summary=research_data["summary"],
                    sentiment=research_data["sentiment"],
                    sentiment_score=research_data["sentiment_score"],
                    keywords=research_data.get("keywords", []),
                    source_urls=research_data.get("source_urls", [])
                )
                news_id = news.id

            logger.success(f"✓ Research 완료: {research_data['topic'][:50]}...")

            # Step 2: Content Generation (블로그 포스트 생성)
            logger.info("\n[Step 2/5] Content: 블로그 포스트 생성 (Haiku - 비용 최적화)")
            content_data = self.content_agent.generate_post(
                research_data=research_data,
                target_length=1200,
                include_ai_promo=True,
                use_cache=True,
                model="haiku"  # Haiku 사용으로 80% 비용 절감!
            )
            result["steps"]["content"] = content_data

            logger.success(f"✓ Content 완료: {content_data['title'][:50]}...")

            # Step 3: Visual Generation (이미지 생성)
            logger.info("\n[Step 3/5] Visual: 이미지 생성")
            visual_data = self.visual_agent.generate_images(
                post_title=content_data["title"],
                post_content=content_data["content"],
                sentiment=research_data["sentiment"]
            )
            result["steps"]["visual"] = visual_data

            # 이미지 경로 리스트
            all_images = []
            for img_type, paths in visual_data.items():
                all_images.extend(paths)

            logger.success(f"✓ Visual 완료: {len(all_images)}개 이미지 생성")

            # Step 4: QA (품질 검증)
            logger.info("\n[Step 4/5] QA: 콘텐츠 품질 검증")
            qa_result = self.qa_agent.validate_content(
                title=content_data["title"],
                content=content_data["content"],
                images=all_images,
                tags=content_data["tags"]
            )
            result["steps"]["qa"] = qa_result

            logger.info(f"QA 점수: {qa_result['score']:.1f}/100")
            logger.info(f"통과 여부: {'✓ 통과' if qa_result['passed'] else '✗ 실패'}")

            # QA 실패 시 처리
            if not qa_result["passed"]:
                logger.warning("QA 검증 실패!")
                logger.warning(f"문제점: {qa_result['issues']}")

                # 개선 시도 (1회)
                if qa_result["suggestions"]:
                    logger.info("콘텐츠 개선 시도...")
                    feedback = "\n".join(qa_result["suggestions"])
                    content_data["content"] = self.content_agent.refine_content(
                        content_data["content"],
                        feedback
                    )

                    # 재검증
                    qa_result = self.qa_agent.validate_content(
                        title=content_data["title"],
                        content=content_data["content"],
                        images=all_images,
                        tags=content_data["tags"]
                    )

                    if not qa_result["passed"]:
                        raise Exception(f"QA 검증 실패: {qa_result['issues']}")

            logger.success(f"✓ QA 완료: {qa_result['score']:.1f}점")

            # 데이터베이스에 포스트 저장
            with DBSession(self.db) as session:
                post = self.db.create_post(
                    session,
                    news_id=news_id,
                    title=content_data["title"],
                    content=content_data["content"],
                    images=[{"path": img} for img in all_images],
                    tags=content_data["tags"],
                    category=settings.BLOG_CATEGORY,
                    status="pending_upload",
                    quality_score=qa_result["score"],
                    qa_passed=qa_result["passed"],
                    qa_issues=qa_result.get("issues", []),
                    qa_warnings=qa_result.get("warnings", [])
                )
                post_id = post.id

            # Step 5: Upload (네이버 블로그 업로드)
            if self.test_mode:
                logger.warning("\n[Step 5/5] Upload: 테스트 모드 - 업로드 건너뛰기")
                upload_result = {
                    "success": True,
                    "post_url": "https://blog.naver.com/test/123 (테스트 모드)",
                    "error": "",
                    "attempts": 0
                }
            else:
                logger.info("\n[Step 5/5] Upload: 네이버 블로그 업로드")
                upload_result = await self.upload_agent.upload_post(
                    title=content_data["title"],
                    content=content_data["content"],
                    images=all_images,
                    tags=content_data["tags"],
                    naver_id=self.naver_id,
                    category=settings.BLOG_CATEGORY
                )

            result["steps"]["upload"] = upload_result

            if upload_result["success"]:
                logger.success(f"✓ Upload 완료: {upload_result['post_url']}")

                # 데이터베이스 업데이트
                with DBSession(self.db) as session:
                    self.db.update_post_status(
                        session,
                        post_id=post_id,
                        status="published",
                        naver_post_url=upload_result["post_url"]
                    )
                    self.db.update_account_last_post(session, self.naver_id)

                result["success"] = True
                result["post_url"] = upload_result["post_url"]
            else:
                raise Exception(f"업로드 실패: {upload_result['error']}")

        except Exception as e:
            logger.error(f"파이프라인 실패: {e}")
            result["error"] = str(e)
            result["success"] = False

        # 최종 결과
        logger.info("\n" + "=" * 60)
        if result["success"]:
            logger.success("✅ 파이프라인 완료!")
            logger.info(f"포스트 URL: {result['post_url']}")
        else:
            logger.error("❌ 파이프라인 실패!")
            logger.error(f"오류: {result['error']}")
        logger.info("=" * 60 + "\n")

        return result


# ============================================
# CLI 인터페이스
# ============================================

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="AI 기반 네이버 블로그 자동화 시스템"
    )
    parser.add_argument(
        "--naver-id",
        type=str,
        help="네이버 ID (환경 변수에서 로드 가능)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 (업로드 안 함)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="1회만 실행 (스케줄러 없음)"
    )

    args = parser.parse_args()

    # 네이버 ID 확인
    naver_id = args.naver_id or input("네이버 ID: ").strip()

    if not naver_id:
        logger.error("네이버 ID가 필요합니다")
        return

    # 오케스트레이터 생성
    orchestrator = BlogAutomationOrchestrator(
        naver_id=naver_id,
        test_mode=args.test
    )

    # 실행
    if args.once:
        # 1회 실행
        await orchestrator.run_pipeline()
    else:
        # 스케줄러 (추후 구현)
        logger.info("스케줄러 모드는 아직 구현 중입니다")
        logger.info("1회 실행을 위해 --once 옵션을 사용하세요")


if __name__ == "__main__":
    asyncio.run(main())
