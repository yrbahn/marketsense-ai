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
from .news_agent import NewsAgent
from .fundamentals_agent import FundamentalsAgent
from .dynamics_agent import DynamicsAgent
from .macro_agent import MacroAgent

logger = logging.getLogger("marketsense")


class SignalAgent(BaseAgent):
    """신호 통합 에이전트"""

    SYSTEM_PROMPT = """당신은 대형 자산 운용사의 최고 투자 책임자(CIO)입니다.

당신의 역할은 산하의 전문 애널리스트들이 제출한 보고서를 종합 검토하여, 최종적인 매매 의사결정을 내리는 것입니다.
상충되는 정보가 있을 경우 논리적인 추론을 통해 결론을 도출해야 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
분석 지시사항:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **종합 분석 (Synthesis)**
   각 애널리스트 보고서의 핵심 주장을 요약하고 통합하십시오.
   - 뉴스 애널리스트: 최근 이슈와 시장 심리
   - 펀더멘털 애널리스트: 재무 건전성과 밸류에이션
   - 기술적 애널리스트: 차트와 수급 동향
   - 거시경제 애널리스트: 경기 사이클과 시장 환경
   
   **질문:** 펀더멘털과 기술적 분석이 일치합니까, 아니면 엇갈립니까?

2. **사고 과정 (Chain-of-Thought)**
   
   **긍정적 요인 (Pros):**
   - 뉴스: [ ]
   - 펀더멘털: [ ]
   - 기술적: [ ]
   - 거시경제: [ ]
   
   **부정적 요인 (Cons):**
   - 뉴스: [ ]
   - 펀더멘털: [ ]
   - 기술적: [ ]
   - 거시경제: [ ]
   
   **의견 충돌 처리:**
   보고서 간 의견 충돌(예: 실적은 좋으나 차트가 무너짐)이 있다면,
   현재 시점에서 어느 요소에 가중치를 더 둘지 논리적으로 서술하십시오.
   
   예시:
   - "펀더멘털은 강하나 기술적으로 약세 → 단기 조정 후 진입 기회"
   - "뉴스는 부정적이나 밸류에이션 매력 → 역발상 매수 기회"
   - "모든 요인 긍정 → 강력한 매수 신호"

3. **최종 결정**
   
   **투자 의견:** 매수 (BUY) / 보류 (HOLD) / 매도 (SELL) 중 하나를 선택하십시오.
   
   **확신도 (Confidence Score):** 당신의 결정에 대한 확신 수준을 0% ~ 100% 사이로 표기하십시오.
   - 90-100%: 매우 높은 확신 (모든 요인 일치)
   - 70-89%: 높은 확신 (주요 요인 긍정)
   - 50-69%: 보통 확신 (혼재된 신호)
   - 30-49%: 낮은 확신 (불확실성 높음)
   - 0-29%: 매우 낮은 확신 (상충되는 신호)
   
   **핵심 논거:** 이 결정을 내린 결정적인 이유를 한 문단으로 작성하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**마크다운 형식**으로 최종 투자 의견을 작성하세요.
마크다운 헤더(##, ###)와 강조(**bold**)를 적극 활용하십시오.
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
            summary = news_result.get('summary', '')
            # 텍스트가 너무 길면 처음 500자만
            if len(summary) > 500:
                summary = summary[:500] + "..."
            analysis_summary.append(
                f"## [뉴스 애널리스트 보고서]\n"
                f"- 감성: {news_result.get('sentiment', 'N/A')}\n"
                f"- 신뢰도: {news_result.get('confidence', 0):.0%}\n\n"
                f"{summary}"
            )
        else:
            analysis_summary.append("## [뉴스 애널리스트 보고서]\n데이터 없음")

        if fundamentals_result and "error" not in fundamentals_result:
            summary = fundamentals_result.get('summary', '')
            if len(summary) > 500:
                summary = summary[:500] + "..."
            valuation = fundamentals_result.get('valuation', {})
            if isinstance(valuation, dict):
                val_rating = valuation.get('rating', 'N/A')
            else:
                val_rating = str(valuation)
            analysis_summary.append(
                f"## [펀더멘털 애널리스트 보고서]\n"
                f"- 밸류에이션: {val_rating}\n"
                f"- 신뢰도: {fundamentals_result.get('confidence', 0):.0%}\n\n"
                f"{summary}"
            )
        else:
            analysis_summary.append("## [펀더멘털 애널리스트 보고서]\n데이터 없음")

        if dynamics_result and "error" not in dynamics_result:
            summary = dynamics_result.get('summary', '')
            if len(summary) > 500:
                summary = summary[:500] + "..."
            analysis_summary.append(
                f"## [기술적/수급 애널리스트 보고서]\n"
                f"- 추세: {dynamics_result.get('trend', 'N/A')}\n"
                f"- 신호: {dynamics_result.get('signal', 'N/A')}\n"
                f"- 현재가: {dynamics_result.get('current_price', 0):,.0f}원\n\n"
                f"{summary}"
            )
        else:
            analysis_summary.append("## [기술적/수급 애널리스트 보고서]\n데이터 없음")

        if macro_result and "error" not in macro_result:
            summary = macro_result.get('summary', '')
            if len(summary) > 500:
                summary = summary[:500] + "..."
            analysis_summary.append(
                f"## [거시경제 애널리스트 보고서]\n"
                f"- 시장 전망: {macro_result.get('market_outlook', 'N/A')}\n"
                f"- 거시경제 점수: {macro_result.get('macro_score', 0)}\n"
                f"- 리스크: {macro_result.get('risk_level', 'N/A')}\n\n"
                f"{summary}"
            )
        else:
            analysis_summary.append("## [거시경제 애널리스트 보고서]\n데이터 없음")

        # Gemini로 통합 분석
        prompt = f"""{self.SYSTEM_PROMPT}

