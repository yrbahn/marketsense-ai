"""블로그 투자 분석글 수집기

네이버 블로그 검색 API에서 종목 분석글 수집
- 종목명 + "분석" 키워드로 검색
- 신뢰도 필터링 (길이, 광고성 키워드)
- 참고용 데이터로 활용
"""
import logging
import time
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import re

from .base_collector import BaseCollector
from src.storage.models import Stock, BlogPost

logger = logging.getLogger("marketsense")


# 광고성 키워드 (제외 대상)
AD_KEYWORDS = [
    "무료", "추천주", "급등주", "대박주", "수익인증",
    "카톡", "텔레그램", "단톡방", "유료방", "구독",
    "리딩", "종목추천", "무료체험", "상담", "문의",
]


class BlogCollector(BaseCollector):
    """블로그 분석글 수집기"""

    def __init__(self, config: Dict[str, Any], db):
        super().__init__(config, db)
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.lookback_days = config.get("blog", {}).get("lookback_days", 30)
        self.min_length = config.get("blog", {}).get("min_length", 300)  # 최소 글자수
        
        if not self.client_id or not self.client_secret:
            logger.warning("[Blog] 네이버 API 키가 없습니다. 블로그 수집 불가")

    def collect(self, tickers: List[str] = None, **kwargs) -> int:
        """블로그 수집"""
        if not self.client_id:
            logger.warning("[Blog] API 키 없음. 건너뜀")
            return 0

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

                logger.info(f"[Blog] {len(stocks)}개 종목 수집 시작")

                for idx, stock in enumerate(stocks):
                    if idx % 50 == 0 and idx > 0:
                        logger.info(f"[Blog] 진행: {idx}/{len(stocks)} ({total}건)")

                    try:
                        count = self._collect_stock_blogs(session, stock)
                        total += count

                        # Rate limit
                        time.sleep(0.5)

                    except Exception as e:
                        logger.debug(f"[Blog] {stock.ticker} 실패: {e}")
                        continue

                # 실시간 벡터화
                if total > 0:
                    try:
                        logger.info(f"[Blog] 즉시 벡터화 시작: {total}건")
                        self._vectorize_collected_blogs(session, run.started_at)
                        logger.info(f"[Blog] 벡터화 완료")
                    except Exception as ve:
                        logger.error(f"[Blog] 벡터화 실패: {ve}")

                self._finish_run(run, total)

            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

        return total

    def _collect_stock_blogs(self, session, stock: Stock) -> int:
        """종목별 블로그 수집"""
        count = 0

        try:
            # 검색 쿼리: 종목명 + 분석
            query = f"{stock.name} 분석"

            # 네이버 블로그 검색 API
            url = "https://openapi.naver.com/v1/search/blog.json"

            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            }

            params = {
                "query": query,
                "display": 20,  # 최대 20개
                "sort": "date",  # 최신순
            }

            resp = requests.get(url, headers=headers, params=params, timeout=10)

            if resp.status_code != 200:
                logger.debug(f"[Blog] {stock.ticker} API 오류: {resp.status_code}")
                return 0

            data = resp.json()
            items = data.get("items", [])

            for item in items:
                try:
                    # 제목
                    title = self._clean_html(item.get("title", ""))

                    # 본문 요약
                    description = self._clean_html(item.get("description", ""))

                    # URL
                    blog_url = item.get("link", "")

                    # 블로거명
                    blogger_name = item.get("bloggername", "")

                    # 작성일 (YYYYMMDD)
                    post_date_str = item.get("postdate", "")
                    if post_date_str:
                        post_date = datetime.strptime(post_date_str, "%Y%m%d").date()
                    else:
                        continue

                    # Lookback 체크
                    cutoff = datetime.now().date() - timedelta(days=self.lookback_days)
                    if post_date < cutoff:
                        continue

                    # 광고성 필터
                    if self._is_ad(title, description):
                        continue

                    # 길이 필터
                    word_count = len(description)
                    if word_count < self.min_length:
                        continue

                    # 중복 확인
                    existing = (
                        session.query(BlogPost)
                        .filter_by(stock_id=stock.id, blog_url=blog_url)
                        .first()
                    )

                    if existing:
                        continue

                    # 품질 점수 계산
                    quality_score = self._calculate_quality(title, description)

                    # 저장
                    blog_post = BlogPost(
                        stock_id=stock.id,
                        blog_url=blog_url,
                        blogger_name=blogger_name,
                        post_date=post_date,
                        title=title,
                        description=description,
                        word_count=word_count,
                        quality_score=quality_score,
                    )

                    session.add(blog_post)
                    count += 1

                except Exception as e:
                    logger.debug(f"[Blog] 항목 파싱 실패: {e}")
                    continue

            session.flush()

        except Exception as e:
            logger.debug(f"[Blog] {stock.ticker} 수집 실패: {e}")

        return count

    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거"""
        # <b>, </b> 등 태그 제거
        text = re.sub(r"<[^>]+>", "", text)
        # HTML 엔티티 처리
        text = text.replace("&quot;", '"')
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text.strip()

    def _is_ad(self, title: str, description: str) -> bool:
        """광고성 글 필터링"""
        text = (title + " " + description).lower()
        
        for keyword in AD_KEYWORDS:
            if keyword in text:
                return True
        
        return False

    def _calculate_quality(self, title: str, description: str) -> float:
        """품질 점수 계산 (0-1)"""
        score = 0.5  # 기본 점수

        # 길이 보너스
        length = len(description)
        if length > 500:
            score += 0.1
        if length > 1000:
            score += 0.1

        # 전문성 키워드
        professional_keywords = [
            "실적", "재무제표", "PER", "PBR", "ROE",
            "영업이익", "순이익", "매출", "자산",
            "부채비율", "밸류에이션", "목표주가",
        ]

        for kw in professional_keywords:
            if kw in title or kw in description:
                score += 0.05

        # 최대 1.0
        return min(score, 1.0)

    def _vectorize_collected_blogs(self, session, started_at):
        """수집된 블로그 즉시 벡터화
        
        블로그는 뉴스 컬렉션에 추가 (유사한 콘텐츠)
        """
        from src.rag.vector_store import VectorStore
        
        # 이번 수집 이후 블로그만 가져오기
        new_blogs = session.query(BlogPost).filter(
            BlogPost.collected_at >= started_at
        ).all()
        
        if not new_blogs:
            return
        
        # 배치 단위로 벡터화 (뉴스 형식으로 변환)
        vs = VectorStore()
        batch_size = 1000
        
        for i in range(0, len(new_blogs), batch_size):
            batch = new_blogs[i:i + batch_size]
            blog_data = []
            
            for blog in batch:
                stock = session.query(Stock).filter_by(id=blog.stock_id).first()
                ticker = stock.ticker if stock else ''
                
                # 블로그를 뉴스 형식으로 변환
                blog_data.append({
                    'id': f"blog_{blog.id}",  # blog_ 접두사로 구분
                    'ticker': ticker,
                    'title': blog.title or '',
                    'content': blog.description or '',
                    'published_at': blog.post_date,
                    'source': f'blog_{blog.blogger_name}',  # 블로거명
                    'url': blog.blog_url or ''
                })
            
            vs.add_news(blog_data)  # 뉴스 컬렉션에 추가
            logger.info(f"  → 블로그 벡터화: {i + len(batch)}/{len(new_blogs)}")
