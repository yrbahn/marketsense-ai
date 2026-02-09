"""데이터베이스 연결 및 세션 관리"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

logger = logging.getLogger("marketsense")


class Database:
    """SQLAlchemy 데이터베이스 관리"""

    def __init__(self, db_url: str = None, echo: bool = False):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL", "sqlite:///data/marketsense.db"
        )

        # SQLite인 경우 디렉토리 생성
        if self.db_url.startswith("sqlite"):
            db_path = self.db_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        self.engine = create_engine(self.db_url, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """모든 테이블 생성"""
        Base.metadata.create_all(self.engine)
        logger.info("데이터베이스 테이블 생성 완료")

    def drop_tables(self):
        """모든 테이블 삭제 (주의!)"""
        Base.metadata.drop_all(self.engine)
        logger.info("데이터베이스 테이블 삭제 완료")

    @contextmanager
    def get_session(self) -> Session:
        """세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_new_session(self) -> Session:
        """새 세션 반환 (수동 관리)"""
        return self.SessionLocal()


def init_db(config: dict = None) -> Database:
    """설정 기반 DB 초기화"""
    db_url = None
    echo = False
    if config:
        db_url = config.get("database", {}).get("url")
        echo = config.get("database", {}).get("echo", False)

    db = Database(db_url=db_url, echo=echo)
    db.create_tables()
    return db
