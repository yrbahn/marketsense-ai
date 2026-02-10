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
- 재무제표를 종합 분석하여 기업의 재무 건전성을 정확히 평가합니다
- 밸류에이션, 수익성, 성장성, 안정성, 현금흐름을 상세히 분석합니다
- 동종업계와 비교하여 상대적 가치를 판단합니다
- 시계열 분석으로 추세를 파악합니다

분석 항목:

1. 밸류에이션 분석
   - P/E (주가수익비율): 동종업계 평균 대비
   - P/B (주가순자산비율): 1 이하면 저평가
   - EV/EBITDA: 기업가치 대비 수익성
   - PEG (P/E to Growth): 성장성 대비 밸류에이션
   - 동종업계 비교 (상대적 저평가/고평가)

2. 수익성 분석
   - ROE (자기자본이익률): 15% 이상 우수
   - ROA (총자산이익률): 5% 이상 양호
   - 영업이익률: 10% 이상 양호
   - 순이익률: 5% 이상 양호
   - 시계열 추이 (개선/악화/유지)

3. 성장성 분석
   - 매출 성장률 (YoY, QoQ)
   - 영업이익 성장률
   - 당기순이익 성장률
   - 최근 4분기 추이 (가속/둔화)
   - 성장 지속가능성

4. 안정성 분석
   - 부채비율: 100% 이하 안정, 200% 이상 주의
   - 유동비율: 150% 이상 양호
   - 이자보상배율: 5배 이상 안정
   - 자본총계 추이
   - 재무 리스크 평가

5. 현금흐름 분석
   - 영업활동 현금흐름: 양수 필수
   - 잉여현금흐름 (FCF): 양수 우량
   - 현금 창출 능력
   - 배당 여력

6. 동종업계 비교
   - 업종 평균 대비 P/E, P/B
   - 업종 평균 대비 수익성
   - 업종 평균 대비 부채비율
   - 경쟁 우위/열위

7. 투자 의견
   - 적정 주가 범위
   - 상승/하락 여력
   - 투자 매력도
   - 주의 사항

