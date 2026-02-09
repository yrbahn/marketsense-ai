"""Signal Agent - 최종 투자 신호 통합

논문 Section 2.3: Signal Aggregation Agent
- 4개 에이전트 결과 통합
- 최종 매수/매도/보유 신호 생성
- 신뢰도 및 리스크 평가
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger("marketsense")


class SignalAgent(BaseAgent):
    """신호 통합 에이전트"""

    SYSTEM_PROMPT = """당신은 투자 신호 통합 전문가입니다.

역할:
- 4개 분석 에이전트(뉴스, 재무, 기술적, 거시경제)의 결과를 종합합니다
- 최종 투자 신호(BUY/SELL/HOLD)를 결정합니다
- 신뢰도와 리스크를 평가합니다

출력 형식:
{
  "signal": "BUY|SELL|HOLD",
  "confidence": 0.0-1.0,
  "risk_level": "low|medium|high",
  "target_price": 숫자 (optional),
  "time_horizon": "단기|중기|장기",
  "summary": "투자 의견 요약",
  "reasoning": "통합 분석 근거"
}
"""

    def aggregate(
        self,
        ticker: str,
        news_result: Optional[Dict] = None,
        fundamentals_result: Optional[Dict] = None,
        dynamics_result: Optional[Dict] = None,
        macro_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """4개 에이전트 결과 통합"""
        logger.info(f"[SignalAgent] {ticker} 신호 통합 시작")

        # 각 에이전트 결과 요약
        analysis_summary = []

        if news_result and "error" not in news_result:
            analysis_summary.append(
                f"뉴스 분석:\n"
                f"  - 감성: {news_result.get('sentiment', 'N/A')}\n"
                f"  - 신뢰도: {news_result.get('confidence', 0):.2f}\n"
                f"  - 요약: {news_result.get('summary', 'N/A')}"
            )
        else:
            analysis_summary.append("뉴스 분석: 데이터 없음")

        if fundamentals_result and "error" not in fundamentals_result:
            analysis_summary.append(
                f"재무 분석:\n"
                f"  - 밸류에이션: {fundamentals_result.get('valuation', 'N/A')}\n"
                f"  - 재무 건전성: {fundamentals_result.get('financial_health', 'N/A')}\n"
                f"  - 요약: {fundamentals_result.get('summary', 'N/A')}"
            )
        else:
            analysis_summary.append("재무 분석: 데이터 없음")

        if dynamics_result and "error" not in dynamics_result:
            analysis_summary.append(
                f"기술적 분석:\n"
                f"  - 추세: {dynamics_result.get('trend', 'N/A')}\n"
                f"  - 신호: {dynamics_result.get('signal', 'N/A')}\n"
                f"  - 현재가: {dynamics_result.get('current_price', 'N/A'):,.0f}원"
            )
        else:
            analysis_summary.append("기술적 분석: 데이터 없음")

        if macro_result and "error" not in macro_result:
            analysis_summary.append(
                f"거시경제 분석:\n"
                f"  - 시장 전망: {macro_result.get('market_outlook', 'N/A')}\n"
                f"  - 리스크: {macro_result.get('risk_level', 'N/A')}\n"
                f"  - 요약: {macro_result.get('summary', 'N/A')}"
            )
        else:
            analysis_summary.append("거시경제 분석: 데이터 없음")

        # Gemini로 통합 분석
        prompt = f"""{self.SYSTEM_PROMPT}

종목: {ticker}

각 에이전트 분석 결과:

{chr(10).join(analysis_summary)}

위 4가지 분석을 종합하여 최종 투자 신호를 JSON 형식으로 답변하세요.
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
            result["analyzed_at"] = datetime.now().isoformat()

            # 개별 에이전트 결과 첨부
            result["agent_results"] = {
                "news": news_result,
                "fundamentals": fundamentals_result,
                "dynamics": dynamics_result,
                "macro": macro_result,
            }

            logger.info(
                f"[SignalAgent] {ticker} 통합 완료: {result.get('signal')} "
                f"(신뢰도 {result.get('confidence', 0):.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"[SignalAgent] {ticker} 통합 실패: {e}")
            return {
                "ticker": ticker,
                "error": str(e),
                "agent_results": {
                    "news": news_result,
                    "fundamentals": fundamentals_result,
                    "dynamics": dynamics_result,
                    "macro": macro_result,
                },
            }
