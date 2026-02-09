"""Dynamics Agent - 기술적 분석

논문 Section 3.4: Enhanced Market Dynamics Analysis
- 주가 추세 분석
- 기술적 지표 해석
- 지지/저항선 식별
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .base_agent import BaseAgent
from src.storage.models import Stock, PriceData, TechnicalIndicator

logger = logging.getLogger("marketsense")


class DynamicsAgent(BaseAgent):
    """기술적 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 한국 증시 기술적 분석 전문가입니다.

역할:
- 주가 차트와 기술적 지표를 분석합니다
- 추세, 지지/저항선, 매매 타이밍을 판단합니다
- 기술적 시그널을 해석합니다

출력 형식:
{
  "trend": "uptrend|downtrend|sideways",
  "signal": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "key_levels": {
    "support": [가격1, 가격2],
    "resistance": [가격1, 가격2]
  },
  "indicators_summary": "주요 지표 해석",
  "reasoning": "분석 근거"
}
"""

    def analyze(self, ticker: str, lookback_days: int = 60) -> Dict[str, Any]:
        """종목 기술적 분석"""
        logger.info(f"[DynamicsAgent] {ticker} 기술적 분석 시작")

        with self.db.get_session() as session:
            # 종목 정보
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return {"error": f"종목 {ticker}를 찾을 수 없습니다"}

            # 최근 주가 데이터
            cutoff = datetime.now() - timedelta(days=lookback_days)
            price_data = (
                session.query(PriceData)
                .filter(
                    PriceData.stock_id == stock.id,
                    PriceData.date >= cutoff.date(),
                )
                .order_by(PriceData.date.desc())
                .limit(60)
                .all()
            )

            if not price_data:
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "error": "주가 데이터가 없습니다",
                }

            # 최근 기술적 지표
            latest_indicators = (
                session.query(TechnicalIndicator)
                .filter(TechnicalIndicator.stock_id == stock.id)
                .order_by(TechnicalIndicator.date.desc())
                .first()
            )

            # 주가 요약
            recent_prices = price_data[:10]
            price_summary = [
                f"{p.date.strftime('%Y-%m-%d')}: 종가 {p.close:,.0f}원 "
                f"(거래량 {p.volume:,})" for p in recent_prices
            ]

            # 지표 요약
            indicators_text = ""
            if latest_indicators:
                indicators_text = f"""
최근 기술적 지표 ({latest_indicators.date}):
- SMA20: {latest_indicators.sma_20 or 'N/A'}
- SMA50: {latest_indicators.sma_50 or 'N/A'}
- SMA200: {latest_indicators.sma_200 or 'N/A'}
- RSI(14): {latest_indicators.rsi_14 or 'N/A'}
- MACD: {latest_indicators.macd or 'N/A'}
- 볼린저밴드: 상단 {latest_indicators.bb_upper or 'N/A'}, 하단 {latest_indicators.bb_lower or 'N/A'}
"""

            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})
현재가: {recent_prices[0].close:,.0f}원

최근 주가 흐름:
{chr(10).join(price_summary)}

{indicators_text}

위 데이터를 종합 분석하여 JSON 형식으로 답변하세요.
"""

            try:
                response_text = self.generate(prompt)
                import json

                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())
                result["ticker"] = ticker
                result["stock_name"] = stock.name
                result["current_price"] = float(recent_prices[0].close)
                result["analyzed_at"] = datetime.now().isoformat()

                logger.info(
                    f"[DynamicsAgent] {ticker} 분석 완료: {result.get('signal')} "
                    f"(신뢰도 {result.get('confidence', 0):.2f})"
                )

                return result

            except Exception as e:
                logger.error(f"[DynamicsAgent] {ticker} 분석 실패: {e}")
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "current_price": float(recent_prices[0].close),
                    "error": str(e),
                }
