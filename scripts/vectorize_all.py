#!/usr/bin/env python3
"""전체 데이터 벡터화 스크립트

공시와 리포트를 ChromaDB에 벡터화
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db
from src.utils.helpers import load_config
from src.storage.models import DisclosureData, ResearchReport, Stock
from src.rag.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("데이터 벡터화 시작")
    
    # DB 초기화
    config = load_config()
    db = init_db(config)
    
    # 벡터 스토어
    vs = VectorStore()
    
    # 기존 통계
    stats = vs.get_stats()
    logger.info(f"현재 벡터 DB:")
    logger.info(f"  뉴스: {stats['news_count']}개")
    logger.info(f"  공시: {stats['disclosures_count']}개")
    logger.info(f"  리포트: {stats['reports_count']}개")
    
    with db.get_session() as session:
        # 1. 공시 벡터화
        logger.info("\n=== 공시 벡터화 ===")
        disclosures = session.query(DisclosureData).all()
        logger.info(f"PostgreSQL 공시: {len(disclosures)}개")
        
        if disclosures:
            disc_data = []
            for disc in disclosures:
                # ticker 가져오기
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
        
        # 2. 리포트 벡터화
        logger.info("\n=== 리포트 벡터화 ===")
        reports = session.query(ResearchReport).all()
        logger.info(f"PostgreSQL 리포트: {len(reports)}개")
        
        if reports:
            report_data = []
            for report in reports:
                # ticker 가져오기
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
    
    # 최종 통계
    stats = vs.get_stats()
    logger.info("\n=== 완료! ===")
    logger.info(f"벡터 DB:")
    logger.info(f"  뉴스: {stats['news_count']}개")
    logger.info(f"  공시: {stats['disclosures_count']}개")
    logger.info(f"  리포트: {stats['reports_count']}개")

if __name__ == "__main__":
    main()
