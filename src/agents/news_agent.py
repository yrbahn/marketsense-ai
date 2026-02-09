"""News Agent - 뉴스 분석 및 감성 분류

논문 Section 3.1: Enhanced News Analysis
- 뉴스 기사 수집 및 감성 분석
- 긍정/부정/중립 분류
- 주요 이벤트 추출
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .base_agent import BaseAgent
from src.storage.models import Stock, NewsArticle

logger = logging.getLogger("marketsense")


class NewsAgent(BaseAgent):
    """뉴스 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 한국 증시 뉴스 분석 전문가입니다.

역할:
- 뉴스 기사를 읽고 주가에 미치는 영향을 분석합니다
- 감성(긍정/부정/중립)을 분류하고 신뢰도를 제공합니다
- 주요 이벤트와 키워드를 추출합니다

출력 형식:
{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.0-1.0,
  "impact": "high|medium|low",
  "summary": "한 문장 요약",
  "key_events": ["이벤트1", "이벤트2"],
  "reasoning": "분석 근거"
}
"""

    def analyze(self, ticker: str, lookback_days: int = 7) -> Dict[str, Any]:
        """종목 뉴스 분석"""
        logger.info(f"[NewsAgent] {ticker} 뉴스 분석 시작 (최근 {lookback_days}일)")

        with self.db.get_session() as session:
            # 종목 정보
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return {"error": f"종목 {ticker}를 찾을 수 없습니다"}

            # 최근 뉴스 가져오기
            cutoff = datetime.now() - timedelta(days=lookback_days)
            news_list = (
                session.query(NewsArticle)
                .filter(
                    NewsArticle.ticker == ticker,
                    NewsArticle.published_at >= cutoff,
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(20)
                .all()
            )

            if not news_list:
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "news_count": 0,
                    "sentiment": "neutral",
                    "message": "최근 뉴스가 없습니다",
                }

            # 뉴스 요약
            news_texts = []
            for idx, news in enumerate(news_list[:10], 1):
                date_str = news.published_at.strftime("%Y-%m-%d") if news.published_at else "날짜 미상"
                news_texts.append(f"{idx}. [{date_str}] {news.title}")
                if news.summary:
                    news_texts.append(f"   요약: {news.summary[:150]}...")

            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})
최근 {lookback_days}일 뉴스 ({len(news_list)}건):

{chr(10).join(news_texts)}

위 뉴스들을 종합 분석하여 JSON 형식으로 답변하세요.
"""

            try:
                response_text = self.generate(prompt)
                # JSON 파싱 시도
                import json
                # ```json ``` 제거
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())
                result["ticker"] = ticker
                result["stock_name"] = stock.name
                result["news_count"] = len(news_list)
                result["analyzed_at"] = datetime.now().isoformat()

                logger.info(
                    f"[NewsAgent] {ticker} 분석 완료: {result.get('sentiment')} "
                    f"(신뢰도 {result.get('confidence', 0):.2f})"
                )

                return result

            except Exception as e:
                logger.error(f"[NewsAgent] {ticker} 분석 실패: {e}")
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "news_count": len(news_list),
                    "error": str(e),
                }
