"""2023년 TOP 50 데이터 백필 스크립트

kospi-3s-trader lookback을 위한 2023년 데이터 수집
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
logger = logging.getLogger("backfill2023")


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
    # TOP 50 종목 리스트
    top50_tickers = [
        "005930", "000660", "373220", "207940", "005380", "000270", "006400", "051910",
        "035420", "035720", "105560", "055550", "096770", "005490", "028260", "034730",
        "032830", "012330", "086790", "015760", "033780", "010130", "009150", "316140",
        "005935", "000810", "003670", "006800", "009540", "010120", "010140", "011200",
        "012450", "024110", "034020", "042660", "042700", "064350", "068270", "086280",
        "086520", "138040", "196170", "247540", "267250", "267260", "272210", "298040",
        "329180", "402340"
    ]
    
    logger.info("=" * 60)
    logger.info("2023년 TOP 50 데이터 백필 시작")
    logger.info("=" * 60)
    logger.info(f"대상 종목: {len(top50_tickers)}개")
    logger.info(f"수집 기간: 2023-01-01 ~ 2023-12-31")
    logger.info(f"시작 시간: {datetime.now()}")
    logger.info("=" * 60)
    
    # 데이터베이스 연결
    db_url = "postgresql://yrbahn@localhost:5432/marketsense"
    db = Database(db_url)
    
    total_inserted = 0
    total_skipped = 0
    
    with db.get_session() as session:
        for i, ticker in enumerate(top50_tickers, 1):
            # 종목 조회
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                logger.warning(f"[{i}/{len(top50_tickers)}] {ticker}: 종목 없음 (건너뜀)")
                continue
            
            logger.info(f"[{i}/{len(top50_tickers)}] {stock.name}({ticker}) 수집 중...")
            
            try:
                # 2023년 데이터 조회
                df = fdr.DataReader(ticker, "2023-01-01", "2023-12-31")
                
                if df.empty:
                    logger.warning(f"  데이터 없음")
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
                
                session.commit()
                
                total_inserted += inserted
                total_skipped += skipped
                
                logger.info(f"  ✅ {inserted}개 추가, {skipped}개 건너뜀")
                
            except Exception as e:
                logger.error(f"  ❌ 실패: {e}")
                session.rollback()
                continue
    
    logger.info("=" * 60)
    logger.info(f"백필 완료!")
    logger.info(f"총 추가: {total_inserted:,}개")
    logger.info(f"총 건너뜀: {total_skipped:,}개")
    logger.info(f"종료 시간: {datetime.now()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
