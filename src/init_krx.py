#!/usr/bin/env python3
"""
한국 증시 전체 종목 유니버스 초기화 (KRX 공식 데이터)

Usage:
  python3 -m src.init_krx                     # 코스피+코스닥 전체
  python3 -m src.init_krx --market KOSPI      # 코스피만
  python3 -m src.init_krx --market KOSDAQ     # 코스닥만
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import io
import requests
import pandas as pd

from src.storage.database import init_db
from src.storage.models import Stock
from src.utils.helpers import load_config

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

KRX_URLS = {
    "KOSPI": "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType=stockMkt",
    "KOSDAQ": "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType=kosdaqMkt",
}


def fetch_krx_stocks(market: str) -> pd.DataFrame:
    """KRX 공식 상장법인목록 다운로드"""
    url = KRX_URLS.get(market)
    if not url:
        return pd.DataFrame()

    print(f"📡 [{market}] KRX 상장법인목록 다운로드 중...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    df = pd.read_html(io.BytesIO(resp.content))[0]
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df = df[df["종목코드"].str.match(r"^\d{6}$")]
    df["market"] = market

    print(f"  ✅ [{market}] {len(df)}종목")
    return df


def init_krx_universe(config, market: str = "ALL"):
    """KRX 종목 유니버스 DB 초기화"""
    db = init_db(config)

    markets = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
    frames = []
    for mkt in markets:
        df = fetch_krx_stocks(mkt)
        if not df.empty:
            frames.append(df)

    if not frames:
        print("❌ 종목 데이터를 가져올 수 없습니다.")
        return

    all_stocks = pd.concat(frames, ignore_index=True)

    with db.get_session() as session:
        added = 0
        skipped = 0
        for _, row in all_stocks.iterrows():
            ticker = row["종목코드"]
            exists = session.query(Stock).filter_by(ticker=ticker).first()
            if exists:
                skipped += 1
                continue

            stock_obj = Stock(
                ticker=ticker,
                name=row["회사명"],
                industry=row.get("업종", ""),
                index_membership=row["market"],
                is_active=True,
            )
            session.add(stock_obj)
            added += 1

        print(f"\n💾 DB 저장: {added}개 신규, {skipped}개 기존")

    print(f"🎉 총 {len(all_stocks)}종목 처리 완료!")


def main():
    parser = argparse.ArgumentParser(description="KRX 전체 종목 유니버스 초기화")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--market", default="ALL", choices=["ALL", "KOSPI", "KOSDAQ"])
    args = parser.parse_args()

    config = load_config(args.config)
    init_krx_universe(config, args.market)


if __name__ == "__main__":
    main()
