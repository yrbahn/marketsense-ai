#!/usr/bin/env python3
"""업종 정보 업데이트

종목명 기반 간단 업종 분류
"""
import sys
import logging
from typing import Dict
import re

from src.storage.database import init_db
from src.storage.models import Stock
from src.utils.helpers import load_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("marketsense")


# 업종 키워드 매핑
SECTOR_KEYWORDS = {
    '반도체': ['삼성전자', 'SK하이닉스', '반도체', 'SK스퀘어', '메모리', '파운드리', '실리콘'],
    '자동차': ['현대차', '기아', '모빌리티', '자동차', '차량', 'LG에너지솔루션'],
    '바이오': ['바이오', '제약', '셀트리온', '의약', '헬스케어', '의료', '병원', '제닉'],
    'IT/소프트웨어': ['네이버', 'NAVER', '카카오', 'IT', '소프트웨어', '게임', '엔터', 'JYP', 'SM', 'YG'],
    '금융': ['은행', '증권', '보험', '카드', '금융', '캐피탈', '저축은행', 'KB금융', '신한지주', '하나금융'],
    '화학': ['LG화학', '화학', '석유화학', '정유', '케미칼'],
    '전자': ['전자', '디스플레이', 'LG전자', '삼성SDI', 'LG디스플레이'],
    '건설': ['건설', '부동산', '시공', '인프라'],
    '유통': ['쇼핑', '유통', '편의점', '백화점', '마트'],
    '식품': ['식품', '음료', '외식', '농심', '오리온', 'CJ제일제당'],
    '통신': ['통신', 'KT', 'SKT', 'LG유플러스'],
    '에너지': ['전력', '에너지', '발전', '한전', '신재생'],
}


def classify_sector(name: str) -> tuple:
    """종목명으로 업종 분류
    
    Args:
        name: 종목명
        
    Returns:
        (sector, industry) 튜플
    """
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name:
                return (sector, sector)
    
    return ('기타', '기타')


def update_stock_sectors(db):
    """DB의 종목에 업종 정보 업데이트
    
    Args:
        db: 데이터베이스
    """
    logger.info("종목 업종 정보 업데이트 시작...")
    
    with db.get_session() as session:
        stocks = session.query(Stock).all()
        
        updated = 0
        for stock in stocks:
            sector, industry = classify_sector(stock.name)
            
            stock.sector = sector
            stock.industry = industry
            
            updated += 1
            
            if updated % 100 == 0:
                logger.info(f"진행: {updated}/{len(stocks)}")
        
        session.commit()
        
        logger.info(f"✅ {updated}/{len(stocks)}개 종목 업종 정보 업데이트 완료")


def main():
    """메인"""
    config = load_config()
    db = init_db(config)
    
    # DB 업데이트
    update_stock_sectors(db)
    
    # 통계
    with db.get_session() as session:
        total = session.query(Stock).count()
        with_sector = session.query(Stock).filter(
            Stock.sector != None, 
            Stock.sector != '', 
            Stock.sector != '기타'
        ).count()
        
        # 업종별 통계
        from sqlalchemy import func
        sector_counts = session.query(
            Stock.sector, func.count(Stock.id)
        ).group_by(Stock.sector).order_by(func.count(Stock.id).desc()).all()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 업종 정보 통계")
        logger.info("=" * 60)
        logger.info(f"전체 종목: {total:,}개")
        logger.info(f"분류된 종목: {with_sector:,}개 ({with_sector/total*100:.1f}%)")
        logger.info("")
        logger.info("업종별 분포:")
        for sector, count in sector_counts[:15]:
            logger.info(f"  {sector}: {count:,}개")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
