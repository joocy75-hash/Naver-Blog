"""
데이터베이스 모델 및 ORM 설정
- SQLAlchemy를 사용한 데이터베이스 모델
- 뉴스, 포스트, 계정, 분석 데이터 관리
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from loguru import logger

# 베이스 모델
Base = declarative_base()


class NewsSource(Base):
    """뉴스 수집 기록"""
    __tablename__ = 'news_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(500), nullable=False)
    summary = Column(Text)
    sentiment = Column(String(50))  # positive, negative, neutral
    sentiment_score = Column(Float)
    keywords = Column(JSON)  # List[str]
    source_urls = Column(JSON)  # List[str]
    collected_at = Column(DateTime, default=datetime.now)

    # 관계
    posts = relationship("Post", back_populates="news")

    def __repr__(self):
        return f"<NewsSource(id={self.id}, topic='{self.topic[:30]}...')>"


class Post(Base):
    """생성된 블로그 포스트"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(Integer, ForeignKey('news_sources.id'))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    images = Column(JSON)  # List[Dict] - [{url, type, alt_text}]
    tags = Column(JSON)  # List[str]
    category = Column(String(100))
    published_at = Column(DateTime)
    naver_post_url = Column(String(500))
    status = Column(String(50), default='draft')  # draft, published, failed
    quality_score = Column(Float)

    # QA 결과
    qa_passed = Column(Boolean)
    qa_issues = Column(JSON)  # List[str]
    qa_warnings = Column(JSON)  # List[str]

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 관계
    news = relationship("NewsSource", back_populates="posts")
    analytics = relationship("Analytics", back_populates="post", uselist=False)

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:30]}...', status='{self.status}')>"


