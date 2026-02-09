#!/usr/bin/env python3
"""
한국 증시 종목 유니버스 초기화 (FinanceDataReader)

Usage:
  python3 -m src.init_krx                     # KRX 전체 (KOSPI+KOSDAQ+KONEX)
  python3 -m src.init_krx --market KOSPI      # KOSPI만
  python3 -m src.init_krx --market KOSDAQ     # KOSDAQ만
  python3 -m src.init_krx --top 100           # 시총 상위 100개
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import FinanceDataReader as fdr

from src.storage.database import init_db
from src.storage.models import Stock
from src.utils.helpers import load_config


def init_krx_universe(config, market: str = "ALL", top_n: int = None):
    """KRX 종목 유니버스 초기화 (FinanceDataReader)"""
    db = init_db(config)

    print(f"📡 KRX 상장 종목 조회 중...")
    
    # FinanceDataReader로 전체 종목 조회
    df_all = fdr.StockListing('KRX')
    print(f"  ✅ 전체 {len(df_all)}개 종목 조회 완료")

    # 시장 필터링
    if market != "ALL":
        df_filtered = df_all[df_all['Market'] == market]
        print(f"  📊 {market}: {len(df_filtered)}개")
    else:
        df_filtered = df_all
        kospi_cnt = len(df_all[df_all['Market'] == 'KOSPI'])
        kosdaq_cnt = len(df_all[df_all['Market'] == 'KOSDAQ'])
        konex_cnt = len(df_all[df_all['Market'] == 'KONEX'])
        print(f"  📊 KOSPI: {kospi_cnt}개, KOSDAQ: {kosdaq_cnt}개, KONEX: {konex_cnt}개")

    # 시가총액으로 정렬 (상위 N개)
    if top_n:
        df_filtered = df_filtered.nlargest(top_n, 'Marcap')
        print(f"  🔝 시총 상위 {top_n}개 선택")

    # DB에 저장
    with db.get_session() as session:
        added = 0
        updated = 0
        
        for _, row in df_filtered.iterrows():
            ticker = row['Code']
            
            # 기존 종목 확인
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            
            if stock:
                # 업데이트
                stock.name = row['Name']
                stock.index_membership = row['Market']
                stock.market_cap = float(row['Marcap']) if row['Marcap'] else None
                stock.is_active = True
                updated += 1
            else:
                # 신규 추가
                stock = Stock(
                    ticker=ticker,
                    name=row['Name'],
                    index_membership=row['Market'],
                    market_cap=float(row['Marcap']) if row['Marcap'] else None,
                    is_active=True,
                )
                session.add(stock)
                added += 1

        print(f"\n💾 DB 저장: {added}개 신규, {updated}개 업데이트")

    print(f"🎉 총 {len(df_filtered)}개 종목 처리 완료!")


def main():
    parser = argparse.ArgumentParser(description="KRX 종목 유니버스 초기화")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--market", default="ALL", choices=["ALL", "KOSPI", "KOSDAQ", "KONEX"])
    parser.add_argument("--top", type=int, default=None, help="시총 상위 N개만")
    args = parser.parse_args()

    config = load_config(args.config)
    init_krx_universe(config, args.market, args.top)


if __name__ == "__main__":
    main()