종목: {ticker}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
애널리스트 보고서:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(analysis_summary)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 4개 애널리스트 보고서를 검토하고 최종 투자 의견을 **마크다운 형식**으로 제시하십시오.

반드시 다음 내용을 포함하십시오:
1. 종합 분석 (Synthesis): 각 보고서의 핵심 주장 요약 및 일치/불일치 여부
2. 긍정적 요인 (Pros) 및 부정적 요인 (Cons)
3. 의견 충돌 처리: 상충되는 요인에 대한 가중치 판단
4. 최종 결정: 투자 의견 (매수/보류/매도) + 확신도 (0-100%) + 핵심 논거

마크다운 헤더(##, ###)와 강조(**bold**)를 적극 활용하십시오.
"""

        try:
            response_text = self.generate(prompt)
            
            # 텍스트에서 신호 추출
            signal = "HOLD"
            if any(word in response_text for word in ["매수", "BUY", "Buy", "적극 매수"]):
                signal = "BUY"
            elif any(word in response_text for word in ["매도", "SELL", "Sell"]):
                signal = "SELL"
            
            # 확신도 추출 (정규식)
            import re
            confidence = 0.70  # 기본값
            conf_match = re.search(r'확신도[:\s]*(\d+)%|confidence[:\s]*(\d+)%', response_text, re.IGNORECASE)
            if conf_match:
                conf_str = conf_match.group(1) or conf_match.group(2)
                confidence = int(conf_str) / 100.0
            
            result = {
                "ticker": ticker,
                "signal": signal,
                "confidence": confidence,
                "summary": response_text,  # 전체 마크다운 텍스트
                "analyzed_at": datetime.now().isoformat(),
                "agent_results": {
                    "news": news_result,
                    "fundamentals": fundamentals_result,
                    "dynamics": dynamics_result,
                    "macro": macro_result,
                }
            }

            logger.info(
                f"[SignalAgent] {ticker} 통합 완료: {signal} (확신도 {confidence:.0%})"
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
    
    def analyze(self, ticker: str) -> Dict[str, Any]:
        """종목 종합 분석 (완전 구현)
        
        Args:
            ticker: 종목 코드
            
        Returns:
            통합 분석 결과
        """
        logger.info(f"[SignalAgent] {ticker} 종합 분석 시작")
        
        try:
            # 1. MacroAgent 실행 (시장 전반 상황)
            macro_agent = MacroAgent(self.config, self.db)
            macro_result = macro_agent.analyze(lookback_days=90)
            logger.debug(f"[SignalAgent] 거시경제 분석 완료")
            
            # 2. NewsAgent 실행
            news_agent = NewsAgent(self.config, self.db)
            news_result = news_agent.analyze(ticker)
            logger.debug(f"[SignalAgent] {ticker} 뉴스 분석 완료")
            
            # 3. FundamentalsAgent 실행
            fundamentals_agent = FundamentalsAgent(self.config, self.db)
            fundamentals_result = fundamentals_agent.analyze(ticker)
            logger.debug(f"[SignalAgent] {ticker} 펀더멘털 분석 완료")
            
            # 4. DynamicsAgent 실행
            dynamics_agent = DynamicsAgent(self.config, self.db)
            dynamics_result = dynamics_agent.analyze(ticker)
            logger.debug(f"[SignalAgent] {ticker} 기술적 분석 완료")
            
            # 5. 4개 에이전트 결과 통합
            prompt = f"""{self.SYSTEM_PROMPT}

종목 코드: {ticker}

**거시경제 분석 (MacroAgent):**
{macro_result.get('summary', 'N/A')}
- 시장 전망: {macro_result.get('market_outlook', 'N/A')}
- 리스크 수준: {macro_result.get('risk_level', 'N/A')}

**뉴스 분석 (NewsAgent):**
{news_result.get('summary', 'N/A')}
- 감성: {news_result.get('sentiment', 'N/A')}
- 영향: {news_result.get('impact', 'N/A')}

**펀더멘털 분석 (FundamentalsAgent):**
{fundamentals_result.get('summary', 'N/A')}
- 밸류에이션: {fundamentals_result.get('valuation', 'N/A')}
- 재무 건전성: {fundamentals_result.get('financial_health', 'N/A')}

**기술적/수급 분석 (DynamicsAgent):**
{dynamics_result.get('summary', 'N/A')}
- 추세: {dynamics_result.get('trend', 'N/A')}
- 모멘텀: {dynamics_result.get('momentum', 'N/A')}

위 4개 에이전트의 분석 결과를 종합하여 최종 투자 신호를 생성하세요.
"""
            
            response_text = self.generate(prompt)
            import json
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["ticker"] = ticker
            result["analyzed_at"] = datetime.now().isoformat()
            
            # 각 에이전트 결과 포함
            result["macro_summary"] = macro_result.get('summary', '')
            result["macro_outlook"] = macro_result.get('market_outlook', 'N/A')
            result["news_summary"] = news_result.get('summary', '')
            result["news_sentiment"] = news_result.get('sentiment', 'N/A')
            result["fundamentals_summary"] = fundamentals_result.get('summary', '')
            result["fundamentals_valuation"] = fundamentals_result.get('valuation', 'N/A')
            result["dynamics_summary"] = dynamics_result.get('summary', '')
            result["dynamics_trend"] = dynamics_result.get('trend', 'N/A')
            
            logger.info(
                f"[SignalAgent] {ticker} 분석 완료: {result.get('signal')} "
                f"(신뢰도 {result.get('confidence', 0):.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[SignalAgent] {ticker} 분석 실패: {e}")
            return {
                "ticker": ticker,
                "signal": "HOLD",
                "confidence": 0.5,
                "risk_level": "medium",
                "summary": "분석 오류",
                "error": str(e)
            }