출력 형식 (JSON):
{
  "valuation": {
    "rating": "undervalued|fair|overvalued",
    "pe_ratio": 숫자 또는 null,
    "pb_ratio": 숫자 또는 null,
    "vs_sector_pe": "저평가|적정|고평가",
    "vs_sector_pb": "저평가|적정|고평가",
    "fair_value_range": "하한-상한 (원)",
    "upside_potential": "상승여력 %"
  },
  
  "profitability": {
    "rating": "excellent|good|fair|poor",
    "roe": 숫자,
    "roa": 숫자,
    "operating_margin": 숫자,
    "net_margin": 숫자,
    "trend": "improving|stable|declining",
    "interpretation": "수익성 해석"
  },
  
  "growth": {
    "rating": "high|moderate|low|negative",
    "revenue_growth_yoy": 숫자,
    "profit_growth_yoy": 숫자,
    "quarterly_trend": "accelerating|stable|decelerating",
    "sustainability": "high|moderate|low",
    "drivers": "성장 동력 설명"
  },
  
  "stability": {
    "rating": "strong|moderate|weak|risky",
    "debt_ratio": 숫자,
    "current_ratio": 숫자,
    "interest_coverage": 숫자 또는 null,
    "equity_trend": "increasing|stable|decreasing",
    "risks": "재무 리스크 설명"
  },
  
  "cash_flow": {
    "rating": "strong|adequate|weak",
    "operating_cf": "양호|보통|부족",
    "free_cf": "양호|보통|부족",
    "cash_generating_power": "우수|보통|약함",
    "dividend_capacity": "high|moderate|low"
  },
  
  "peer_comparison": {
    "sector": "업종명",
    "vs_sector_valuation": "저평가|적정|고평가",
    "vs_sector_profitability": "우수|평균|열위",
    "competitive_advantage": "경쟁 우위 설명"
  },
  
  "investment_thesis": {
    "target_price": "목표가 (원)",
    "investment_merit": "투자 매력 포인트",
    "key_risks": "주의 사항",
    "recommendation": "적극 매수|매수|보유|관망|매도"
  },
  
  "summary": "종합 의견 (3-5문장)",
  "confidence": 0.0-1.0,
  "reasoning": "상세 분석 근거"
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
            
            # 현재가 가져오기
            from src.storage.models import PriceData
            price_data = session.query(PriceData).filter(
                PriceData.stock_id == stock.id
            ).order_by(PriceData.date.desc()).first()
            
            current_price = price_data.close if price_data else None

            # 최근 재무제표 (OpenDartReader 우선, 8개 분기 = 2년)
            statements = (
                session.query(FinancialStatement)
                .filter(FinancialStatement.stock_id == stock.id)
                .filter(FinancialStatement.source == 'opendartreader')
                .order_by(FinancialStatement.period_end.desc())
                .limit(8)
                .all()
            )
            
            # OpenDartReader 데이터 없으면 다른 소스 사용
            if not statements:
                statements = (
                    session.query(FinancialStatement)
                    .filter(FinancialStatement.stock_id == stock.id)
                    .order_by(FinancialStatement.period_end.desc())
                    .limit(8)
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
                quarter = stmt.fiscal_quarter or stmt.statement_type
                financials_text.append(f"\n[{period}] {quarter}:")

                # OpenDartReader 데이터 처리
                if stmt.source == 'opendartreader' and stmt.raw_data:
                    data = stmt.raw_data
                    
                    # 손익계산서
                    if data.get('revenue'):
                        financials_text.append(f"  - 매출액: {data['revenue']:,.0f}원")
                    if data.get('operating_income'):
                        financials_text.append(f"  - 영업이익: {data['operating_income']:,.0f}원")
                    if data.get('net_income'):
                        financials_text.append(f"  - 당기순이익: {data['net_income']:,.0f}원")
                    
                    # 재무상태표
                    if data.get('total_assets'):
                        financials_text.append(f"  - 자산총계: {data['total_assets']:,.0f}원")
                    if data.get('total_liabilities'):
                        financials_text.append(f"  - 부채총계: {data['total_liabilities']:,.0f}원")
                    if data.get('total_equity'):
                        financials_text.append(f"  - 자본총계: {data['total_equity']:,.0f}원")
                    
                    # 현금흐름
                    if data.get('operating_cash_flow'):
                        financials_text.append(f"  - 영업활동현금흐름: {data['operating_cash_flow']:,.0f}원")
                    
                    # 계산 지표
                    if data.get('roe'):
                        financials_text.append(f"  - ROE: {data['roe']:.1f}%")
                    if data.get('debt_ratio'):
                        financials_text.append(f"  - 부채비율: {data['debt_ratio']:.1f}%")
                    if data.get('current_ratio'):
                        financials_text.append(f"  - 유동비율: {data['current_ratio']:.1f}%")
                    if data.get('operating_margin'):
                        financials_text.append(f"  - 영업이익률: {data['operating_margin']:.1f}%")
                    if data.get('net_margin'):
                        financials_text.append(f"  - 순이익률: {data['net_margin']:.1f}%")
                        
                # 기존 DART API 데이터 처리
                elif stmt.raw_data:
                    # 주요 항목만 추출 (한국어 계정명)
                    key_items = [
                        "자산총계",
                        "매출액", 
                        "영업이익",
                        "당기순이익",
                        "부채총계",
                        "자본총계",
                        "영업활동현금흐름",
                    ]
                    for key in key_items:
                        if key in stmt.raw_data and stmt.raw_data[key] is not None:
                            value = stmt.raw_data[key]
                            financials_text.append(f"  - {key}: {value:,.0f}원")

            # 동종업계 비교 (Peer Analysis)
            from src.utils.peer_analysis import compare_with_peers
            
            peer_comparison = compare_with_peers(session, ticker)
            peer_text = ""
            
            if peer_comparison and peer_comparison.get('sector') != '미분류':
                peer_text = f"\n\n동종업계 비교 ({peer_comparison['sector']}):\n"
                
                if peer_comparison.get('peers'):
                    peer_names = [p['name'] for p in peer_comparison['peers'][:5]]
                    peer_text += f"주요 경쟁사: {', '.join(peer_names)}\n"
                
                if peer_comparison.get('comparison'):
                    comp = peer_comparison['comparison']
                    if comp.get('pe_vs_sector'):
                        peer_text += f"P/E 비교: {comp.get('target_pe', 0):.1f} vs 업종평균 {comp.get('sector_avg_pe', 0):.1f} → {comp['pe_vs_sector']}\n"
                    if comp.get('debt_vs_sector'):
                        peer_text += f"부채비율 비교: {comp.get('target_debt_ratio', 0):.1f}% vs 업종평균 {comp.get('sector_avg_debt_ratio', 0):.1f}% → {comp['debt_vs_sector']}\n"
            
            # 밸류에이션 계산 (TTM 또는 네이버)
            valuation_text = ""
            
            if current_price:
                # 1. TTM 계산 시도
                from src.utils.valuation import get_valuation_summary
                
                valuation = get_valuation_summary(
                    session,
                    stock.id,
                    current_price,
                    stock.market_cap
                )
                
                if valuation:
                    # TTM 계산 성공
                    valuation_text = f"""
밸류에이션 (TTM 기준, {valuation['quarters_used']}개 분기):
  현재가: {current_price:,.0f}원
  EPS: {valuation['eps']:,.0f}원
  PER: {valuation['per']:.2f}배
  BPS: {valuation['bps']:,.0f}원
  PBR: {valuation['pbr']:.2f}배
  
  적정가 범위 (PER 10-15배):
    보수적: {valuation['fair_value_range']['conservative']:,.0f}원 ({valuation['upside_conservative']:+.1f}%)
    적정: {valuation['fair_value_range']['fair']:,.0f}원 ({valuation['upside_fair']:+.1f}%)
    낙관적: {valuation['fair_value_range']['optimistic']:,.0f}원 ({valuation['upside_optimistic']:+.1f}%)
  
  성장주 프리미엄 (PER 15-20배):
    보수적: {valuation['growth_value_range']['conservative']:,.0f}원
    낙관적: {valuation['growth_value_range']['optimistic']:,.0f}원
"""
                else:
                    # TTM 실패 → 네이버 PER 시도
                    from src.collectors.naver_per_collector import NaverPERCollector
                    
                    naver = NaverPERCollector()
                    naver_data = naver.get_valuation_metrics(ticker)
                    
                    if naver_data and naver_data.get('per') and naver_data.get('eps'):
                        # 적정가 계산
                        eps = naver_data['eps']
                        fair_10 = eps * 10
                        fair_12 = eps * 12.5
                        fair_15 = eps * 15
                        fair_18 = eps * 18
                        fair_20 = eps * 20
                        
                        upside_10 = ((fair_10 - current_price) / current_price * 100)
                        upside_12 = ((fair_12 - current_price) / current_price * 100)
                        upside_15 = ((fair_15 - current_price) / current_price * 100)
                        
                        valuation_text = f"""
밸류에이션 (네이버 금융, TTM 기준):
  현재가: {current_price:,.0f}원
  EPS: {eps:,}원 (최근 4분기)
  PER: {naver_data['per']:.2f}배
"""
                        if naver_data.get('pbr') and naver_data.get('bps'):
                            valuation_text += f"""  PBR: {naver_data['pbr']:.2f}배
  BPS: {naver_data['bps']:,}원
"""
                        
                        valuation_text += f"""  
  적정가 범위 (PER 10-15배):
    보수적: {fair_10:,.0f}원 ({upside_10:+.1f}%)
    적정: {fair_12:,.0f}원 ({upside_12:+.1f}%)
    낙관적: {fair_15:,.0f}원 ({upside_15:+.1f}%)
  
  성장주 프리미엄 (PER 15-20배):
    적정: {fair_15:,.0f}원
    낙관적: {fair_20:,.0f}원
"""
            
            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})
업종: {stock.industry or 'N/A'}

재무제표 (최근 8개 분기 = 2년):
{''.join(financials_text)}{peer_text}{valuation_text}

분석 시 중점 사항:
1. YoY (전년 동기 대비) 성장률 계산 및 추세 파악
2. QoQ (전분기 대비) 변화 추이 분석
3. 2년간 성장 가속/둔화 여부
4. 계절성 패턴 존재 여부
5. 수익성/안정성 지표의 시계열 추이
6. **밸류에이션 분석** - 제공된 PER, 적정가 범위를 반드시 참조하여 판단
7. 목표가는 제공된 적정가 범위 내에서 성장성/수익성을 고려하여 설정

위 재무 데이터, 동종업계 비교, 밸류에이션을 종합 분석하여 JSON 형식으로 답변하세요.
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
