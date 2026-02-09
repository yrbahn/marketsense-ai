#!/usr/bin/env python3
"""
한국 증시 (코스피) 종목 유니버스 초기화

Usage:
  python3 -m src.init_krx              # 코스피 시총 Top 30
  python3 -m src.init_krx --top 50     # Top 50
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from src.storage.database import init_db
from src.storage.models import Stock
from src.utils.helpers import load_config


# 코스피 시가총액 Top 50 (2025년 기준)
KOSPI_TOP_STOCKS = [
    ("005930", "삼성전자", "Technology"),
    ("000660", "SK하이닉스", "Technology"),
    ("373220", "LG에너지솔루션", "Industrials"),
    ("207940", "삼성바이오로직스", "Healthcare"),
    ("005380", "현대차", "Consumer Cyclical"),
    ("000270", "기아", "Consumer Cyclical"),
    ("006400", "삼성SDI", "Technology"),
    ("051910", "LG화학", "Basic Materials"),
    ("035420", "NAVER", "Communication Services"),
    ("035720", "카카오", "Communication Services"),
    ("105560", "KB금융", "Financial Services"),
    ("055550", "신한지주", "Financial Services"),
    ("096770", "SK이노베이션", "Energy"),
    ("003670", "포스코홀딩스", "Basic Materials"),
    ("028260", "삼성물산", "Industrials"),
    ("034730", "SK", "Industrials"),
    ("032830", "삼성생명", "Financial Services"),
    ("003550", "LG", "Industrials"),
    ("066570", "LG전자", "Consumer Cyclical"),
    ("012330", "현대모비스", "Consumer Cyclical"),
    ("086790", "하나금융지주", "Financial Services"),
    ("015760", "한국전력", "Utilities"),
    ("017670", "SK텔레콤", "Communication Services"),
    ("030200", "KT", "Communication Services"),
    ("009150", "삼성전기", "Technology"),
    ("018260", "삼성에스디에스", "Technology"),
    ("316140", "우리금융지주", "Financial Services"),
    ("033780", "KT&G", "Consumer Defensive"),
    ("010130", "고려아연", "Basic Materials"),
    ("011170", "롯데케미칼", "Basic Materials"),
    ("034020", "두산에너빌리티", "Industrials"),
    ("009540", "한국조선해양", "Industrials"),
    ("010950", "S-Oil", "Energy"),
    ("024110", "기업은행", "Financial Services"),
    ("011200", "HMM", "Industrials"),
    ("138040", "메리츠금융지주", "Financial Services"),
    ("000810", "삼성화재", "Financial Services"),
    ("036570", "엔씨소프트", "Communication Services"),
    ("003490", "대한항공", "Industrials"),
    ("004020", "현대제철", "Basic Materials"),
    ("047050", "포스코인터내셔널", "Basic Materials"),
    ("259960", "크래프톤", "Communication Services"),
    ("352820", "하이브", "Communication Services"),
    ("090430", "아모레퍼시픽", "Consumer Defensive"),
    ("068270", "셀트리온", "Healthcare"),
    ("011790", "SKC", "Basic Materials"),
    ("088980", "맥쿼리인프라", "Financial Services"),
    ("161390", "한국타이어앤테크놀로지", "Consumer Cyclical"),
    ("004490", "세방전지", "Industrials"),
    ("009830", "한화솔루션", "Technology"),
]


def init_krx_universe(config, top_n: int = 30):
    """KRX 종목 유니버스 DB 초기화"""
    db = init_db(config)
    stocks_data = KOSPI_TOP_STOCKS[:top_n]

    print(f"📈 코스피 시가총액 Top {top_n} 종목 초기화 중...")

    with db.get_session() as session:
        added = 0
        for ticker, name, sector in stocks_data:
            exists = session.query(Stock).filter_by(ticker=ticker).first()
            if exists:
                print(f"  ⏭️  {ticker} {name} (이미 존재)")
                continue

            stock_obj = Stock(
                ticker=ticker,
                name=name,
                sector=sector,
                index_membership="KOSPI",
                is_active=True,
            )
            session.add(stock_obj)
            added += 1
            print(f"  ✅ {ticker} {name} [{sector}]")

    print(f"\n🎉 {added}개 종목 추가 완료!")


def main():
    parser = argparse.ArgumentParser(description="KRX 종목 유니버스 초기화")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--top", type=int, default=30, help="상위 N개 종목")
    args = parser.parse_args()

    config = load_config(args.config)
    init_krx_universe(config, args.top)


if __name__ == "__main__":
    main()
