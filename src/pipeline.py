#!/usr/bin/env python3
"""
MarketSenseAI 2.0 - Data Collection Pipeline

전체 데이터 수집 파이프라인을 실행합니다.

Usage:
  python -m src.pipeline                    # 전체 수집
  python -m src.pipeline --collector news   # 뉴스만 수집
  python -m src.pipeline --collector fundamentals
  python -m src.pipeline --collector dynamics
  python -m src.pipeline --collector macro
  python -m src.pipeline --init-db          # DB 초기화만
  python -m src.pipeline --init-universe    # 종목 유니버스 초기화
  python -m src.pipeline --tickers AAPL MSFT GOOGL  # 특정 종목만
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.utils.helpers import load_config, setup_logger, get_sp500_tickers, get_sp100_tickers
from src.storage.database import init_db
from src.storage.models import Stock
from src.collectors.news_collector import NewsCollector
from src.collectors.fundamentals_collector import FundamentalsCollector
from src.collectors.dynamics_collector import DynamicsCollector
from src.collectors.macro_collector import MacroCollector


def init_universe(db, index: str = "SP500"):
    """종목 유니버스 초기화"""
    import yfinance as yf

    if index == "SP100":
        tickers = get_sp100_tickers()
    else:
        tickers = get_sp500_tickers()

    with db.get_session() as session:
        for ticker in tickers:
            exists = session.query(Stock).filter_by(ticker=ticker).first()
            if exists:
                continue

            try:
                info = yf.Ticker(ticker).info
                stock = Stock(
                    ticker=ticker,
                    name=info.get("longName") or info.get("shortName", ticker),
                    sector=info.get("sector", ""),
                    industry=info.get("industry", ""),
                    market_cap=info.get("marketCap"),
                    index_membership=index,
                )
                session.add(stock)
                print(f"  ✓ {ticker}: {stock.name}")
            except Exception as e:
                print(f"  ✗ {ticker}: {e}")
                stock = Stock(ticker=ticker, name=ticker, index_membership=index)
                session.add(stock)

    print(f"\n✅ {len(tickers)} 종목 초기화 완료 ({index})")


def run_pipeline(config, db, collector_name: str = None, tickers: list = None):
    """데이터 수집 파이프라인 실행"""
    collectors = {
        "news": NewsCollector,
        "fundamentals": FundamentalsCollector,
        "dynamics": DynamicsCollector,
        "macro": MacroCollector,
    }

    if collector_name:
        if collector_name not in collectors:
            print(f"❌ 알 수 없는 수집기: {collector_name}")
            print(f"   사용 가능: {', '.join(collectors.keys())}")
            return
        targets = {collector_name: collectors[collector_name]}
    else:
        targets = collectors

    for name, CollectorClass in targets.items():
        print(f"\n{'='*50}")
        print(f"📦 [{name.upper()}] 수집 시작...")
        print(f"{'='*50}")

        try:
            collector = CollectorClass(config, db)
            collector.collect(tickers=tickers)
            print(f"✅ [{name.upper()}] 완료")
        except Exception as e:
            print(f"❌ [{name.upper()}] 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description="MarketSenseAI Data Pipeline")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--collector", choices=["news", "fundamentals", "dynamics", "macro"],
                        help="특정 수집기만 실행")
    parser.add_argument("--tickers", nargs="+", help="특정 종목만 수집")
    parser.add_argument("--init-db", action="store_true", help="DB 초기화")
    parser.add_argument("--init-universe", action="store_true", help="종목 유니버스 초기화")
    parser.add_argument("--index", default="SP500", choices=["SP100", "SP500"])
    args = parser.parse_args()

    config = load_config(args.config)
    log_cfg = config.get("logging", {})
    setup_logger(level=log_cfg.get("level", "INFO"), log_file=log_cfg.get("file"))

    print("🚀 MarketSenseAI 2.0 Data Pipeline")
    print(f"   DB: {config.get('database', {}).get('url', 'sqlite:///data/marketsense.db')}")

    db = init_db(config)

    if args.init_db:
        print("✅ 데이터베이스 초기화 완료")
        return

    if args.init_universe:
        init_universe(db, args.index)
        return

    run_pipeline(config, db, args.collector, args.tickers)
    print("\n🏁 파이프라인 완료!")


if __name__ == "__main__":
    main()