class Account(Base):
    """네이버 계정 관리"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    naver_id = Column(String(100), unique=True, nullable=False)
    blog_url = Column(String(500))
    last_login = Column(DateTime)
    last_post_at = Column(DateTime)
    total_posts = Column(Integer, default=0)
    status = Column(String(50), default='active')  # active, suspended, banned
    notes = Column(Text)  # 메모

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Account(id={self.id}, naver_id='{self.naver_id}', status='{self.status}')>"


class Analytics(Base):
    """포스트 성과 추적"""
    __tablename__ = 'analytics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id'), unique=True)
    views = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    likes = Column(Integer, default=0)

    # 추적 기록
    last_checked_at = Column(DateTime, default=datetime.now)
    check_history = Column(JSON)  # List[Dict] - 시간별 추적 기록

    # 관계
    post = relationship("Post", back_populates="analytics")

    def __repr__(self):
        return f"<Analytics(post_id={self.post_id}, views={self.views})>"


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Args:
            database_url: 데이터베이스 URL (None이면 환경 변수에서 로드)
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'sqlite:///./data/blog_bot.db'
        )

        # 엔진 생성
        self.engine = create_engine(
            self.database_url,
            echo=False,  # SQL 로그 출력 비활성화
            pool_pre_ping=True  # 연결 유효성 검사
        )

        # 세션 팩토리
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"데이터베이스 연결: {self.database_url}")

    def create_tables(self):
        """모든 테이블 생성"""
        Base.metadata.create_all(bind=self.engine)
        logger.success("데이터베이스 테이블 생성 완료")

    def drop_tables(self):
        """모든 테이블 삭제 (주의!)"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("데이터베이스 테이블 삭제 완료")

    def get_session(self):
        """새 데이터베이스 세션 생성"""
        return self.SessionLocal()

    # ============================================
    # NewsSource CRUD
    # ============================================

    def create_news(self, session, **kwargs) -> NewsSource:
        """뉴스 레코드 생성"""
        news = NewsSource(**kwargs)
        session.add(news)
        session.commit()
        session.refresh(news)
        logger.info(f"뉴스 저장: {news.topic[:50]}...")
        return news

    def get_recent_news(self, session, limit: int = 10):
        """최근 뉴스 조회"""
        return session.query(NewsSource).order_by(
            NewsSource.collected_at.desc()
        ).limit(limit).all()

    # ============================================
    # Post CRUD
    # ============================================

    def create_post(self, session, **kwargs) -> Post:
        """포스트 레코드 생성"""
        post = Post(**kwargs)
        session.add(post)
        session.commit()
        session.refresh(post)
        logger.info(f"포스트 저장: {post.title[:50]}...")
        return post

    def update_post_status(
        self,
        session,
        post_id: int,
        status: str,
        naver_post_url: Optional[str] = None
    ):
        """포스트 상태 업데이트"""
        post = session.query(Post).filter(Post.id == post_id).first()
        if post:
            post.status = status
            if naver_post_url:
                post.naver_post_url = naver_post_url
                post.published_at = datetime.now()
            session.commit()
            logger.info(f"포스트 상태 업데이트: {post_id} -> {status}")

    def get_posts_by_status(self, session, status: str):
        """상태별 포스트 조회"""
        return session.query(Post).filter(Post.status == status).all()

    # ============================================
    # Account CRUD
    # ============================================

    def get_or_create_account(self, session, naver_id: str) -> Account:
        """계정 조회 또는 생성"""
        account = session.query(Account).filter(
            Account.naver_id == naver_id
        ).first()

        if not account:
            account = Account(naver_id=naver_id)
            session.add(account)
            session.commit()
            session.refresh(account)
            logger.info(f"새 계정 생성: {naver_id}")

        return account

    def update_account_last_post(self, session, naver_id: str):
        """계정의 마지막 포스팅 시간 업데이트"""
        account = self.get_or_create_account(session, naver_id)
        account.last_post_at = datetime.now()
        account.total_posts += 1
        session.commit()
        logger.info(f"계정 포스팅 기록 업데이트: {naver_id}")

    # ============================================
    # Analytics CRUD
    # ============================================

    def create_analytics(self, session, post_id: int) -> Analytics:
        """분석 레코드 생성"""
        analytics = Analytics(post_id=post_id)
        session.add(analytics)
        session.commit()
        session.refresh(analytics)
        return analytics

    def update_analytics(
        self,
        session,
        post_id: int,
        views: int,
        comments: int = 0,
        shares: int = 0,
        likes: int = 0
    ):
        """분석 데이터 업데이트"""
        analytics = session.query(Analytics).filter(
            Analytics.post_id == post_id
        ).first()

        if analytics:
            analytics.views = views
            analytics.comments = comments
            analytics.shares = shares
            analytics.likes = likes
            analytics.last_checked_at = datetime.now()
            session.commit()
            logger.info(f"분석 데이터 업데이트: post_id={post_id}, views={views}")

    # ============================================
    # Topic & Category 관련 메서드
    # ============================================

    def get_recent_topics(self, session, days: int = 7) -> list:
        """최근 N일간 포스팅 주제(제목) 조회"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        posts = session.query(Post).filter(
            Post.created_at >= cutoff
        ).all()
        return [p.title for p in posts]

    def is_topic_duplicate(self, session, topic: str, similarity_threshold: float = 0.7) -> bool:
        """
        주제 중복 확인 - difflib.SequenceMatcher 사용

        Args:
            session: DB 세션
            topic: 확인할 주제
            similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)

        Returns:
            중복 여부
        """
        from difflib import SequenceMatcher

        recent_topics = self.get_recent_topics(session)
        for recent in recent_topics:
            similarity = SequenceMatcher(None, topic.lower(), recent.lower()).ratio()
            if similarity > similarity_threshold:
                logger.warning(f"중복 주제 감지: '{topic}' ~ '{recent}' (유사도: {similarity:.2f})")
                return True
        return False

    def get_recent_categories(self, session, hours: int = 24) -> list:
        """최근 N시간 포스팅 카테고리 조회"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        posts = session.query(Post).filter(
            Post.created_at >= cutoff
        ).all()
        return [p.category for p in posts if p.category]


# ============================================
# 컨텍스트 매니저
# ============================================

class DBSession:
    """데이터베이스 세션 컨텍스트 매니저"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session = None

    def __enter__(self):
        self.session = self.db_manager.get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
            logger.error(f"트랜잭션 롤백: {exc_val}")
        else:
            self.session.commit()
        self.session.close()


# ============================================
# 테스트 코드
# ============================================

def test_database():
    """데이터베이스 테스트"""
    print("\n=== Database 테스트 ===\n")

    # 데이터베이스 매니저 생성
    db = DatabaseManager("sqlite:///./data/test_blog_bot.db")

    # 테이블 생성
    db.create_tables()

    # 테스트 데이터 생성
    with DBSession(db) as session:
        # 뉴스 생성
        news = db.create_news(
            session,
            topic="비트코인 급등",
            summary="비트코인이 6만 달러를 돌파했습니다.",
            sentiment="positive",
            sentiment_score=0.8,
            keywords=["비트코인", "급등"],
            source_urls=["https://example.com"]
        )

        # 포스트 생성
        post = db.create_post(
            session,
            news_id=news.id,
            title="비트코인 6만 달러 돌파!",
            content="<p>내용...</p>",
            tags=["비트코인", "투자"],
            status="draft",
            quality_score=85.5
        )

        # 계정 생성
        account = db.get_or_create_account(session, "test_user")

        print(f"뉴스: {news}")
        print(f"포스트: {post}")
        print(f"계정: {account}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    test_database()
