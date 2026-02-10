#!/usr/bin/env python3
"""증분 벡터화 스크립트

마지막 벡터화 이후 새로운 데이터만 벡터화
- 뉴스
- 리포트
- 블로그
- 공시
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db
from src.utils.helpers import load_config
from src.storage.models import NewsArticle, ResearchReport, BlogPost, DisclosureData, Stock
from src.rag.vector_store import VectorStore
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

METADATA_FILE = "./cache/vectorize_metadata.json"

def load_metadata():
    """메타데이터 로드"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'news_last_vectorized': None,
        'reports_last_vectorized': None,
        'blogs_last_vectorized': None,
        'disclosures_last_vectorized': None
    }

def save_metadata(metadata):
    """메타데이터 저장"""
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def main():
    logger.info("=== 증분 벡터화 시작 ===")
    
    # 메타데이터 로드
    metadata = load_metadata()
    logger.info(f"마지막 벡터화: {metadata}")
    
    # DB 초기화
    config = load_config()
    db = init_db(config)
    
    # 벡터 스토어
    vs = VectorStore()
    
    # 현재 시간
    now = datetime.now()
    now_str = now.isoformat()
    
    total_added = 0
    
    with db.get_session() as session:
        # 1. 뉴스 증분 벡터화
        logger.info("\n=== 뉴스 증분 벡터화 ===")
        last_news = metadata.get('news_last_vectorized')
        
        if last_news:
            last_dt = datetime.fromisoformat(last_news)
            new_news = session.query(NewsArticle).filter(
                NewsArticle.collected_at > last_dt
            ).all()
        else:
            # 처음이면 전체
            new_news = session.query(NewsArticle).all()
        
        logger.info(f"새 뉴스: {len(new_news)}개")
        
        if new_news:
            # 배치 단위로 추가 (ChromaDB 제한)
            batch_size = 1000
            for i in range(0, len(new_news), batch_size):
                batch = new_news[i:i + batch_size]
                news_data = []
                
                for news in batch:
                    news_data.append({
                        'id': str(news.id),
                        'ticker': news.ticker or '',
                        'title': news.title or '',
                        'content': news.summary or '',
                        'published_at': news.published_at,
                        'source': news.source or '',
                        'url': news.url or ''
                    })
                
                vs.add_news(news_data)
                total_added += len(news_data)
                logger.info(f"  → 뉴스 {i + len(batch)}/{len(new_news)} 완료")
            
            metadata['news_last_vectorized'] = now_str
        
        # 2. 리포트 증분 벡터화
        logger.info("\n=== 리포트 증분 벡터화 ===")
        last_reports = metadata.get('reports_last_vectorized')
        
        if last_reports:
            last_dt = datetime.fromisoformat(last_reports)
            new_reports = session.query(ResearchReport).filter(
                ResearchReport.collected_at > last_dt
            ).all()
        else:
            new_reports = session.query(ResearchReport).all()
        
        logger.info(f"새 리포트: {len(new_reports)}개")
        
        if new_reports:
            # 배치 단위로 추가
            batch_size = 1000
            for i in range(0, len(new_reports), batch_size):
                batch = new_reports[i:i + batch_size]
                report_data = []
                
                for report in batch:
                    stock = session.query(Stock).filter_by(id=report.stock_id).first()
                    ticker = stock.ticker if stock else ''
                    
                    report_data.append({
                        'id': str(report.id),
                        'stock_id': report.stock_id,
                        'ticker': ticker,
                        'title': report.title or '',
                        'firm': report.firm or '',
                        'report_date': report.report_date
                    })
                
                vs.add_reports(report_data)
                total_added += len(report_data)
                logger.info(f"  → 리포트 {i + len(batch)}/{len(new_reports)} 완료")
            
            metadata['reports_last_vectorized'] = now_str
        
        # 3. 블로그 증분 벡터화 (선택)
        logger.info("\n=== 블로그 증분 벡터화 (스킵) ===")
        # 블로그는 RAG 사용 안 함
        
        # 4. 공시 증분 벡터화
        logger.info("\n=== 공시 증분 벡터화 ===")
        last_disclosures = metadata.get('disclosures_last_vectorized')
        
        if last_disclosures:
            last_dt = datetime.fromisoformat(last_disclosures)
            new_disclosures = session.query(DisclosureData).filter(
                DisclosureData.collected_at > last_dt
            ).all()
        else:
            new_disclosures = session.query(DisclosureData).all()
        
        logger.info(f"새 공시: {len(new_disclosures)}개")
        
        if new_disclosures:
            # 배치 단위로 추가
            batch_size = 1000
            for i in range(0, len(new_disclosures), batch_size):
                batch = new_disclosures[i:i + batch_size]
                disc_data = []
                
                for disc in batch:
                    stock = session.query(Stock).filter_by(id=disc.stock_id).first()
                    ticker = stock.ticker if stock else ''
                    
                    disc_data.append({
                        'id': str(disc.id),
                        'stock_id': disc.stock_id,
                        'ticker': ticker,
                        'report_nm': disc.report_nm or '',
                        'disclosure_type': disc.disclosure_type or '',
                        'rcept_dt': disc.rcept_dt
                    })
                
                vs.add_disclosures(disc_data)
                total_added += len(disc_data)
                logger.info(f"  → 공시 {i + len(batch)}/{len(new_disclosures)} 완료")
            
            metadata['disclosures_last_vectorized'] = now_str
    
    # 메타데이터 저장
    save_metadata(metadata)
    
    # 통계
    stats = vs.get_stats()
    logger.info("\n=== 완료! ===")
    logger.info(f"새로 추가: {total_added}개")
    logger.info(f"벡터 DB 현황:")
    logger.info(f"  뉴스: {stats['news_count']}개")
    logger.info(f"  리포트: {stats['reports_count']}개")
    logger.info(f"  공시: {stats['disclosures_count']}개")

if __name__ == "__main__":
    main()
