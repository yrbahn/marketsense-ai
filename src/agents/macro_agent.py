"""Macro Agent - 거시경제 분석

논문 Section 3.3: Macroeconomic Analysis
- 거시경제 지표 분석
- 중앙은행 정책 해석
- 시장 전반 영향 평가
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from .base_agent import BaseAgent
from src.storage.models import MacroReport, MacroIndicator

logger = logging.getLogger("marketsense")


class MacroAgent(BaseAgent):
    """거시경제 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 한국 거시경제 분석 전문가입니다.

역할:
- 거시경제 지표와 한국은행 정책을 분석합니다
- 증시 전반에 미치는 영향을 평가합니다
- 투자 환경을 종합 판단합니다

출력 형식:
{
  "market_outlook": "bullish|bearish|neutral",
  "confidence": 0.0-1.0,
  "risk_level": "low|medium|high",
  "key_factors": ["요인1", "요인2", "요인3"],
  "summary": "시장 전망 요약",
  "reasoning": "분석 근거"
}
"""

    def analyze(self, lookback_days: int = 90) -> Dict[str, Any]:
        """거시경제 분석"""
        logger.info(f"[MacroAgent] 거시경제 분석 시작")

        with self.db.get_session() as session:
            # 최근 한국은행 보고서
            cutoff = datetime.now() - timedelta(days=lookback_days)
            reports = (
                session.query(MacroReport)
                .filter(
                    MacroReport.source_name.like("%한국은행%"),
                    MacroReport.published_at >= cutoff,
                )
                .order_by(MacroReport.published_at.desc())
                .limit(10)
                .all()
            )

            # 최근 경제 지표
            indicators = (
                session.query(MacroIndicator)
                .filter(MacroIndicator.source.like("%bok%"))
                .order_by(MacroIndicator.date.desc())
                .limit(20)
                .all()
            )

            # 보고서 요약
            reports_text = []
            if reports:
                reports_text.append("한국은행 최근 보도자료:")
                for r in reports[:5]:
                    date_str = r.published_at.strftime("%Y-%m-%d") if r.published_at else "날짜 미상"
                    reports_text.append(f"- [{date_str}] {r.title}")
                    if r.summary:
                        reports_text.append(f"  {r.summary[:100]}...")
            else:
                reports_text.append("한국은행 보도자료: 데이터 없음")

            # 지표 요약
            indicators_text = []
            if indicators:
                indicators_text.append("\n주요 경제 지표:")
                for ind in indicators[:10]:
                    date_str = ind.date.strftime("%Y-%m")
                    indicators_text.append(
                        f"- {ind.series_name} ({date_str}): {ind.value}"
                    )
            else:
                indicators_text.append("\n경제 지표: 데이터 없음")

            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

{chr(10).join(reports_text)}

{chr(10).join(indicators_text)}

위 거시경제 데이터를 종합 분석하여 JSON 형식으로 답변하세요.
"""

            try:
                response_text = self.generate(prompt)
                import json

                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())
                result["analyzed_at"] = datetime.now().isoformat()
                result["reports_count"] = len(reports)
                result["indicators_count"] = len(indicators)

                logger.info(
                    f"[MacroAgent] 분석 완료: {result.get('market_outlook')}"
                )

                return result

            except Exception as e:
                logger.error(f"[MacroAgent] 분석 실패: {e}")
                return {"error": str(e)}
