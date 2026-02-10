#!/usr/bin/env python3
"""뉴스 벡터화 스크립트

PostgreSQL의 뉴스를 ChromaDB에 벡터화
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db
from src.utils.helpers import load_config
from src.storage.models import NewsArticle
from src.rag.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("뉴스 벡터화 시작")
    
    # DB 초기화
    config = load_config()
    db = init_db(config)
    
    # 벡터 스토어
    vs = VectorStore()
    
    # 기존 통계
    stats = vs.get_stats()
    logger.info(f"현재 벡터 DB: 뉴스 {stats['news_count']}개")
    
    # 뉴스 가져오기
    with db.get_session() as session:
        total_news = session.query(NewsArticle).count()
        logger.info(f"PostgreSQL 뉴스: {total_news}개")
        
        # 배치로 벡터화
        batch_size = 1000
        offset = 0
        total_added = 0
        
        while True:
            news_batch = (
                session.query(NewsArticle)
                .order_by(NewsArticle.id)
                .limit(batch_size)
                .offset(offset)
                .all()
            )
            
            if not news_batch:
                break
            
            # 벡터화용 데이터 준비
            articles = []
            for news in news_batch:
                articles.append({
                    'id': str(news.id),
                    'ticker': news.ticker or '',
                    'title': news.title or '',
                    'content': news.summary or '',
                    'published_at': news.published_at,
                    'source': news.source or '',
                    'url': news.url or ''
                })
            
            # 벡터화
            vs.add_news(articles)
            total_added += len(articles)
            
            logger.info(f"진행: {total_added}/{total_news}")
            
            offset += batch_size
    
    # 최종 통계
    stats = vs.get_stats()
    logger.info(f"완료! 벡터 DB: 뉴스 {stats['news_count']}개")

if __name__ == "__main__":
    main()
