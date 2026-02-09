"""재무 데이터 수집기 (한국 증시 전용)

한국 상장기업 재무 데이터:
1. 재무제표 (손익계산서, 재무상태표, 현금흐름표) - yfinance 또는 KRX
2. 공시 - DART API (향후 추가)
3. 실적발표 - 향후 추가
"""
import os
import time
import json
import logging
import requests
import yfinance as yf
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from .base_collector import BaseCollector
from src.storage.database import Database
from src.storage.models import Stock, FinancialStatement

logger = logging.getLogger("marketsense")


class FundamentalsCollector(BaseCollector):
    """재무 데이터 수집기 (한국 증시)"""

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.fund_config = config.get("fundamentals", {})
        self.quarters = self.fund_config.get("financial_statements", {}).get("quarters", 5)

    def _to_yf_ticker(self, ticker: str, session=None) -> str:
        """DB 티커를 yfinance 티커로 변환"""
        if ticker.startswith("^") or "." in ticker:
            return ticker
        if session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if stock and stock.index_membership in ("KOSPI", "KOSDAQ"):
                suffix = ".KS" if stock.index_membership == "KOSPI" else ".KQ"
                return ticker + suffix
        if ticker.isdigit() and len(ticker) == 6:
            return ticker + ".KS"
        return ticker

    def collect(self, tickers: list = None, **kwargs):
        """재무제표 수집 (yfinance)"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            try:
                if not tickers:
                    # 한국 종목만 필터링
                    stocks = session.query(Stock).filter(
                        Stock.is_active == True,
                        Stock.index_membership.in_(["KOSPI", "KOSDAQ"])
                    ).all()
                    tickers = [s.ticker for s in stocks]

                logger.info(f"[Fundamentals] {len(tickers)}개 종목 재무제표 수집 시작")

                for idx, ticker in enumerate(tickers):
                    if idx > 0 and idx % 100 == 0:
                        logger.info(f"[Fundamentals] 진행: {idx}/{len(tickers)} ({total}건 수집)")

                    stock = session.query(Stock).filter_by(ticker=ticker).first()
                    if not stock:
                        continue

                    yf_ticker = self._to_yf_ticker(ticker, session)
                    count = self._collect_financials_yfinance(session, ticker, stock.id, yf_ticker)
                    total += count

                    # 주기적으로 flush
                    if idx % 50 == 0 and idx > 0:
                        session.flush()

                    time.sleep(0.3)

                self._finish_run(run, total)
                logger.info(f"[Fundamentals] 총 {total}건 수집 완료")

            except Exception as e:
                logger.error(f"[Fundamentals] 실패: {e}")
                self._finish_run(run, total, str(e))
                raise

    def _collect_financials_yfinance(self, session, ticker: str, stock_id: int, yf_symbol: str) -> int:
        """yfinance로 재무제표 수집"""
        count = 0
        try:
            yf_ticker = yf.Ticker(yf_symbol)

            # 분기별 재무제표
            quarterly_financials = {
                "income_statement": yf_ticker.quarterly_financials,
                "balance_sheet": yf_ticker.quarterly_balance_sheet,
                "cash_flow": yf_ticker.quarterly_cashflow,
            }

            for statement_type, df in quarterly_financials.items():
                if df is None or df.empty:
                    continue

                # 최근 N 분기
                for col in df.columns[:self.quarters]:
                    period_end = col.date() if hasattr(col, "date") else col

                    # 중복 체크
                    exists = session.query(FinancialStatement).filter_by(
                        stock_id=stock_id,
                        period="quarterly",
                        period_end=period_end,
                        statement_type=statement_type,
                    ).first()
                    if exists:
                        continue

                    # JSON 데이터
                    data_dict = df[col].to_dict()
                    # NaN을 None으로 변환
                    data_dict = {k: (None if str(v) == "nan" else float(v)) for k, v in data_dict.items()}

                    stmt = FinancialStatement(
                        stock_id=stock_id,
                        ticker=ticker,
                        period="quarterly",
                        period_end=period_end,
                        statement_type=statement_type,
                        data=data_dict,
                        currency="KRW",
                    )
                    session.add(stmt)
                    count += 1

        except Exception as e:
            logger.debug(f"[yfinance] {ticker} ({yf_symbol}) 실패: {e}")

        return count
