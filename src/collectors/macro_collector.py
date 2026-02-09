"""매크로 경제 데이터 수집기

MarketSenseAI Macroeconomic Agent에 필요한 데이터:
1. 경제 지표 시계열 (FRED API) - GDP, CPI, 금리, 실업률 등
2. 중앙은행 보고서/연설 (Fed, ECB RSS)
3. 기관 리포트 (IMF, BIS, 투자은행)

논문 Section 3.3 (Macroeconomic Analysis):
"These updates address known limitations of LLMs by systematically
incorporating diverse macroeconomic data from authoritative sources."

Data Injection Pipeline (Section 3.3.1):
1. Parse documents → 2. Extract metadata → 3. Filter relevance
→ 4. Clean & summarize → 5. Store + vector index
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
    """매크로 경제 데이터 수집기"""

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
                for source_cfg in self.macro_config.get("sources", []):
                    name = source_cfg["name"]
                    if name == "fred":
                        total += self._collect_fred(session, source_cfg)
                    elif name == "imf":
                        total += self._collect_imf(session, source_cfg)
                    elif name == "fed_speeches":
                        total += self._collect_rss_reports(session, source_cfg, "fed")
                    elif name == "ecb_publications":
                        total += self._collect_rss_reports(session, source_cfg, "ecb")
                    elif name == "institutional_reports":
                        total += self._collect_institutional(session, source_cfg)

                self._finish_run(run, total)
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

    # ─────────────────────────────────────
    # FRED API (경제 지표 시계열)
    # ─────────────────────────────────────
    def _collect_fred(self, session, source_cfg: Dict) -> int:
        """FRED에서 경제 지표 수집"""
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            logger.warning("FRED_API_KEY 미설정, FRED 데이터 스킵")
            return 0

        base_url = "https://api.stlouisfed.org/fred/series/observations"
        series_list = source_cfg.get("series", [])
        count = 0
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)

        for series_id in series_list:
            try:
                params = {
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "observation_start": start_date.strftime("%Y-%m-%d"),
                    "observation_end": end_date.strftime("%Y-%m-%d"),
                }
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # 시리즈 메타데이터
                series_info = self._get_fred_series_info(api_key, series_id)
                series_name = series_info.get("title", series_id)
                unit = series_info.get("units", "")
                frequency = series_info.get("frequency", "")

                for obs in data.get("observations", []):
                    obs_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()
                    value_str = obs.get("value", ".")
                    if value_str == ".":
                        continue

                    # 중복 체크
                    exists = session.query(MacroIndicator).filter_by(
                        series_id=series_id, date=obs_date
                    ).first()
                    if exists:
                        continue

                    indicator = MacroIndicator(
                        series_id=series_id,
                        series_name=series_name,
                        date=obs_date,
                        value=float(value_str),
                        unit=unit,
                        frequency=frequency,
                        source="fred",
                    )
                    session.add(indicator)
                    count += 1

                time.sleep(0.3)
                logger.debug(f"[FRED] {series_id}: {count}건")

            except Exception as e:
                logger.error(f"[FRED] {series_id} 실패: {e}")

        logger.info(f"[FRED] 총 {count}건 수집")
        return count

    def _get_fred_series_info(self, api_key: str, series_id: str) -> Dict:
        """FRED 시리즈 메타정보 조회"""
        try:
            url = "https://api.stlouisfed.org/fred/series"
            params = {"series_id": series_id, "api_key": api_key, "file_type": "json"}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                series = resp.json().get("seriess", [{}])
                return series[0] if series else {}
        except Exception:
            pass
        return {}

    # ─────────────────────────────────────
    # IMF Data
    # ─────────────────────────────────────
    def _collect_imf(self, session, source_cfg: Dict) -> int:
        """IMF 데이터 수집"""
        count = 0
        try:
            # IMF World Economic Outlook 데이터
            base_url = source_cfg.get("base_url", "https://www.imf.org/external/datamapper/api/v1")

            # 주요 글로벌 지표
            indicators = ["NGDP_RPCH", "PCPIPCH", "LUR"]  # GDP성장률, 인플레이션, 실업률
            for ind_id in indicators:
                try:
                    url = f"{base_url}/{ind_id}/USA"
                    resp = requests.get(url, timeout=15)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    values = data.get("values", {}).get(ind_id, {}).get("USA", {})

                    for year_str, value in values.items():
                        obs_date = datetime.strptime(f"{year_str}-12-31", "%Y-%m-%d").date()
                        series_key = f"IMF_{ind_id}_USA"

                        exists = session.query(MacroIndicator).filter_by(
                            series_id=series_key, date=obs_date
                        ).first()
                        if exists:
                            continue

                        indicator = MacroIndicator(
                            series_id=series_key,
                            series_name=f"IMF {ind_id} USA",
                            date=obs_date,
                            value=float(value),
                            frequency="annual",
                            source="imf",
                        )
                        session.add(indicator)
                        count += 1

                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"[IMF] {ind_id} 실패: {e}")

        except Exception as e:
            logger.error(f"[IMF] 수집 실패: {e}")

        logger.info(f"[IMF] 총 {count}건 수집")
        return count

    # ─────────────────────────────────────
    # Central Bank Reports (RSS)
    # ─────────────────────────────────────
    def _collect_rss_reports(self, session, source_cfg: Dict, source_name: str) -> int:
        """RSS 피드에서 중앙은행 보고서/연설 수집"""
        url = source_cfg.get("url", "")
        if not url:
            return 0

        count = 0
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:50]:
                link = entry.get("link", "")
                if not link:
                    continue

                # 중복 체크
                exists = session.query(MacroReport).filter_by(source_url=link).first()
                if exists:
                    continue

                # 날짜 파싱
                pub_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_at = datetime(*entry.published_parsed[:6])

                # 본문 가져오기 시도
                raw_text = self._fetch_report_text(link)

                report = MacroReport(
                    title=entry.get("title", ""),
                    source_name=source_name,
                    source_url=link,
                    published_at=pub_at,
                    report_type="speech" if source_name == "fed" else "publication",
                    raw_text=raw_text,
                    author=entry.get("author", ""),
                    tags=[source_name, "central_bank"],
                )
                session.add(report)
                count += 1

            logger.info(f"[{source_name.upper()}] {count}건 수집")

        except Exception as e:
            logger.error(f"[{source_name.upper()}] RSS 수집 실패: {e}")

        return count

    # ─────────────────────────────────────
    # Institutional Reports
    # ─────────────────────────────────────
    def _collect_institutional(self, session, source_cfg: Dict) -> int:
        """투자은행/기관 보고서 수집 (스크래핑)"""
        count = 0
        sources = source_cfg.get("sources", [])

        # 공개 리서치 RSS/페이지
        institutional_feeds = {
            "blackrock": "https://www.blackrock.com/corporate/insights/blackrock-investment-institute",
            "jpmorgan": "https://am.jpmorgan.com/us/en/asset-management/institutional/insights/market-insights/",
        }

        for inst_name in sources:
            url = institutional_feeds.get(inst_name)
            if not url:
                continue

            try:
                # trafilatura로 페이지 텍스트 추출 시도
                raw_text = self._fetch_report_text(url)
                if not raw_text or len(raw_text) < 100:
                    continue

                exists = session.query(MacroReport).filter_by(source_url=url).first()
                if exists:
                    # 기존 레코드 업데이트
                    exists.raw_text = raw_text
                    exists.collected_at = datetime.utcnow()
                else:
                    report = MacroReport(
                        title=f"{inst_name.title()} Market Insights",
                        source_name=inst_name,
                        source_url=url,
                        published_at=datetime.utcnow(),
                        report_type="research",
                        raw_text=raw_text,
                        tags=[inst_name, "institutional"],
                    )
                    session.add(report)
                    count += 1

                time.sleep(2)

            except Exception as e:
                logger.error(f"[{inst_name}] 수집 실패: {e}")

        logger.info(f"[Institutional] 총 {count}건 수집")
        return count

    def _fetch_report_text(self, url: str) -> Optional[str]:
        """URL에서 본문 텍스트 추출"""
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                return text
        except ImportError:
            pass

        # fallback: requests + beautifulsoup
        try:
            from bs4 import BeautifulSoup
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 MarketSenseAI Research Bot"
            })
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                return soup.get_text(separator="\n", strip=True)[:100000]
        except Exception:
            pass

        return None
