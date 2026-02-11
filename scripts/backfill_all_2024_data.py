"""전체 종목 2024년 데이터 백필 스크립트

marketsense-ai 전체 2,884개 종목 2024년 가격 데이터 수집
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
import FinanceDataReader as fdr

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import Database
from src.storage.models import Stock, PriceData
from sqlalchemy import and_

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("backfill_all")


def to_python_type(value):
    """pandas 값을 Python 타입으로 변환"""
    import pandas as pd
    import numpy as np
    
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def main():
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("전체 종목 2024년 데이터 백필 시작")
    logger.info("=" * 60)
    logger.info(f"수집 기간: 2024-01-01 ~ 2024-12-31")
    logger.info(f"시작 시간: {datetime.now()}")
    logger.info("=" * 60)
    
    # 데이터베이스 연결
    db_url = "postgresql://yrbahn@localhost:5432/marketsense"
    db = Database(db_url)
    
    with db.get_session() as session:
        # 전체 활성 종목 조회
        stocks = session.query(Stock).filter_by(is_active=True).all()
        total_stocks = len(stocks)
        
        logger.info(f"대상 종목: {total_stocks:,}개")
        logger.info("=" * 60)
        
        total_inserted = 0
        total_skipped = 0
        total_errors = 0
        
        for i, stock in enumerate(stocks, 1):
            ticker = stock.ticker
            
            # 주기적 진행 상황 출력 (매 100개)
            if i % 100 == 0:
                logger.info(f"진행: [{i}/{total_stocks}] ({i/total_stocks*100:.1f}%) - 추가: {total_inserted:,}, 건너뜀: {total_skipped:,}, 오류: {total_errors}")
            
            # 디버그 로그 (매 10개)
            if i % 10 == 0:
                logger.debug(f"[{i}/{total_stocks}] {stock.name}({ticker})")
            
            try:
                # 2024년 데이터 조회
                df = fdr.DataReader(ticker, "2024-01-01", "2024-12-31")
                
                if df.empty:
                    total_errors += 1
                    continue
                
                # 데이터 저장
                inserted = 0
                skipped = 0
                
                for idx, row in df.iterrows():
                    date = idx.date()
                    
                    # 이미 존재하는지 확인
                    exists = session.query(PriceData).filter(
                        and_(
                            PriceData.stock_id == stock.id,
                            PriceData.date == date
                        )
                    ).first()
                    
                    if exists:
                        skipped += 1
                        continue
                    
                    # 새 데이터 추가
                    price = PriceData(
                        stock_id=stock.id,
                        date=date,
                        open=to_python_type(row.get("Open")),
                        high=to_python_type(row.get("High")),
                        low=to_python_type(row.get("Low")),
                        close=to_python_type(row.get("Close")),
                        volume=to_python_type(row.get("Volume")),
                        dividend=0,
                        stock_split=0
                    )
                    session.add(price)
                    inserted += 1
                
                # 매 10개 종목마다 commit (메모리 관리)
                if i % 10 == 0:
                    session.commit()
                
                total_inserted += inserted
                total_skipped += skipped
                
            except Exception as e:
                logger.debug(f"  ❌ {stock.name}({ticker}) 실패: {e}")
                total_errors += 1
                session.rollback()
                continue
        
        # 마지막 commit
        session.commit()
    
    logger.info("=" * 60)
    logger.info(f"백필 완료!")
    logger.info(f"처리 종목: {total_stocks:,}개")
    logger.info(f"총 추가: {total_inserted:,}개")
    logger.info(f"총 건너뜀: {total_skipped:,}개")
    logger.info(f"총 오류: {total_errors:,}개")
    logger.info(f"종료 시간: {datetime.now()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
