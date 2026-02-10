"""증권사 리포트 수집기

네이버 금융에서 증권사 리포트 수집
- 투자의견 (매수/중립/매도)
- 목표주가
- 애널리스트 의견
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from src.storage.models import Stock, ResearchReport

logger = logging.getLogger("marketsense")


class ResearchReportCollector(BaseCollector):
    """증권사 리포트 수집기"""

    def __init__(self, config: Dict[str, Any], db):
        super().__init__(config, db)
        self.lookback_days = config.get("research_report", {}).get("lookback_days", 90)

    def collect(self, tickers: List[str] = None, **kwargs) -> int:
        """리포트 수집"""
        total = 0

        with self.db.get_session() as session:
            run = self._start_run(session)

            try:
                # 수집 대상 종목
                if tickers:
                    stocks = (
                        session.query(Stock)
                        .filter(Stock.ticker.in_(tickers))
                        .all()
                    )
                else:
                    stocks = session.query(Stock).all()

                logger.info(f"[ResearchReport] {len(stocks)}개 종목 수집 시작")

                for idx, stock in enumerate(stocks):
                    if idx % 100 == 0 and idx > 0:
                        logger.info(f"[ResearchReport] 진행: {idx}/{len(stocks)} ({total}건)")

                    try:
                        count = self._collect_stock_reports(session, stock)
                        total += count

                        # Rate limit
                        time.sleep(0.5)

                    except Exception as e:
                        logger.debug(f"[ResearchReport] {stock.ticker} 실패: {e}")
                        continue

                self._finish_run(run, total)

            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

        return total

    def _collect_stock_reports(self, session, stock: Stock) -> int:
        """종목별 리포트 수집 (네이버 금융)"""
        count = 0

        try:
            ticker = stock.ticker

            # 네이버 금융 리포트 페이지
            url = "https://finance.naver.com/research/company_list.naver"

            params = {
                "keyword": "",
                "brokerCode": "",
                "writeFromDate": "",
                "writeToDate": "",
                "searchType": "itemCode",
                "itemCode": ticker,
                "page": "1",
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://finance.naver.com/",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code != 200:
                return 0

            soup = BeautifulSoup(resp.text, "html.parser")

            # 리포트 테이블
            table = soup.select_one("table.type_1")

            if not table:
                return 0

            rows = table.select("tr")[2:]  # 헤더 제외

            for row in rows:
                try:
                    cols = row.select("td")

                    if len(cols) < 5:
                        continue

                    # 종목명 (컬럼 0) - 건너뜀
                    
                    # 제목 및 링크 (컬럼 1)
                    title_elem = cols[1].select_one("a")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    detail_link = title_elem.get("href", "")

                    # 증권사 (컬럼 2)
                    firm = cols[2].get_text(strip=True)
                    if not firm:
                        continue

                    # PDF 링크 (컬럼 3)
                    pdf_elem = cols[3].select_one("a")
                    pdf_url = pdf_elem.get("href", "") if pdf_elem else None

                    # 날짜 (컬럼 4)
                    date_elem = cols[4].get_text(strip=True) if len(cols) > 4 else None

                    if date_elem:
                        try:
                            # "26.02.10" 형식
                            report_date = datetime.strptime(date_elem, "%y.%m.%d").date()
                        except:
                            try:
                                # "2026.02.10" 형식
                                report_date = datetime.strptime(date_elem, "%Y.%m.%d").date()
                            except:
                                continue
                    else:
                        continue
                    
                    # 애널리스트, 투자의견, 목표주가는 상세 페이지에서만 제공
                    # 일단 None으로 저장
                    analyst = None
                    opinion = None
                    target_price = None

                    # Lookback 체크
                    cutoff = datetime.now().date() - timedelta(days=self.lookback_days)
                    if report_date < cutoff:
                        break  # 오래된 리포트는 중단

                    # 중복 확인
                    existing = (
                        session.query(ResearchReport)
                        .filter_by(
                            stock_id=stock.id,
                            firm=firm,
                            report_date=report_date,
                            title=title,
                        )
                        .first()
                    )

                    if existing:
                        continue

                    # 저장
                    report = ResearchReport(
                        stock_id=stock.id,
                        firm=firm,
                        analyst=analyst,
                        report_date=report_date,
                        opinion=opinion,
                        target_price=target_price,
                        title=title,
                        pdf_url=pdf_url,
                        source_url=url,
                    )

                    session.add(report)
                    count += 1

                except Exception as e:
                    logger.debug(f"[ResearchReport] 행 파싱 실패: {e}")
                    continue

            session.flush()

        except Exception as e:
            logger.debug(f"[ResearchReport] {stock.ticker} 수집 실패: {e}")

        return count
