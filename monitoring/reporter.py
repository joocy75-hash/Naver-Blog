"""
통계 리포트 시스템
- 일간/주간/월간 통계 생성
- 텔레그램 리포트 전송
- 성과 분석
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import DatabaseManager, DBSession, Post, Analytics


class StatisticsReporter:
    """통계 리포트 클래스"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Args:
            db: DatabaseManager 인스턴스 (None이면 자동 생성)
        """
        self.db = db or DatabaseManager()
        logger.info("StatisticsReporter 초기화")

    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        일간 리포트 생성

        Args:
            date: 대상 날짜 (None이면 오늘)

        Returns:
            일간 통계 데이터
        """
        target_date = date or datetime.now()
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        try:
            with DBSession(self.db) as session:
                # 해당 날짜 포스트 조회
                posts = session.query(Post).filter(
                    Post.created_at >= start_of_day,
                    Post.created_at < end_of_day
                ).all()

                # 상태별 분류
                published = [p for p in posts if p.status == "published"]
                failed = [p for p in posts if p.status == "failed"]
                draft = [p for p in posts if p.status == "draft"]

                # 카테고리별 분류
                categories = {}
                for post in published:
                    cat = post.category or "미분류"
                    categories[cat] = categories.get(cat, 0) + 1

                # 품질 점수 통계
                quality_scores = [p.quality_score for p in posts if p.quality_score]
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

                # 조회수 통계 (발행된 포스트)
                total_views = 0
                for post in published:
                    if post.analytics:
                        total_views += post.analytics.views or 0

                return {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "summary": {
                        "total_posts": len(posts),
                        "published": len(published),
                        "failed": len(failed),
                        "draft": len(draft),
                        "success_rate": f"{len(published)/len(posts)*100:.1f}%" if posts else "N/A"
                    },
                    "categories": categories,
                    "quality": {
                        "average_score": round(avg_quality, 1),
                        "min_score": min(quality_scores) if quality_scores else 0,
                        "max_score": max(quality_scores) if quality_scores else 0
                    },
                    "views": {
                        "total": total_views,
                        "average_per_post": round(total_views / len(published), 1) if published else 0
                    },
                    "top_posts": self._get_top_posts(published, limit=3)
                }

        except Exception as e:
            logger.error(f"일간 리포트 생성 실패: {e}")
            return {"error": str(e)}

    def generate_weekly_report(self, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        주간 리포트 생성

        Args:
            end_date: 주 마지막 날짜 (None이면 오늘)

        Returns:
            주간 통계 데이터
        """
        target_date = end_date or datetime.now()
        start_of_week = target_date - timedelta(days=7)

        try:
            with DBSession(self.db) as session:
                posts = session.query(Post).filter(
                    Post.created_at >= start_of_week,
                    Post.created_at <= target_date
                ).all()

                published = [p for p in posts if p.status == "published"]

                # 요일별 통계
                daily_stats = {}
                for post in published:
                    day_name = post.created_at.strftime("%A")
                    daily_stats[day_name] = daily_stats.get(day_name, 0) + 1

                # 카테고리별 통계
                categories = {}
                for post in published:
                    cat = post.category or "미분류"
                    categories[cat] = categories.get(cat, 0) + 1

                # 조회수 통계
                total_views = 0
                for post in published:
                    if post.analytics:
                        total_views += post.analytics.views or 0

                return {
                    "period": f"{start_of_week.strftime('%Y-%m-%d')} ~ {target_date.strftime('%Y-%m-%d')}",
                    "summary": {
                        "total_posts": len(posts),
                        "published": len(published),
                        "average_per_day": round(len(published) / 7, 1),
                        "success_rate": f"{len(published)/len(posts)*100:.1f}%" if posts else "N/A"
                    },
                    "daily_distribution": daily_stats,
                    "categories": categories,
                    "views": {
                        "total": total_views,
                        "average_per_post": round(total_views / len(published), 1) if published else 0
                    },
                    "top_posts": self._get_top_posts(published, limit=5)
                }

        except Exception as e:
            logger.error(f"주간 리포트 생성 실패: {e}")
            return {"error": str(e)}

    def generate_monthly_report(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        월간 리포트 생성

        Args:
            year: 연도 (None이면 현재)
            month: 월 (None이면 현재)

        Returns:
            월간 통계 데이터
        """
        now = datetime.now()
        target_year = year or now.year
        target_month = month or now.month

        start_of_month = datetime(target_year, target_month, 1)
        if target_month == 12:
            end_of_month = datetime(target_year + 1, 1, 1)
        else:
            end_of_month = datetime(target_year, target_month + 1, 1)

        try:
            with DBSession(self.db) as session:
                posts = session.query(Post).filter(
                    Post.created_at >= start_of_month,
                    Post.created_at < end_of_month
                ).all()

                published = [p for p in posts if p.status == "published"]

                # 주별 통계
                weekly_stats = {}
                for post in published:
                    week_num = post.created_at.isocalendar()[1]
                    weekly_stats[f"Week {week_num}"] = weekly_stats.get(f"Week {week_num}", 0) + 1

                # 카테고리별 통계
                categories = {}
                for post in published:
                    cat = post.category or "미분류"
                    categories[cat] = categories.get(cat, 0) + 1

                # 품질 점수 트렌드
                quality_scores = [p.quality_score for p in posts if p.quality_score]

                # 조회수 통계
                total_views = 0
                for post in published:
                    if post.analytics:
                        total_views += post.analytics.views or 0

                return {
                    "period": f"{target_year}년 {target_month}월",
                    "summary": {
                        "total_posts": len(posts),
                        "published": len(published),
                        "average_per_week": round(len(published) / 4, 1),
                        "success_rate": f"{len(published)/len(posts)*100:.1f}%" if posts else "N/A"
                    },
                    "weekly_distribution": weekly_stats,
                    "categories": categories,
                    "quality": {
                        "average_score": round(sum(quality_scores)/len(quality_scores), 1) if quality_scores else 0
                    },
                    "views": {
                        "total": total_views,
                        "average_per_post": round(total_views / len(published), 1) if published else 0
                    },
                    "top_posts": self._get_top_posts(published, limit=10)
                }

        except Exception as e:
            logger.error(f"월간 리포트 생성 실패: {e}")
            return {"error": str(e)}

    def _get_top_posts(self, posts: List[Post], limit: int = 5) -> List[Dict[str, Any]]:
        """조회수 기준 상위 포스트"""
        posts_with_views = []
        for post in posts:
            views = post.analytics.views if post.analytics else 0
            posts_with_views.append((post, views))

        # 조회수 순 정렬
        sorted_posts = sorted(posts_with_views, key=lambda x: x[1], reverse=True)

        return [
            {
                "title": post.title[:50] + "..." if len(post.title) > 50 else post.title,
                "category": post.category,
                "views": views,
                "url": post.naver_post_url,
                "published_at": post.published_at.isoformat() if post.published_at else None
            }
            for post, views in sorted_posts[:limit]
        ]

    # ============================================
    # 텔레그램 포맷팅
    # ============================================

    def format_daily_for_telegram(self, report: Dict[str, Any]) -> str:
        """일간 리포트 텔레그램 포맷"""
        if "error" in report:
            return f"❌ 리포트 생성 실패: {report['error']}"

        summary = report.get("summary", {})
        quality = report.get("quality", {})
        views = report.get("views", {})

        text = f"📊 <b>일간 리포트</b> ({report['date']})\n\n"

        # 요약
        text += f"📝 포스팅: {summary.get('published', 0)}/{summary.get('total_posts', 0)}개\n"
        text += f"✅ 성공률: {summary.get('success_rate', 'N/A')}\n"
        text += f"⭐ 평균 품질: {quality.get('average_score', 0)}점\n"
        text += f"👁 총 조회수: {views.get('total', 0):,}회\n\n"

        # 카테고리
        categories = report.get("categories", {})
        if categories:
            text += "📁 <b>카테고리별</b>\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                text += f"  • {cat}: {count}개\n"

        # 상위 포스트
        top_posts = report.get("top_posts", [])
        if top_posts:
            text += "\n🏆 <b>인기 포스트</b>\n"
            for i, post in enumerate(top_posts[:3], 1):
                text += f"  {i}. {post['title']} ({post['views']}회)\n"

        return text

    def format_weekly_for_telegram(self, report: Dict[str, Any]) -> str:
        """주간 리포트 텔레그램 포맷"""
        if "error" in report:
            return f"❌ 리포트 생성 실패: {report['error']}"

        summary = report.get("summary", {})
        views = report.get("views", {})

        text = f"📈 <b>주간 리포트</b>\n{report['period']}\n\n"

        text += f"📝 총 포스팅: {summary.get('published', 0)}개\n"
        text += f"📅 일 평균: {summary.get('average_per_day', 0)}개\n"
        text += f"✅ 성공률: {summary.get('success_rate', 'N/A')}\n"
        text += f"👁 총 조회수: {views.get('total', 0):,}회\n\n"

        # 요일별 분포
        daily = report.get("daily_distribution", {})
        if daily:
            text += "📊 <b>요일별 포스팅</b>\n"
            for day, count in daily.items():
                bar = "█" * count + "░" * (5 - min(count, 5))
                text += f"  {day[:3]}: {bar} {count}\n"

        return text

    async def send_daily_report(self) -> bool:
        """일간 리포트 텔레그램 전송"""
        try:
            from utils.telegram_notifier import send_notification

            report = self.generate_daily_report()
            message = self.format_daily_for_telegram(report)

            await send_notification(message)
            logger.info("일간 리포트 전송 완료")
            return True

        except Exception as e:
            logger.error(f"일간 리포트 전송 실패: {e}")
            return False

    async def send_weekly_report(self) -> bool:
        """주간 리포트 텔레그램 전송"""
        try:
            from utils.telegram_notifier import send_notification

            report = self.generate_weekly_report()
            message = self.format_weekly_for_telegram(report)

            await send_notification(message)
            logger.info("주간 리포트 전송 완료")
            return True

        except Exception as e:
            logger.error(f"주간 리포트 전송 실패: {e}")
            return False


# ============================================
# 테스트 코드
# ============================================

def test_statistics_reporter():
    """StatisticsReporter 테스트"""
    print("\n=== StatisticsReporter 테스트 ===\n")

    reporter = StatisticsReporter()

    # 일간 리포트
    print("일간 리포트:")
    daily = reporter.generate_daily_report()
    print(f"  날짜: {daily.get('date')}")
    print(f"  요약: {daily.get('summary')}")

    # 텔레그램 포맷
    print("\n텔레그램 포맷:")
    telegram_text = reporter.format_daily_for_telegram(daily)
    print(telegram_text)

    print("\n테스트 완료!")


if __name__ == "__main__":
    test_statistics_reporter()
