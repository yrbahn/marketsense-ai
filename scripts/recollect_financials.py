#!/usr/bin/env python3
"""재무제표 재수집 스크립트

DART API 데이터 구조 변경 후 재무제표를 재수집합니다.
- 기존: flat structure {계정명: 금액}
- 신규: nested structure {재무제표명: {계정명: 금액}}
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import load_config
from src.storage.database import Database
from src.collectors.fundamentals_collector import FundamentalsCollector

def main():
    """재무제표 재수집 실행"""
    config = load_config()
    db = Database(config)
    
    print("🔄 재무제표 재수집 시작...")
    print("⚠️  이전 데이터는 유지되며, 중복 체크 후 새 데이터만 추가됩니다.")
    
    # FundamentalsCollector 초기화
    collector = FundamentalsCollector(config, db)
    
    # 상위 200개 종목만 재수집 (테스트)
    print("\n📊 상위 200개 종목 재수집...")
    
    with db.get_session() as session:
        from src.storage.models import Stock
        stocks = session.query(Stock).filter(
            Stock.is_active == True,
            Stock.index_membership.in_(["KOSPI", "KOSDAQ"])
        ).order_by(Stock.market_cap.desc()).limit(200).all()
        
        tickers = [s.ticker for s in stocks]
        print(f"대상 종목: {len(tickers)}개")
    
    # 수집 실행
    collector.collect(tickers=tickers)
    
    print("\n✅ 재수집 완료!")
    print("\n📋 확인:")
    print("  psql -d marketsense -c \"SELECT s.ticker, s.name, fs.period_end, ")
    print("         jsonb_object_keys(fs.raw_data) as statement_type ")
    print("         FROM financial_statements fs ")
    print("         JOIN stocks s ON fs.stock_id = s.id ")
    print("         WHERE s.ticker='005380' LIMIT 10\"")

if __name__ == "__main__":
    main()
