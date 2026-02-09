"""Fundamentals Agent - 재무제표 분석

논문 Section 3.2: Enhanced Fundamentals Analysis
- 재무제표 분석
- 기업가치 평가
- 성장성, 수익성, 안정성 분석
"""
import logging
from datetime import datetime
from typing import Dict, Any

from .base_agent import BaseAgent
from src.storage.models import Stock, FinancialStatement

logger = logging.getLogger("marketsense")


class FundamentalsAgent(BaseAgent):
    """재무 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 한국 증시 재무 분석 전문가입니다.

역할:
- 재무제표를 분석하여 기업의 재무 건전성을 평가합니다
- 수익성, 성장성, 안정성을 판단합니다
- 적정 주가와 투자 가치를 평가합니다

출력 형식:
{
  "valuation": "undervalued|fair|overvalued",
  "financial_health": "excellent|good|fair|poor",
  "confidence": 0.0-1.0,
  "key_metrics": {
    "profitability": "평가",
    "growth": "평가",
    "stability": "평가"
  },
  "summary": "재무 상태 요약",
  "reasoning": "분석 근거"
}
"""

    def analyze(self, ticker: str) -> Dict[str, Any]:
        """종목 재무 분석"""
        logger.info(f"[FundamentalsAgent] {ticker} 재무 분석 시작")

        with self.db.get_session() as session:
            # 종목 정보
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return {"error": f"종목 {ticker}를 찾을 수 없습니다"}

            # 최근 재무제표
            statements = (
                session.query(FinancialStatement)
                .filter(FinancialStatement.stock_id == stock.id)
                .order_by(FinancialStatement.period_end.desc())
                .limit(4)
                .all()
            )

            if not statements:
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "error": "재무제표 데이터가 없습니다",
                }

            # 재무 데이터 요약
            financials_text = []
            for stmt in statements:
                period = stmt.period_end.strftime("%Y-%m-%d")
                stmt_type = stmt.statement_type
                financials_text.append(f"\n[{period}] {stmt_type}:")

                if stmt.data:
                    # 주요 항목만 추출
                    key_items = [
                        "Total Revenue",
                        "Net Income",
                        "Total Assets",
                        "Total Liabilities",
                        "Operating Cash Flow",
                    ]
                    for key in key_items:
                        if key in stmt.data and stmt.data[key] is not None:
                            value = stmt.data[key]
                            financials_text.append(f"  - {key}: {value:,.0f} {stmt.currency}")

            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})
업종: {stock.industry or 'N/A'}

재무제표 (최근 4분기):
{''.join(financials_text)}

위 재무 데이터를 종합 분석하여 JSON 형식으로 답변하세요.
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
                result["analyzed_at"] = datetime.now().isoformat()

                logger.info(
                    f"[FundamentalsAgent] {ticker} 분석 완료: {result.get('valuation')}"
                )

                return result

            except Exception as e:
                logger.error(f"[FundamentalsAgent] {ticker} 분석 실패: {e}")
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "error": str(e),
                }
