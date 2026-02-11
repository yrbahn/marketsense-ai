"""재무 데이터 수집기 (한국 증시 전용)

한국 상장기업 재무 데이터:
1. 재무제표 (손익계산서, 재무상태표, 현금흐름표) - DART API
2. 공시 - DART API
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
from .dart_client import DartClient
from src.storage.database import Database
from src.storage.models import Stock, FinancialStatement

logger = logging.getLogger("marketsense")


class FundamentalsCollector(BaseCollector):
    """재무 데이터 수집기 (한국 증시)"""

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.fund_config = config.get("fundamentals", {})
        self.quarters = self.fund_config.get("financial_statements", {}).get("quarters", 5)
        
        # DART API 클라이언트
        try:
            self.dart = DartClient()
            self.dart_enabled = True
            logger.info("[Fundamentals] DART API 활성화")
        except ValueError:
            self.dart = None
            self.dart_enabled = False
            logger.warning("[Fundamentals] DART API 키 없음 - DART 수집 비활성화")
        
        # DART 기업 고유번호 캐시
        self.corp_code_map = {}

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
        """재무제표 수집 (DART API)"""
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

                # DART 고유번호 매핑 (한 번만)
                if self.dart_enabled and not self.corp_code_map:
                    logger.info("[Fundamentals] DART 기업 고유번호 매핑 중...")
                    self.corp_code_map = self.dart.get_corp_code_list()

                for idx, ticker in enumerate(tickers):
                    if idx > 0 and idx % 100 == 0:
                        logger.info(f"[Fundamentals] 진행: {idx}/{len(tickers)} ({total}건 수집)")

                    stock = session.query(Stock).filter_by(ticker=ticker).first()
                    if not stock:
                        continue

                    # DART API 사용
                    if self.dart_enabled:
                        count = self._collect_financials_dart(session, ticker, stock.id)
                        total += count

                    # 주기적으로 flush
                    if idx % 50 == 0 and idx > 0:
                        session.flush()

                    time.sleep(0.5)  # DART API rate limit

                self._finish_run(run, total)
                logger.info(f"[Fundamentals] 총 {total}건 수집 완료")

            except Exception as e:
                logger.error(f"[Fundamentals] 실패: {e}")
                self._finish_run(run, total, str(e))
                raise

    def _collect_financials_dart(self, session, ticker: str, stock_id: int) -> int:
        """DART API로 재무제표 수집 (2024년 4개 분기)"""
        count = 0
        results = {"Q1": False, "Q2": False, "Q3": False, "Q4": False}

        # DART 고유번호 조회
        corp_code = self.corp_code_map.get(ticker)
        if not corp_code:
            logger.debug(f"[DART] {ticker} 고유번호 없음")
            return 0

        logger.info(f"[DART] {ticker} 처리 중...")

        try:
            # 2024년 사업보고서 (Q4 포함)
            year = 2024
            raw_data = self.dart.get_financial_statements(corp_code, year, "11011", "CFS")
            if raw_data:
                parsed = self.dart.parse_financial_statements(raw_data)
                if parsed:
                    period_end = date(year, 12, 31)
                    exists = session.query(FinancialStatement).filter_by(
                        stock_id=stock_id,
                        period_type="annual",
                        period_end=period_end,
                        statement_type="consolidated",
                    ).first()
                    
                    if not exists:
                        stmt = FinancialStatement(
                            stock_id=stock_id,
                            period_type="annual",
                            period_end=period_end,
                            statement_type="consolidated",
                            raw_data=parsed,
                        )
                        session.add(stmt)
                        count += 1
                        results["Q4"] = True
                    else:
                        results["Q4"] = True  # 이미 존재
            
            time.sleep(0.5)

            # 2024년 분기보고서 (Q1, Q2, Q3)
            year = 2024
            
            # Q1 (1분기)
            raw_data = self.dart.get_financial_statements(corp_code, year, "11013", "CFS")
            if raw_data:
                parsed = self.dart.parse_financial_statements(raw_data)
                if parsed:
                    period_end = date(year, 3, 31)
                    exists = session.query(FinancialStatement).filter_by(
                        stock_id=stock_id,
                        period_type="quarterly",
                        period_end=period_end,
                        statement_type="consolidated",
                    ).first()
                    if not exists:
                        stmt = FinancialStatement(
                            stock_id=stock_id,
                            period_type="quarterly",
                            period_end=period_end,
                            fiscal_quarter="Q1",
                            statement_type="consolidated",
                            raw_data=parsed,
                        )
                        session.add(stmt)
                        count += 1
                        results["Q1"] = True
                    else:
                        results["Q1"] = True  # 이미 존재
            time.sleep(0.5)
            
            # Q2 (반기)
            raw_data = self.dart.get_financial_statements(corp_code, year, "11012", "CFS")
            if raw_data:
                parsed = self.dart.parse_financial_statements(raw_data)
                if parsed:
                    period_end = date(year, 6, 30)
                    exists = session.query(FinancialStatement).filter_by(
                        stock_id=stock_id,
                        period_type="quarterly",
                        period_end=period_end,
                        statement_type="consolidated",
                    ).first()
                    if not exists:
                        stmt = FinancialStatement(
                            stock_id=stock_id,
                            period_type="quarterly",
                            period_end=period_end,
                            fiscal_quarter="Q2",
                            statement_type="consolidated",
                            raw_data=parsed,
                        )
                        session.add(stmt)
                        count += 1
                        results["Q2"] = True
                    else:
                        results["Q2"] = True  # 이미 존재
            time.sleep(0.5)
            
            # Q3 (3분기)
            raw_data = self.dart.get_financial_statements(corp_code, year, "11014", "CFS")
            if raw_data:
                parsed = self.dart.parse_financial_statements(raw_data)
                if parsed:
                    period_end = date(year, 9, 30)
                    exists = session.query(FinancialStatement).filter_by(
                        stock_id=stock_id,
                        period_type="quarterly",
                        period_end=period_end,
                        statement_type="consolidated",
                    ).first()
                    if not exists:
                        stmt = FinancialStatement(
                            stock_id=stock_id,
                            period_type="quarterly",
                            period_end=period_end,
                            fiscal_quarter="Q3",
                            statement_type="consolidated",
                            raw_data=parsed,
                        )
                        session.add(stmt)
                        count += 1
                        results["Q3"] = True
                    else:
                        results["Q3"] = True  # 이미 존재
            time.sleep(0.5)
            
            # 결과 요약
            success_quarters = [q for q, success in results.items() if success]
            if success_quarters:
                logger.info(f"[DART] {ticker} 완료: {', '.join(success_quarters)} ({count}개 신규)")
            else:
                logger.warning(f"[DART] {ticker} 데이터 없음")

        except Exception as e:
            import traceback
            logger.error(f"[DART] {ticker} 오류: {e}")
            logger.error(traceback.format_exc())

        return count

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
                        period_type="quarterly",
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
                        period_type="quarterly",
                        period_end=period_end,
                        statement_type=statement_type,
                        data=data_dict,
                    )
                    session.add(stmt)
                    count += 1

        except Exception as e:
            logger.debug(f"[yfinance] {ticker} ({yf_symbol}) 실패: {e}")

        return count
