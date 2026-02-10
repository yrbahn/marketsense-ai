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
from src.storage.models import Stock, PriceData, TechnicalIndicator, SupplyDemandData

logger = logging.getLogger("marketsense")


class DynamicsAgent(BaseAgent):
    """기술적 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 기술적 분석가이자 퀀트 트레이더입니다.

뉴스나 재무 정보는 배제하고, 오직 가격 데이터(Price Action), 거래량, 변동성 지표, 수급 데이터, 그리고 시장 모멘텀만을 분석하여 트레이딩 셋업을 판단합니다.

역할:
- 주가 차트와 기술적 지표를 종합 분석합니다
- 추세, 패턴, 지지/저항선을 정확히 판단합니다
- 이동평균선, RSI, MACD, 볼린저밴드, 거래량을 상세히 해석합니다
- 수급 데이터(외국인/기관 매매, 공매도, 신용잔고)를 분석합니다
- 경쟁사 대비 상대 강도를 평가합니다
- 매매 타이밍과 목표가, 손절선을 제시합니다

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
분석 지시사항:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **추세 파악 (최우선)**
   현재 주가 흐름이 **상승세, 하락세, 횡보** 중 어느 국면인지 명확히 정의하십시오.
   - 상승세: 고점/저점 상승, 이평선 정배열, 거래량 증가
   - 하락세: 고점/저점 하락, 이평선 역배열, 거래량 증가
   - 횡보: 일정 범위 내 등락, 방향성 없음
   
2. **주요 레벨 식별**
   단기 및 중기 **지지선**과 **저항선** 가격대를 구체적으로 식별하십시오.
   - 지지선: 과거 저점, 이평선, 심리적 가격대
   - 저항선: 과거 고점, 이평선, 심리적 가격대
   - 현재 가격이 어디에 위치하는지 명시
   
3. **리스크 평가**
   변동성과 보조지표(RSI 과매수 등)를 통해 **현재 진입 시 리스크 수준**을 평가하십시오.
   - 고위험: RSI 70+, 볼밴 상단, 급등 후, 거래량 폭발
   - 중위험: RSI 50-70, 볼밴 중간, 정상 거래량
   - 저위험: RSI 30-, 볼밴 하단, 과매도 구간
   
4. **상대 강도 분석**
   경쟁사들(Peer Group) 또는 시장 대비 이 주식이 **더 강한지 약한지** 분석하십시오.
   - Strong: 시장 대비 초과 수익
   - Weak: 시장 대비 부진
   - Neutral: 시장과 동조
   
5. **수급 분석 (중요!)**
   투자자별 매매 동향, 공매도, 신용잔고를 종합하여 수급 상황을 판단하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

4. 수급 분석 (중요!)
   - 투자자별 순매수: 외국인/기관 매수 → 긍정적, 순매도 → 부정적
   - 공매도: 급증 → 부정적, 감소 → 긍정적
   - 신용잔고: 융자 급증 → 과열 위험, 감소 → 건전
   - 외국인 보유율: 상승 → 긍정적, 하락 → 부정적
   
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
  
  "supply_demand": {
    "investor_trend": {
      "foreign_5d": "순매수|순매도",
      "institution_5d": "순매수|순매도",
      "overall_signal": "긍정적|부정적|중립"
    },
    "short_selling": {
      "trend": "증가|감소|보합",
      "signal": "긍정적|부정적|중립"
    },
    "credit_balance": {
      "margin_trend": "증가|감소|보합",
      "risk_level": "과열|정상|건전"
    },
    "summary": "수급 종합 판단 (2-3문장)"
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
    "entry_point": "진입 가격대 (구체적 숫자)",
    "target_price": "목표가 (구체적 숫자)",
    "stop_loss": "손절가 (구체적 숫자)",
    "time_horizon": "단기|중기|장기",
    "risk_reward_ratio": "위험 대비 수익 비율"
  },
  
  "risk_assessment": {
    "risk_level": "고위험|중위험|저위험",
    "volatility": "변동성 설명",
    "entry_timing": "지금 진입 시 리스크 평가"
  },
  
  "relative_strength": {
    "vs_market": "강세|약세|중립",
    "vs_peers": "상대적 강도 설명 (있는 경우)",
    "momentum": "모멘텀 강도"
  },
  
  "technical_verdict": "강세|약세|중립",
  "summary": "종합 의견 (3-5문장)",
  "reasoning": "상세 분석 근거"
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
최종 결론:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

기술적 관점에서 [강세 / 약세 / 중립]을 판정하고, 
잠재적인 **진입 구간**, **목표가**, **손절선**을 구체적 숫자로 제시하십시오.
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

            # 수급 데이터 조회
            supply_demand_text = ""
            supply_demand_data = (
                session.query(SupplyDemandData)
                .filter(SupplyDemandData.stock_id == stock.id)
                .order_by(SupplyDemandData.date.desc())
                .limit(10)
                .all()
            )
            
            if supply_demand_data:
                supply_demand_text = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                supply_demand_text += "📊 수급 분석 (최근 10일)\n"
                supply_demand_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # 1. 투자자별 순매수 추세
                investor_data = []
                for sd in supply_demand_data:
                    if sd.individual_net_buy or sd.foreign_net_buy or sd.institution_net_buy:
                        investor_data.append({
                            'date': sd.date,
                            'individual': sd.individual_net_buy or 0,
                            'foreign': sd.foreign_net_buy or 0,
                            'institution': sd.institution_net_buy or 0,
                        })
                
                if investor_data:
                    supply_demand_text += "1️⃣ 투자자별 순매수 (최근 5일):\n"
                    for data in investor_data[:5]:
                        date_str = data['date'].strftime('%m/%d')
                        supply_demand_text += f"  {date_str}: "
                        supply_demand_text += f"개인 {data['individual']:+,.0f} | "
                        supply_demand_text += f"외국인 {data['foreign']:+,.0f} | "
                        supply_demand_text += f"기관 {data['institution']:+,.0f}\n"
                    
                    # 5일 누적
                    if len(investor_data) >= 5:
                        ind_5d = sum([d['individual'] for d in investor_data[:5]])
                        for_5d = sum([d['foreign'] for d in investor_data[:5]])
                        ins_5d = sum([d['institution'] for d in investor_data[:5]])
                        
                        supply_demand_text += f"\n  → 5일 누적: "
                        supply_demand_text += f"개인 {ind_5d:+,.0f} | "
                        supply_demand_text += f"외국인 {for_5d:+,.0f} | "
                        supply_demand_text += f"기관 {ins_5d:+,.0f}\n"
                        
                        # 추세 판단
                        if for_5d > 0 and ins_5d > 0:
                            supply_demand_text += f"  💪 외국인+기관 순매수 (긍정적 신호)\n"
                        elif for_5d < 0 and ins_5d < 0:
                            supply_demand_text += f"  ⚠️ 외국인+기관 순매도 (부정적 신호)\n"
                    
                    supply_demand_text += "\n"
                
                # 2. 공매도 분석
                short_data = []
                for sd in supply_demand_data:
                    if sd.short_volume or sd.short_ratio:
                        short_data.append({
                            'date': sd.date,
                            'volume': sd.short_volume or 0,
                            'ratio': sd.short_ratio or 0,
                        })
                
                if short_data:
                    supply_demand_text += "2️⃣ 공매도 추이 (최근 5일):\n"
                    for data in short_data[:5]:
                        date_str = data['date'].strftime('%m/%d')
                        supply_demand_text += f"  {date_str}: {data['volume']:,.0f}주 ({data['ratio']:.2f}%)\n"
                    
                    # 추세 분석
                    if len(short_data) >= 2:
                        recent_avg = sum([d['ratio'] for d in short_data[:3]]) / 3 if len(short_data) >= 3 else short_data[0]['ratio']
                        older_avg = sum([d['ratio'] for d in short_data[-3:]]) / 3 if len(short_data) >= 6 else short_data[-1]['ratio']
                        
                        if recent_avg > older_avg * 1.5:
                            supply_demand_text += f"  ⚠️ 공매도 급증 (부정적 신호)\n"
                        elif recent_avg < older_avg * 0.7:
                            supply_demand_text += f"  💪 공매도 감소 (긍정적 신호)\n"
                    
                    supply_demand_text += "\n"
                
                # 3. 신용잔고 분석
                credit_data = []
                for sd in supply_demand_data:
                    if sd.margin_balance or sd.credit_sell_balance:
                        credit_data.append({
                            'date': sd.date,
                            'margin': sd.margin_balance or 0,
                            'credit_sell': sd.credit_sell_balance or 0,
                        })
                
                if credit_data:
                    supply_demand_text += "3️⃣ 신용잔고 추이 (최근 5일):\n"
                    for data in credit_data[:5]:
                        date_str = data['date'].strftime('%m/%d')
                        supply_demand_text += f"  {date_str}: 융자 {data['margin']:,.0f}주 | 대주 {data['credit_sell']:,.0f}주\n"
                    
                    # 과열 판단
                    if len(credit_data) >= 2:
                        margin_change = ((credit_data[0]['margin'] - credit_data[-1]['margin']) / credit_data[-1]['margin'] * 100) if credit_data[-1]['margin'] > 0 else 0
                        
                        if margin_change > 20:
                            supply_demand_text += f"  ⚠️ 융자 급증 +{margin_change:.1f}% (과열 가능성)\n"
                        elif margin_change < -20:
                            supply_demand_text += f"  💪 융자 감소 {margin_change:.1f}% (건전)\n"
                    
                    supply_demand_text += "\n"
                
                # 4. 외국인 보유율
                foreign_ownership_data = []
                for sd in supply_demand_data:
                    if sd.foreign_ownership:
                        foreign_ownership_data.append({
                            'date': sd.date,
                            'ownership': sd.foreign_ownership,
                        })
                
                if foreign_ownership_data:
                    supply_demand_text += "4️⃣ 외국인 보유율:\n"
                    latest = foreign_ownership_data[0]
                    supply_demand_text += f"  현재: {latest['ownership']:.2f}%\n"
                    
                    if len(foreign_ownership_data) >= 2:
                        change_10d = latest['ownership'] - foreign_ownership_data[-1]['ownership']
                        supply_demand_text += f"  10일 변화: {change_10d:+.2f}%p\n"

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

{supply_demand_text}

{indicators_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 데이터를 바탕으로 상세한 기술적 분석을 수행하세요:

1. 추세 분석 (단기/중기)
2. 이동평균선 배열 및 교차
3. RSI, MACD 시그널
4. 거래량 패턴
5. 지지/저항선 식별
6. 매매 전략 (진입가, 목표가, 손절가)

**마크다운 형식**으로 간결하게 작성하세요.

반드시 다음 내용을 포함하되, 자유로운 형식으로 작성하십시오:
- 추세 판단 (상승/하락/횡보)
- 주요 레벨 (지지선/저항선)
- 리스크 평가 (고/중/저)
- 기술적 판정 (강세/약세/중립)

**중요: 전체 분석을 300자 이내로 간결하게 작성하세요.**
핵심 기술적 신호와 수급 상황에 집중하십시오.

마크다운 헤더(##, ###)와 강조(**bold**)를 적극 활용하세요.
"""

            try:
                response_text = self.generate(prompt)
                
                # 텍스트에서 간단한 정보 추출
                trend = "uptrend"
                if any(word in response_text.lower() for word in ["상승", "uptrend", "강세", "bullish"]):
                    trend = "uptrend"
                elif any(word in response_text.lower() for word in ["하락", "downtrend", "약세", "bearish"]):
                    trend = "downtrend"
                elif any(word in response_text.lower() for word in ["횡보", "sideways", "중립"]):
                    trend = "sideways"
                
                signal = "buy"
                if any(word in response_text.lower() for word in ["매수", "buy", "진입"]):
                    signal = "buy"
                elif any(word in response_text.lower() for word in ["매도", "sell"]):
                    signal = "sell"
                else:
                    signal = "hold"
                
                result = {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "current_price": float(recent_prices[0].close),
                    "trend": trend,
                    "signal": signal,
                    "confidence": 0.80,  # 기본값
                    "summary": response_text,  # 전체 마크다운 텍스트
                    "analyzed_at": datetime.now().isoformat()
                }

                logger.info(
                    f"[DynamicsAgent] {ticker} 분석 완료: {signal}"
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
