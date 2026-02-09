"""재무 데이터 수집기

MarketSenseAI Fundamentals Agent에 필요한 데이터:
1. 재무제표 (Income Statement, Balance Sheet, Cash Flow) - yfinance
2. SEC 10-K/10-Q 공시 - SEC EDGAR API
3. Earnings Call 트랜스크립트 - RapidAPI

논문 Section 3.2 (Enhanced Fundamentals Analysis):
"The updated agent now processes disclosures, footnotes, and strategic
insights found in 10-Q and 10-K SEC filings. Moreover, it accounts for
the qualitative dimension of earnings call transcripts."
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
from src.storage.models import Stock, FinancialStatement, SECFiling, EarningsCall

logger = logging.getLogger("marketsense")


class FundamentalsCollector(BaseCollector):
    """재무 데이터 수집기"""

    SEC_FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"
    SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    SEC_FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.fund_config = config.get("fundamentals", {})
        self.quarters = self.fund_config.get("financial_statements", {}).get("quarters", 5)

        self.sec_headers = {
            "User-Agent": "MarketSenseAI research@example.com",
            "Accept-Encoding": "gzip, deflate",
        }

    def collect(self, tickers: list = None, **kwargs):
        """모든 재무 데이터 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            try:
                if not tickers:
                    tickers = [s.ticker for s in session.query(Stock).filter_by(is_active=True).all()]

                for ticker in tickers:
                    stock = session.query(Stock).filter_by(ticker=ticker).first()
                    if not stock:
                        continue

                    # 1. 재무제표 (yfinance)
                    total += self._collect_financial_statements(session, stock)

                    # 2. SEC Filings
                    if self.fund_config.get("sec_filings", {}).get("enabled", True):
                        total += self._collect_sec_filings(session, stock)

                    # 3. Earnings Calls
                    if self.fund_config.get("earnings_calls", {}).get("enabled", True):
                        total += self._collect_earnings_calls(session, stock)

                    time.sleep(0.5)

                self._finish_run(run, total)
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

    # ─────────────────────────────────────
    # Financial Statements (yfinance)
    # ─────────────────────────────────────
    def _collect_financial_statements(self, session, stock: Stock) -> int:
        """yfinance로 재무제표 수집"""
        count = 0
        try:
            yf_stock = yf.Ticker(stock.ticker)

            statements = {
                "income": ("quarterly_financials", "quarterly"),
                "balance_sheet": ("quarterly_balance_sheet", "quarterly"),
                "cash_flow": ("quarterly_cashflow", "quarterly"),
            }

            for stmt_type, (attr_name, period_type) in statements.items():
                try:
                    df = getattr(yf_stock, attr_name)
                    if df is None or df.empty:
                        continue

                    for col_date in df.columns[:self.quarters]:
                        period_end = col_date.date() if hasattr(col_date, 'date') else col_date

                        # 중복 체크
                        exists = session.query(FinancialStatement).filter_by(
                            stock_id=stock.id,
                            statement_type=stmt_type,
                            period_end=period_end,
                            period_type=period_type,
                        ).first()
                        if exists:
                            continue

                        col_data = df[col_date].dropna()
                        raw = {str(k): float(v) if v == v else None for k, v in col_data.items()}

                        stmt = FinancialStatement(
                            stock_id=stock.id,
                            statement_type=stmt_type,
                            period_type=period_type,
                            period_end=period_end,
                            raw_data=raw,
                            revenue=raw.get("Total Revenue"),
                            net_income=raw.get("Net Income"),
                            operating_income=raw.get("Operating Income"),
                            total_assets=raw.get("Total Assets"),
                            total_liabilities=raw.get("Total Liabilities Net Minority Interest"),
                            total_equity=raw.get("Stockholders Equity") or raw.get("Total Equity Gross Minority Interest"),
                            operating_cash_flow=raw.get("Operating Cash Flow"),
                            free_cash_flow=raw.get("Free Cash Flow"),
                            eps=raw.get("Basic EPS") or raw.get("Diluted EPS"),
                            source="yfinance",
                        )
                        session.add(stmt)
                        count += 1

                except Exception as e:
                    logger.warning(f"[{stock.ticker}] {stmt_type} 수집 실패: {e}")

            logger.debug(f"[{stock.ticker}] 재무제표 {count}건")

        except Exception as e:
            logger.error(f"[{stock.ticker}] yfinance 실패: {e}")

        return count

    # ─────────────────────────────────────
    # SEC Filings (EDGAR API)
    # ─────────────────────────────────────
    def _collect_sec_filings(self, session, stock: Stock) -> int:
        """SEC EDGAR에서 10-K/10-Q 공시 수집"""
        if not stock.cik:
            # CIK 조회 시도
            stock.cik = self._lookup_cik(stock.ticker)
            if not stock.cik:
                logger.warning(f"[{stock.ticker}] CIK 번호 없음, SEC 수집 스킵")
                return 0

        count = 0
        filing_types = self.fund_config.get("sec_filings", {}).get("filing_types", ["10-K", "10-Q"])

        try:
            # SEC Submissions API
            cik_padded = stock.cik.zfill(10)
            url = self.SEC_SUBMISSIONS_URL.format(cik=cik_padded)
            resp = requests.get(url, headers=self.sec_headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            filing_dates = recent.get("filingDate", [])
            primary_docs = recent.get("primaryDocument", [])
            report_dates = recent.get("reportDate", [])

            for i in range(len(forms)):
                if forms[i] not in filing_types:
                    continue

                accession = accessions[i].replace("-", "")
                accession_full = accessions[i]

                # 중복 체크
                exists = session.query(SECFiling).filter_by(accession_number=accession_full).first()
                if exists:
                    continue

                filing = SECFiling(
                    stock_id=stock.id,
                    filing_type=forms[i],
                    accession_number=accession_full,
                    filing_date=datetime.strptime(filing_dates[i], "%Y-%m-%d").date(),
                    period_of_report=datetime.strptime(report_dates[i], "%Y-%m-%d").date() if report_dates[i] else None,
                    file_url=f"https://www.sec.gov/Archives/edgar/data/{stock.cik}/{accession}/{primary_docs[i]}",
                )

                # 본문 다운로드 시도
                try:
                    doc_url = filing.file_url
                    doc_resp = requests.get(doc_url, headers=self.sec_headers, timeout=30)
                    if doc_resp.status_code == 200:
                        filing.raw_text = doc_resp.text[:500000]  # 최대 500KB
                        filing.file_size_bytes = len(doc_resp.content)
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning(f"[{stock.ticker}] Filing 다운로드 실패: {e}")

                session.add(filing)
                count += 1

                if count >= 10:  # 종목당 최대 10건
                    break

            time.sleep(0.5)  # SEC rate limit
            logger.debug(f"[{stock.ticker}] SEC filings {count}건")

        except Exception as e:
            logger.error(f"[{stock.ticker}] SEC EDGAR 실패: {e}")

        return count

    def _lookup_cik(self, ticker: str) -> Optional[str]:
        """티커로 CIK 번호 조회"""
        try:
            url = "https://www.sec.gov/cgi-bin/browse-edgar"
            params = {"action": "getcompany", "company": ticker, "type": "", "dateb": "",
                      "owner": "include", "count": 1, "search_text": "", "action": "getcompany",
                      "CIK": ticker, "output": "atom"}
            resp = requests.get(url, params=params, headers=self.sec_headers, timeout=10)
            if resp.status_code == 200 and "CIK" in resp.text:
                import re
                match = re.search(r'CIK=(\d+)', resp.text)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # 대안: SEC company_tickers.json
        try:
            resp = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=self.sec_headers, timeout=10
            )
            data = resp.json()
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    return str(entry["cik_str"])
        except Exception:
            pass

        return None

    # ─────────────────────────────────────
    # Earnings Calls (RapidAPI)
    # ─────────────────────────────────────
    def _collect_earnings_calls(self, session, stock: Stock) -> int:
        """Earnings Call 트랜스크립트 수집"""
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            logger.warning("RAPIDAPI_KEY 미설정, Earnings Call 스킵")
            return 0

        count = 0
        try:
            # Seeking Alpha Earnings Calendar via RapidAPI
            url = "https://seeking-alpha.p.rapidapi.com/transcripts/v2/list"
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com",
            }
            params = {"id": stock.ticker, "size": 5}

            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[{stock.ticker}] Earnings API {resp.status_code}")
                return 0

            data = resp.json()
            transcripts = data.get("data", [])

            for t in transcripts:
                attrs = t.get("attributes", {})
                call_date_str = attrs.get("publishOn", "")

                try:
                    call_date = datetime.fromisoformat(call_date_str.replace("Z", "+00:00")).date()
                except (ValueError, AttributeError):
                    continue

                # 중복 체크
                exists = session.query(EarningsCall).filter_by(
                    stock_id=stock.id, call_date=call_date
                ).first()
                if exists:
                    continue

                # 트랜스크립트 상세 가져오기
                transcript_id = t.get("id")
                full_text = self._fetch_transcript_detail(api_key, transcript_id)

                ec = EarningsCall(
                    stock_id=stock.id,
                    call_date=call_date,
                    title=attrs.get("title", ""),
                    full_transcript=full_text,
                    source="rapidapi",
                    source_url=f"https://seekingalpha.com/article/{transcript_id}",
                )
                session.add(ec)
                count += 1

            time.sleep(1)
            logger.debug(f"[{stock.ticker}] Earnings calls {count}건")

        except Exception as e:
            logger.error(f"[{stock.ticker}] Earnings Call 수집 실패: {e}")

        return count

    def _fetch_transcript_detail(self, api_key: str, transcript_id: str) -> Optional[str]:
        """개별 트랜스크립트 본문 가져오기"""
        try:
            url = f"https://seeking-alpha.p.rapidapi.com/transcripts/v2/get-details"
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com",
            }
            resp = requests.get(url, headers=headers, params={"id": transcript_id}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("data", {}).get("attributes", {}).get("content", "")
                return content
        except Exception as e:
            logger.warning(f"트랜스크립트 상세 실패: {e}")
        return None
