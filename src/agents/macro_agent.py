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

    SYSTEM_PROMPT = """당신은 한국 거시경제 전략가(Korea Macro Strategist)입니다.

금리, 인플레이션, 환율, GDP 성장률, 고용 및 대내외 정책 이슈가 한국 증시와 특정 산업 섹터에 미치는 파급 효과를 분석하는 것이 전문입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
분석 지시사항:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **경기 사이클 진단**
   현재 한국 경제가 **확장, 수축, 회복, 스태그플레이션** 중 어느 단계에 있는지 요약하십시오.
   - 확장: GDP 성장 가속, 고용 증가, 소비/투자 활발
   - 수축: GDP 성장 둔화, 실업률 상승, 소비 위축
   - 회복: 저점 이후 개선, 정책 효과 나타남
   - 스태그플레이션: 저성장 + 고물가 동시 발생

2. **시장 영향 분석**
   현재의 **금리 수준**과 **인플레이션 추세**가 한국 증시 전반에 호재인지 악재인지 논리적으로 설명하십시오.
   - 금리 인상 → 부담 증가, 밸류에이션 압박
   - 금리 인하 → 유동성 확대, 증시 긍정적
   - 인플레이션 상승 → 원자재 부담, 소비 위축
   - 인플레이션 안정 → 긍정적 환경

3. **환율/대외 요인**
   원/달러 환율, 미국 Fed 정책, 한미 금리차가 미치는 영향을 분석하십시오.
   - 원화 약세 → 수출 기업 유리, 수입 부담
   - 원화 강세 → 수입 기업 유리, 수출 부담
   - 한미 금리차 확대 → 외국인 자금 유출 우려

4. **시스템 리스크**
   시장 전체에 충격을 줄 수 있는 잠재적 위험 요소를 식별하십시오.
   - 글로벌: 미중 갈등, 지정학적 리스크
   - 국내: 부동산 시장, 가계부채
   - 금융: 금리 급변동, 유동성 위기

5. **거시경제 환경 점수**
   현재 거시경제 환경이 한국 증시에 얼마나 우호적인지 **-10 ~ +10 점수**로 평가하십시오.
   - +10: 매우 우호적 (저금리, 저물가, 강한 성장)
   - +5: 우호적 (완만한 성장, 안정적 물가)
   - 0: 중립 (불확실성 혼재)
   - -5: 비우호적 (고금리 또는 고물가)
   - -10: 매우 비우호적 (침체 + 고물가)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

출력 형식 (JSON):
{
  "economic_cycle": {
    "phase": "확장|수축|회복|스태그플레이션",
    "confidence": 0.0-1.0,
    "reasoning": "사이클 판단 근거"
  },
  
  "market_impact": {
    "interest_rate_impact": "긍정적|부정적|중립",
    "inflation_impact": "긍정적|부정적|중립",
    "overall_assessment": "호재|악재|혼재"
  },
  
  "external_factors": {
    "exchange_rate": "원화 강세|약세|중립",
    "us_fed_policy": "긴축|완화|중립",
    "capital_flow": "유입|유출|중립"
  },
  
  "systemic_risks": [
    {
      "risk": "리스크 요인",
      "severity": "high|medium|low",
      "description": "상세 설명"
    }
  ],
  
  "macro_score": -10 ~ +10 (정수),
  "market_outlook": "bullish|bearish|neutral",
  "confidence": 0.0-1.0,
  "risk_level": "low|medium|high",
  "key_factors": ["요인1", "요인2", "요인3"],
  "summary": "시장 전망 요약",
  "reasoning": "상세 분석 근거"
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
