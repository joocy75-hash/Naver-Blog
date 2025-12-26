"""
주제 카테고리 순환 관리
- 가중치 기반 카테고리 선택
- 최근 사용 카테고리 가중치 감소
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

# 프로젝트 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import DatabaseManager, DBSession, Post


class TopicRotator:
    """주제 카테고리 순환 관리"""

    # 카테고리 목록
    CATEGORIES = ["crypto", "us_stock", "kr_stock", "ai_tech", "economy", "hot_issue"]

    # 카테고리별 기본 가중치 (crypto에 더 높은 가중치)
    WEIGHTS = {
        "crypto": 4,
        "us_stock": 2,
        "kr_stock": 2,
        "ai_tech": 2,
        "economy": 1,
        "hot_issue": 1
    }

    # 카테고리 한글 매핑
    CATEGORY_NAMES = {
        "crypto": "암호화폐",
        "us_stock": "미국 주식",
        "kr_stock": "한국 주식",
        "ai_tech": "AI/기술",
        "economy": "경제",
        "hot_issue": "핫이슈"
    }

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Args:
            db: DatabaseManager 인스턴스 (None이면 자동 생성)
        """
        self.db = db or DatabaseManager()
        logger.info("TopicRotator 초기화")

    def get_next_category(self) -> str:
        """
        다음 포스팅 카테고리 결정
        - 가중치 기반 랜덤 선택
        - 최근 사용 카테고리 가중치 감소

        Returns:
            선택된 카테고리 코드
        """
        # 최근 24시간 사용된 카테고리 조회
        recent_categories = self._get_recent_categories(hours=24)

        # 각 카테고리별 조정된 가중치 계산
        adjusted_weights = {}

        for category in self.CATEGORIES:
            base_weight = self.WEIGHTS.get(category, 1)

            # 최근 사용 횟수에 따라 가중치 감소
            recent_count = recent_categories.count(category)

            # 감소 비율: 사용할 때마다 30% 감소 (최소 10%까지)
            reduction_factor = max(0.1, 1 - (recent_count * 0.3))
            adjusted_weight = base_weight * reduction_factor

            adjusted_weights[category] = adjusted_weight

        logger.debug(f"조정된 카테고리 가중치: {adjusted_weights}")

        # 가중치 기반 랜덤 선택
        categories = list(adjusted_weights.keys())
        weights = list(adjusted_weights.values())

        selected_category = random.choices(categories, weights=weights, k=1)[0]

        logger.info(
            f"다음 포스팅 카테고리 선택: {selected_category} "
            f"({self.CATEGORY_NAMES.get(selected_category, selected_category)})"
        )
        return selected_category

    def _get_recent_categories(self, hours: int = 24) -> List[str]:
        """
        최근 N시간 포스팅 카테고리 조회

        Args:
            hours: 조회 기간 (시간)

        Returns:
            카테고리 목록
        """
        recent_categories = []

        try:
            with DBSession(self.db) as session:
                # 최근 N시간 이내 발행된 포스트 조회
                cutoff_time = datetime.now() - timedelta(hours=hours)

                posts = session.query(Post).filter(
                    Post.published_at >= cutoff_time,
                    Post.status == 'published',
                    Post.category.isnot(None)
                ).all()

                recent_categories = [post.category for post in posts if post.category]

                logger.debug(f"최근 {hours}시간 포스팅 카테고리: {recent_categories}")

        except Exception as e:
            logger.warning(f"최근 카테고리 조회 실패: {e}")

        return recent_categories

    def get_category_stats(self) -> Dict[str, Any]:
        """
        카테고리별 통계 조회

        Returns:
            카테고리별 포스팅 수, 마지막 포스팅 시간 등
        """
        stats = {}

        try:
            with DBSession(self.db) as session:
                for category in self.CATEGORIES:
                    posts = session.query(Post).filter(
                        Post.category == category,
                        Post.status == 'published'
                    ).order_by(Post.published_at.desc()).all()

                    stats[category] = {
                        "name": self.CATEGORY_NAMES.get(category, category),
                        "total_posts": len(posts),
                        "last_post": posts[0].published_at.isoformat() if posts else None,
                        "base_weight": self.WEIGHTS.get(category, 1)
                    }

        except Exception as e:
            logger.error(f"카테고리 통계 조회 실패: {e}")

        return stats

    def get_least_used_category(self, hours: int = 48) -> str:
        """
        최근 N시간 동안 가장 적게 사용된 카테고리 반환

        Args:
            hours: 조회 기간 (시간)

        Returns:
            가장 적게 사용된 카테고리
        """
        recent_categories = self._get_recent_categories(hours=hours)

        # 카테고리별 사용 횟수 계산
        usage_count = {cat: recent_categories.count(cat) for cat in self.CATEGORIES}

        # 가장 적게 사용된 카테고리 (동률이면 기본 가중치 높은 것 우선)
        least_used = min(
            self.CATEGORIES,
            key=lambda x: (usage_count.get(x, 0), -self.WEIGHTS.get(x, 1))
        )

        logger.info(f"가장 적게 사용된 카테고리: {least_used}")
        return least_used


# ============================================
# 테스트 코드
# ============================================

def test_topic_rotator():
    """TopicRotator 테스트"""
    print("\n=== TopicRotator 테스트 ===\n")

    rotator = TopicRotator()

    # 10번 카테고리 선택 테스트
    print("카테고리 선택 테스트 (10회):")
    category_counts = {}

    for i in range(10):
        category = rotator.get_next_category()
        category_counts[category] = category_counts.get(category, 0) + 1
        print(f"  {i+1}. {category} ({rotator.CATEGORY_NAMES.get(category)})")

    print(f"\n카테고리 분포: {category_counts}")

    # 가장 적게 사용된 카테고리
    least_used = rotator.get_least_used_category()
    print(f"\n가장 적게 사용된 카테고리: {least_used}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    test_topic_rotator()
