"""매크로 경제 데이터 수집기 (한국 경제 지표)

한국 매크로 경제 데이터:
1. 한국은행 경제통계 - BOK API (향후 추가)
2. 한국은행 보고서/공지 - RSS
3. 글로벌 기관 리포트 - IMF (선택)
"""
import os
import time
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .base_collector import BaseCollector
from src.storage.database import Database
from src.storage.models import MacroReport, MacroIndicator

logger = logging.getLogger("marketsense")


class MacroCollector(BaseCollector):
    """매크로 경제 데이터 수집기 (한국)"""

    BOK_RSS_URL = "https://www.bok.or.kr/portal/bbs/B0000245/rss.do"
    ECOS_API_URL = "https://ecos.bok.or.kr/api"

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.macro_config = config.get("macro", {})
        self.cache_dir = self.macro_config.get("report_cache_dir", "./data/macro_reports")
        os.makedirs(self.cache_dir, exist_ok=True)

    def collect(self, tickers: list = None, **kwargs):
        """매크로 데이터 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            try:
                # 한국은행 보도자료/공지
                total += self._collect_bok_rss(session)

                # 한국은행 경제통계 (BOK API 키 있으면)
                if os.getenv("BOK_API_KEY"):
                    total += self._collect_bok_indicators(session)

                self._finish_run(run, total)
                logger.info(f"[Macro] 총 {total}건 수집 완료")

            except Exception as e:
                logger.error(f"[Macro] 실패: {e}")
                self._finish_run(run, total, str(e))
                raise

    def _collect_bok_rss(self, session) -> int:
        """한국은행 RSS 피드 수집"""
        count = 0
        try:
            logger.info("[BOK RSS] 한국은행 보도자료 수집 중...")
            feed = feedparser.parse(self.BOK_RSS_URL)

            cutoff = datetime.now() - timedelta(days=90)

            for entry in feed.entries:
                url = entry.get("link", "")
                title = entry.get("title", "")
                if not url or not title:
                    continue

                # 날짜 파싱
                pub_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_at = datetime(*entry.published_parsed[:6])
                    if pub_at < cutoff:
                        continue

                # 중복 체크
                exists = session.query(MacroReport).filter_by(url=url).first()
                if exists:
                    continue

                summary = entry.get("summary", "")
                report = MacroReport(
                    source="bok",
                    doc_type="press_release",
                    title=title,
                    url=url,
                    published_at=pub_at,
                    summary=summary[:1000] if summary else None,
                )
                session.add(report)
                count += 1

            logger.info(f"[BOK RSS] {count}건 수집")

        except Exception as e:
            logger.warning(f"[BOK RSS] 실패: {e}")

        return count

    def _collect_bok_indicators(self, session) -> int:
        """한국은행 경제통계시스템 API로 주요 지표 수집"""
        api_key = os.getenv("BOK_API_KEY")
        if not api_key:
            return 0

        count = 0
        # 주요 지표 코드 (예시)
        indicators = [
            {"code": "722Y001", "name": "GDP_growth"},  # GDP 성장률
            {"code": "901Y009", "name": "CPI_inflation"},  # 소비자물가지수
            {"code": "722Y003", "name": "unemployment"},  # 실업률
            {"code": "817Y002", "name": "base_rate"},  # 기준금리
        ]

        try:
            logger.info("[BOK API] 경제통계 수집 중...")
            end_date = datetime.now().strftime("%Y%m")
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y%m")

            for indicator in indicators:
                try:
                    # ECOS API 호출 (예시 URL)
                    url = f"{self.ECOS_API_URL}/StatisticSearch/{api_key}/json/kr/1/100/{indicator['code']}/M/{start_date}/{end_date}"
                    resp = requests.get(url, timeout=10)

                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    rows = data.get("StatisticSearch", {}).get("row", [])

                    for row in rows:
                        time_str = row.get("TIME", "")
                        value_str = row.get("DATA_VALUE", "")

                        if not time_str or not value_str:
                            continue

                        # 날짜 파싱 (YYYYMM)
                        try:
                            obs_date = datetime.strptime(time_str, "%Y%m").date()
                        except ValueError:
                            continue

                        # 중복 체크
                        exists = session.query(MacroIndicator).filter_by(
                            series_id=indicator["code"],
                            observation_date=obs_date,
                        ).first()
                        if exists:
                            continue

                        try:
                            value = float(value_str)
                        except ValueError:
                            continue

                        ind = MacroIndicator(
                            series_id=indicator["code"],
                            series_name=indicator["name"],
                            observation_date=obs_date,
                            value=value,
                            frequency="monthly",
                            source="bok",
                        )
                        session.add(ind)
                        count += 1

                    time.sleep(0.5)

                except Exception as e:
                    logger.debug(f"[BOK API] {indicator['code']} 실패: {e}")
                    continue

            logger.info(f"[BOK API] {count}건 수집")

        except Exception as e:
            logger.warning(f"[BOK API] 실패: {e}")

        return count
