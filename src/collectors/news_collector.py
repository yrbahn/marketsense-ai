"""뉴스 데이터 수집기

MarketSenseAI News Agent에 필요한 데이터:
- 종목별 금융 뉴스 (제목, 요약, 본문, 소스, 날짜)
- 뉴스 소스: Finnhub API, NewsAPI, RSS 피드

논문 Section 3.1 (News Agent):
"Each day's raw text is first distilled into a concise summary,
which is then integrated with previous summaries to form a
progressive narrative of recent developments."
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
from src.storage.models import NewsArticle, Stock

logger = logging.getLogger("marketsense")


class NewsCollector(BaseCollector):
    """금융 뉴스 수집기 (Finnhub, NewsAPI, RSS)"""

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.news_config = config.get("news", {})
        self.lookback_days = self.news_config.get("lookback_days", 7)
        self.max_articles = self.news_config.get("max_articles_per_stock", 50)
        self.pages_to_collect = self.news_config.get("pages_to_collect", 5)

    def collect(self, tickers: list = None, **kwargs):
        """모든 소스에서 뉴스 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            try:
                if not tickers:
                    tickers = [s.ticker for s in session.query(Stock).filter_by(is_active=True).all()]

                # 한국 종목 감지 (6자리 숫자)
                kr_tickers = [t for t in tickers if t.isdigit() and len(t) == 6]
                us_tickers = [t for t in tickers if t not in kr_tickers]

                # 한국 종목: 네이버 금융 뉴스 + 검색 API
                if kr_tickers:
                    total += self._collect_naver_finance(session, kr_tickers)
                    
                    # 네이버 검색 API로 추가 뉴스 수집 (쿼리 확장)
                    naver_client_id = os.getenv("NAVER_CLIENT_ID")
                    naver_client_secret = os.getenv("NAVER_CLIENT_SECRET")
                    
                    if naver_client_id and naver_client_secret:
                        total += self._collect_naver_search(session, kr_tickers)

                # 미국 종목: 기존 소스
                if us_tickers:
                    for source_cfg in self.news_config.get("sources", []):
                        source_name = source_cfg["name"]
                        if source_name == "finnhub":
                            total += self._collect_finnhub(session, us_tickers)
                        elif source_name == "newsapi":
                            total += self._collect_newsapi(session, us_tickers)
                        elif source_name == "rss_feeds":
                            total += self._collect_rss(session, source_cfg.get("feeds", []))

                self._finish_run(run, total)
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

    # ─────────────────────────────────────
    # Naver Stock API (한국 종목)
    # ─────────────────────────────────────
    def _collect_naver_finance(self, session, tickers: List[str]) -> int:
        """네이버 증권 모바일 API로 한국 종목 뉴스 수집"""
        count = 0
        total_tickers = len(tickers)
        api_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

        for idx, ticker in enumerate(tickers):
            if idx % 100 == 0 and idx > 0:
                logger.info(f"[NaverAPI] 진행: {idx}/{total_tickers} ({count}건 수집)")

            stock = session.query(Stock).filter_by(ticker=ticker).first()
            stock_id = stock.id if stock else None

            try:
                cutoff = datetime.now() - timedelta(days=self.lookback_days)
                
                # 여러 페이지 수집
                for page in range(1, self.pages_to_collect + 1):
                    url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize=20&page={page}"
                    resp = requests.get(url, headers=api_headers, timeout=10)

                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    if not isinstance(data, list) or len(data) == 0:
                        break

                    for group in data:
                        items = group.get("items", [])
                        for article in items:
                            article_id = article.get("id", "")
                            title = article.get("title") or article.get("titleFull", "")
                            body = article.get("body", "")
                            office = article.get("officeName", "")
                            dt_str = article.get("datetime", "")

                            if not title or not article_id:
                                continue

                            # 날짜 파싱 (YYYYMMDDHHmm)
                            pub_at = None
                            try:
                                pub_at = datetime.strptime(dt_str, "%Y%m%d%H%M")
                            except (ValueError, TypeError):
                                pass

                            if pub_at and pub_at < cutoff:
                                continue

                            # 네이버 뉴스 URL 생성
                            office_id = article.get("officeId", "")
                            article_num = article.get("articleId", "")
                            news_url = f"https://n.news.naver.com/mnews/article/{office_id}/{article_num}"

                            # 중복 체크
                            exists = session.query(NewsArticle).filter_by(url=news_url).first()
                            if exists:
                                continue

                            news = NewsArticle(
                                stock_id=stock_id,
                                ticker=ticker,
                                title=title,
                                summary=body[:500] if body else None,
                                url=news_url,
                                source="naver",
                                author=office,
                                published_at=pub_at,
                                source_id=article_id,
                                category="finance",
                                related_tickers=[ticker],
                            )
                            session.add(news)
                            count += 1

                # 커밋 주기적으로
                if idx % 50 == 0 and idx > 0:
                    session.flush()

                time.sleep(0.2)

            except Exception as e:
                logger.debug(f"[NaverAPI] {ticker} 실패: {e}")
                continue

        logger.info(f"[NaverAPI] 총 {count}건 수집 완료")
        return count

    # ─────────────────────────────────────
    # Finnhub API
    # ─────────────────────────────────────
    def _collect_finnhub(self, session, tickers: List[str]) -> int:
        """Finnhub에서 종목별 뉴스 수집"""
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            logger.warning("FINNHUB_API_KEY 미설정, Finnhub 뉴스 스킵")
            return 0

        base_url = "https://finnhub.io/api/v1/company-news"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        count = 0

        for ticker in tickers:
            try:
                params = {
                    "symbol": ticker,
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "token": api_key,
                }
                resp = requests.get(base_url, params=params, timeout=10)
                resp.raise_for_status()
                articles = resp.json()

                stock = session.query(Stock).filter_by(ticker=ticker).first()
                stock_id = stock.id if stock else None

                for article in articles[:self.max_articles]:
                    # 중복 체크
                    url = article.get("url", "")
                    exists = session.query(NewsArticle).filter_by(url=url).first()
                    if exists:
                        continue

                    news = NewsArticle(
                        stock_id=stock_id,
                        ticker=ticker,
                        title=article.get("headline", ""),
                        summary=article.get("summary", ""),
                        content=None,  # Finnhub은 본문 미제공
                        url=url,
                        source="finnhub",
                        source_id=str(article.get("id", "")),
                        published_at=datetime.fromtimestamp(article.get("datetime", 0)),
                        category=article.get("category", ""),
                        related_tickers=article.get("related", "").split(","),
                    )
                    session.add(news)
                    count += 1

                time.sleep(0.3)  # Rate limiting
                logger.debug(f"[Finnhub] {ticker}: {min(len(articles), self.max_articles)}건")

            except Exception as e:
                logger.error(f"[Finnhub] {ticker} 실패: {e}")
                continue

        logger.info(f"[Finnhub] 총 {count}건 수집")
        return count

    # ─────────────────────────────────────
    # NewsAPI
    # ─────────────────────────────────────
    def _collect_newsapi(self, session, tickers: List[str]) -> int:
        """NewsAPI에서 뉴스 수집"""
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            logger.warning("NEWSAPI_KEY 미설정, NewsAPI 스킵")
            return 0

        base_url = "https://newsapi.org/v2/everything"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        count = 0

        # 배치 처리 (NewsAPI는 쿼리당 최대 5종목 추천)
        from src.utils.helpers import chunk_list
        for batch in chunk_list(tickers, 5):
            query = " OR ".join(batch)
            try:
                params = {
                    "q": query,
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "language": "en",
                    "sortBy": "relevancy",
                    "pageSize": 100,
                    "apiKey": api_key,
                }
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                for article in data.get("articles", []):
                    url = article.get("url", "")
                    if not url or session.query(NewsArticle).filter_by(url=url).first():
                        continue

                    pub_at = None
                    if article.get("publishedAt"):
                        try:
                            pub_at = datetime.fromisoformat(
                                article["publishedAt"].replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    news = NewsArticle(
                        ticker=batch[0],  # 대표 티커
                        title=article.get("title", ""),
                        summary=article.get("description", ""),
                        content=article.get("content", ""),
                        url=url,
                        source="newsapi",
                        author=article.get("author", ""),
                        published_at=pub_at,
                        related_tickers=batch,
                    )
                    session.add(news)
                    count += 1

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"[NewsAPI] batch {batch[:3]}... 실패: {e}")
                continue

        logger.info(f"[NewsAPI] 총 {count}건 수집")
        return count

    # ─────────────────────────────────────
    # RSS Feeds
    # ─────────────────────────────────────
    def _collect_rss(self, session, feeds: List[str]) -> int:
        """RSS 피드에서 뉴스 수집"""
        count = 0
        cutoff = datetime.now() - timedelta(days=self.lookback_days)

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    url = entry.get("link", "")
                    if not url or session.query(NewsArticle).filter_by(url=url).first():
                        continue

                    # 날짜 파싱
                    pub_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_at = datetime(*entry.published_parsed[:6])
                        if pub_at < cutoff:
                            continue

                    news = NewsArticle(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", ""),
                        url=url,
                        source="rss",
                        published_at=pub_at,
                        category=feed_url.split("/")[-1] if "/" in feed_url else "general",
                    )
                    session.add(news)
                    count += 1

            except Exception as e:
                logger.error(f"[RSS] {feed_url} 실패: {e}")
                continue

        logger.info(f"[RSS] 총 {count}건 수집")
        return count
    
    # ─────────────────────────────────────
    # Naver Search API (쿼리 확장)
    # ─────────────────────────────────────
    def _collect_naver_search(self, session, tickers: List[str]) -> int:
        """네이버 검색 API로 확장 쿼리 뉴스 수집"""
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.warning("네이버 검색 API 키 미설정, 확장 검색 스킵")
            return 0
        
        count = 0
        total_tickers = len(tickers)
        
        for idx, ticker in enumerate(tickers):
            if idx % 50 == 0 and idx > 0:
                logger.info(f"[NaverSearch] 진행: {idx}/{total_tickers} ({count}건)")
            
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                continue
            
            # 쿼리 확장: 종목명 + 업종 키워드
            queries = self._expand_query(stock)
            
            for query in queries:
                try:
                    # 네이버 검색 API 호출
                    url = "https://openapi.naver.com/v1/search/news.json"
                    headers = {
                        "X-Naver-Client-Id": client_id,
                        "X-Naver-Client-Secret": client_secret
                    }
                    params = {
                        "query": query,
                        "display": 10,  # 최대 10개
                        "sort": "date"  # 최신순
                    }
                    
                    resp = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if resp.status_code != 200:
                        continue
                    
                    data = resp.json()
                    items = data.get("items", [])
                    
                    for item in items:
                        # 관련도 계산
                        relevance_score = self._calculate_relevance(stock, item)
                        
                        # 낮은 관련도 필터링
                        if relevance_score < 0.3:
                            continue
                        
                        # URL 정리
                        news_url = item.get("link", "")
                        if not news_url:
                            continue
                        
                        # 중복 체크
                        exists = session.query(NewsArticle).filter_by(url=news_url).first()
                        if exists:
                            continue
                        
                        # 제목/설명 HTML 태그 제거
                        title = self._clean_html(item.get("title", ""))
                        description = self._clean_html(item.get("description", ""))
                        
                        # 날짜 파싱
                        pub_date_str = item.get("pubDate", "")
                        pub_at = None
                        try:
                            # RFC 2822 형식: "Mon, 10 Feb 2026 16:00:00 +0900"
                            pub_at = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                            pub_at = pub_at.replace(tzinfo=None)  # naive datetime
                        except:
                            pass
                        
                        # 최근 30일 이내만
                        if pub_at:
                            cutoff = datetime.now() - timedelta(days=self.lookback_days)
                            if pub_at < cutoff:
                                continue
                        
                        # 뉴스 저장
                        news = NewsArticle(
                            stock_id=stock.id,
                            ticker=ticker,
                            title=title,
                            summary=description,
                            url=news_url,
                            source="naver_search",
                            published_at=pub_at,
                            category="finance",
                            related_tickers=[ticker]
                        )
                        session.add(news)
                        count += 1
                    
                    time.sleep(0.1)  # Rate limit
                    
                except Exception as e:
                    logger.debug(f"[NaverSearch] {ticker} - {query} 실패: {e}")
                    continue
            
            session.flush()
        
        logger.info(f"[NaverSearch] 총 {count}건 수집 완료")
        return count
    
    def _expand_query(self, stock: Stock) -> List[str]:
        """쿼리 확장: 종목명 + 업종 키워드"""
        queries = []
        
        # 1. 종목명
        queries.append(stock.name)
        
        # 2. 종목명 + 업종
        if stock.sector and stock.sector != '기타':
            queries.append(f"{stock.name} {stock.sector}")
        
        # 3. 업종별 키워드 (관련 뉴스)
        sector_keywords = {
            '반도체': ['반도체', '칩', '웨이퍼', 'DRAM', 'NAND'],
            '화장품': ['화장품', 'K-뷰티', '마스크팩', '스킨케어'],
            '바이오': ['바이오', '신약', '임상', '치료제'],
            '자동차': ['전기차', 'EV', '배터리', '자동차'],
            '2차전지': ['배터리', '2차전지', 'LFP', 'NCM'],
        }
        
        if stock.sector in sector_keywords:
            # 업종 키워드만 (종목이 간접적으로 언급될 수 있음)
            for keyword in sector_keywords[stock.sector][:2]:  # 상위 2개만
                queries.append(keyword)
        
        return queries
    
    def _calculate_relevance(self, stock: Stock, item: dict) -> float:
        """뉴스 관련도 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0
        
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        text = title + " " + description
        
        # 1. 종목명 직접 언급 (+0.5)
        if stock.name.lower() in text:
            score += 0.5
        
        # 2. 업종 언급 (+0.3)
        if stock.sector and stock.sector.lower() in text:
            score += 0.3
        
        # 3. 업종 관련 키워드 (+0.2)
        sector_keywords = {
            '반도체': ['반도체', '칩', '웨이퍼'],
            '화장품': ['화장품', '뷰티', '마스크팩'],
            '바이오': ['바이오', '신약', '치료제'],
        }
        
        if stock.sector in sector_keywords:
            for keyword in sector_keywords[stock.sector]:
                if keyword in text:
                    score += 0.2
                    break
        
        return min(score, 1.0)
    
    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        # <b>, </b> 등 제거
        text = re.sub(r'<[^>]+>', '', text)
        # &quot; 등 HTML 엔티티 변환
        text = text.replace("&quot;", '"')
        text = text.replace("&apos;", "'")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text
