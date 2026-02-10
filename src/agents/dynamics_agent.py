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
- 주가 차트와 기술적 지표를 종합 분석합니다
- 추세, 패턴, 지지/저항선을 정확히 판단합니다
- 이동평균선, RSI, MACD, 거래량을 상세히 해석합니다
- 매매 타이밍과 목표가를 제시합니다

분석 항목:
1. 추세 분석
   - 단기 추세 (5일, 20일 이평선)
   - 중기 추세 (60일, 120일 이평선)
   - 골든크로스/데드크로스 여부
   
2. 보조지표 분석
   - RSI(14): 과매수(70+)/과매도(30-) 판단
   - MACD: 시그널 교차, 히스토그램 방향
   - 볼린저밴드: 밴드폭, 현재 위치
   
3. 거래량 분석
   - 거래량 추세 (증가/감소)
   - 가격-거래량 괴리
   - 급증/급감 시그널
   
4. 패턴 인식
   - 차트 패턴 (헤드앤숄더, 삼각수렴 등)
   - 캔들 패턴 (도지, 망치형 등)
   
5. 지지/저항선
   - 주요 지지선 3개
   - 주요 저항선 3개
   - 돌파 가능성

출력 형식 (JSON):
{
  "trend": "uptrend|downtrend|sideways",
  "trend_strength": "strong|moderate|weak",
  "signal": "buy|sell|hold",
  "confidence": 0.0-1.0,
  
  "moving_averages": {
    "ma5_vs_ma20": "골든크로스|데드크로스|정배열|역배열",
    "ma20_vs_ma60": "상승|하락|횡보",
    "interpretation": "이평선 해석"
  },
  
  "indicators": {
    "rsi": {"value": 숫자, "status": "과매수|중립|과매도"},
    "macd": {"signal": "매수|매도|중립", "strength": "강|중|약"},
    "volume": {"trend": "증가|감소|보합", "signal": "긍정|부정|중립"}
  },
  
  "patterns": {
    "chart_pattern": "패턴명 또는 null",
    "candle_pattern": "패턴명 또는 null",
    "interpretation": "패턴 해석"
  },
  
  "key_levels": {
    "support": [지지선1, 지지선2, 지지선3],
    "resistance": [저항선1, 저항선2, 저항선3],
    "current_position": "지지선 근처|중립|저항선 근처"
  },
  
  "trading_strategy": {
    "entry_point": "진입 가격대",
    "target_price": "목표가",
    "stop_loss": "손절가",
    "time_horizon": "단기|중기|장기"
  },
  
  "summary": "종합 의견 (3-5문장)",
  "reasoning": "상세 분석 근거"
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

            # 최근 주가 요약 (상세)
            recent_prices = price_data[:20]
            current_price = recent_prices[0].close
            
            # 가격 통계
            prices = [p.close for p in recent_prices]
            high_20d = max(prices)
            low_20d = min(prices)
            
            price_summary = []
            price_summary.append(f"현재가: {current_price:,.0f}원")
            price_summary.append(f"20일 고가: {high_20d:,.0f}원 (현재 대비 {((high_20d-current_price)/current_price*100):+.1f}%)")
            price_summary.append(f"20일 저가: {low_20d:,.0f}원 (현재 대비 {((low_20d-current_price)/current_price*100):+.1f}%)")
            
            # 최근 10일 데이터
            price_summary.append("\n최근 10일 주가:")
            for p in recent_prices[:10]:
                change = ((p.close - p.open) / p.open * 100) if p.open else 0
                price_summary.append(
                    f"  {p.date.strftime('%Y-%m-%d')}: "
                    f"시가 {p.open:,.0f} → 종가 {p.close:,.0f}원 ({change:+.1f}%) "
                    f"고가 {p.high:,.0f} 저가 {p.low:,.0f} "
                    f"거래량 {p.volume:,}"
                )
            
            # 이동평균선 계산 (간단)
            ma5 = sum([p.close for p in recent_prices[:5]]) / 5 if len(recent_prices) >= 5 else None
            ma20 = sum([p.close for p in recent_prices[:20]]) / 20 if len(recent_prices) >= 20 else None
            
            ma_text = ""
            if ma5 and ma20:
                ma_text = f"\n이동평균선:\n"
                ma_text += f"  MA5: {ma5:,.0f}원 (현재가 대비 {((current_price-ma5)/ma5*100):+.1f}%)\n"
                ma_text += f"  MA20: {ma20:,.0f}원 (현재가 대비 {((current_price-ma20)/ma20*100):+.1f}%)\n"
                
                if current_price > ma5 > ma20:
                    ma_text += "  → 정배열 (상승 추세)\n"
                elif current_price < ma5 < ma20:
                    ma_text += "  → 역배열 (하락 추세)\n"
            
            # 거래량 분석
            volumes = [p.volume for p in recent_prices[:10]]
            avg_volume = sum(volumes) / len(volumes)
            recent_volume = volumes[0]
            volume_change = ((recent_volume - avg_volume) / avg_volume * 100) if avg_volume else 0
            
            volume_text = f"\n거래량 분석:\n"
            volume_text += f"  최근 거래량: {recent_volume:,}주\n"
            volume_text += f"  10일 평균: {avg_volume:,.0f}주\n"
            volume_text += f"  평균 대비: {volume_change:+.1f}%\n"

            # 지표 요약
            indicators_text = ""
            if latest_indicators:
                sma20_text = f"{latest_indicators.sma_20:,.0f}원 (현재가: {current_price:,.0f}원)" if latest_indicators.sma_20 else 'N/A'
                sma50_text = f"{latest_indicators.sma_50:,.0f}원" if latest_indicators.sma_50 else 'N/A'
                sma200_text = f"{latest_indicators.sma_200:,.0f}원" if latest_indicators.sma_200 else 'N/A'
                rsi_text = f"{latest_indicators.rsi_14:.1f}" if latest_indicators.rsi_14 else 'N/A'
                macd_text = f"{latest_indicators.macd:.2f}" if latest_indicators.macd else 'N/A'
                signal_text = f"{latest_indicators.macd_signal:.2f}" if latest_indicators.macd_signal else 'N/A'
                bb_upper_text = f"{latest_indicators.bb_upper:,.0f}원" if latest_indicators.bb_upper else 'N/A'
                bb_lower_text = f"{latest_indicators.bb_lower:,.0f}원" if latest_indicators.bb_lower else 'N/A'
                
                indicators_text = f"""
기술적 지표 ({latest_indicators.date}):
- SMA20: {sma20_text}
- SMA50: {sma50_text}
- SMA200: {sma200_text}
- RSI(14): {rsi_text}
- MACD: {macd_text}
- Signal: {signal_text}
- 볼린저밴드 상단: {bb_upper_text}
- 볼린저밴드 하단: {bb_lower_text}
"""

            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 주가 데이터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(price_summary)}

{ma_text}

{volume_text}

{indicators_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 데이터를 바탕으로 상세한 기술적 분석을 수행하세요:

1. 추세 분석 (단기/중기)
2. 이동평균선 배열 및 교차
3. RSI, MACD 시그널
4. 거래량 패턴
5. 지지/저항선 식별
6. 매매 전략 (진입가, 목표가, 손절가)

JSON 형식으로 상세히 답변하세요.
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
