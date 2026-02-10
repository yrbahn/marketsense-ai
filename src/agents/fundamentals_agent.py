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

    SYSTEM_PROMPT = """당신은 주식 시장의 펀더멘털 리서치 애널리스트입니다.

재무제표(대차대조표, 손익계산서 등)의 수치 분석과 증권사 리서치 리포트 분석에 탁월한 능력을 가지고 있습니다.
회사의 재무 건전성과 성장 잠재력을 냉철하게 평가하십시오.

역할:
- 재무제표를 종합 분석하여 기업의 재무 건전성을 정확히 평가합니다
- 밸류에이션, 수익성, 성장성, 안정성, 현금흐름을 상세히 분석합니다
- 동종업계와 비교하여 상대적 가치를 판단합니다
- 시계열 분석 (YoY, QoQ)으로 추세를 파악합니다
- 증권사 리포트의 어조와 sentiment를 분석합니다

━━━━━━━━━━━━━━━━━━━━━━
분석 프로세스 (Chain-of-Thought):
━━━━━━━━━━━━━━━━━━━━━━

**반드시 다음 7단계를 순서대로 따라 생각하세요:**

📊 Step 1: 데이터 이해
   - 제공된 재무 지표를 읽고 파악
   - "매출 XXX억, 순이익 XXX억, ROE XX%를 확인했다"
   - PER, 적정가 범위 확인

💡 Step 2: 지표 해석
   - 각 지표가 의미하는 바 해석
   - "ROE 15%는 자기자본 대비 수익률이 우수하다"
   - "부채비율 43%는 안정적 수준이다"

🏢 Step 3: 업종 맥락 이해
   - 동종업계 정보로 업종 특성 파악
   - "화장품은 경기소비재로 일반적 PER 12-15배"
   - "경쟁사는 아모레퍼시픽, LG생활건강 등 대형사"

📈 Step 4: 시계열 추세 분석 (YoY/QoQ)
   - **전년 동기 대비 (YoY)**: 계절성 제거, 진정한 성장 파악
   - **전분기 대비 (QoQ)**: 최근 모멘텀 확인
   - 최근 8개 분기 변화 패턴 파악
   - "매출 YoY +32%, QoQ +8% → 가속 성장"
   - "영업이익 YoY +45%, QoQ +12% → 레버리지 효과"
   - "ROE 13% → 15%로 개선 추세"
   - **중요**: 매출과 영업이익의 유의미한 변화에 집중

⚖️ Step 5: 상대 밸류에이션 판단
   - 업종 평균 PER 추론 (예: 12-15배)
   - 대상 PER과 비교
   - "PER 10.77은 업종 대비 약 10-20% 낮음 → 저평가"

🎯 Step 6: 종합 판단
   - 펀더멘털 우수 + 저평가 → 매력적
   - 펀더멘털 부진 + 저평가 → 가치함정
   - 성장성, 상대 밸류, 안정성 종합

💰 Step 7: 목표가 산출
   - 적정가 범위 참조
   - 성장성 우수 + 저평가 → 상한 선택
   - 명확한 근거 제시: "성장률 32%, 업종 대비 저평가로 PER 15배 적용"

**각 단계의 추론 과정을 JSON의 reasoning 필드에 명시하세요!**

━━━━━━━━━━━━━━━━━━━━━━

분석 항목:

1. 밸류에이션 분석 (업종 상대 평가 중요!)
   - P/E (주가수익비율): **반드시 업종 특성 고려**
     * 성장주 (IT, 바이오): 15-25배 정상
     * 경기소비재 (화장품, 패션): 10-15배 정상
     * 안정주 (금융, 유틸): 5-10배 정상
     * 제공된 동종업계 정보를 바탕으로 업종 평균 수준 추론
     * 업종 대비 -15% 이하 → 저평가
     * 업종 대비 ±15% → 적정
     * 업종 대비 +15% 이상 → 고평가
   - P/B (주가순자산비율): 1 이하면 저평가, 업종별로 다름
   - PEG (P/E to Growth): 성장성 대비 밸류에이션
   - **상대 밸류에이션이 절대 밸류에이션보다 중요!**

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

6. 동종업계 비교 (핵심!)
   - **업종 특성 이해**: 성장주/가치주/경기소비재 등
   - **동종업계 밸류에이션 추론**: 
     * 제공된 경쟁사 정보로 업종 평균 PER 수준 추정
     * 예: 화장품 업종은 보통 PER 12-15배
   - **상대 평가**:
     * 대상 종목 PER이 업종 수준보다 낮으면 → 저평가
     * 단, 낮은 이유가 실적 부진이면 함정
     * 성장성/수익성이 우수한데 PER 낮으면 → 진짜 저평가
   - 업종 평균 대비 수익성, 부채비율 비교
   - 경쟁 우위/열위

7. 투자 의견 (목표가 설정 가이드)
   - **적정 주가 범위**: 제공된 적정가 범위 참조
   - **목표가 설정 원칙**:
     * 성장성 우수 + 업종 대비 저평가 → 적정가 상한 선택
     * 성장성 보통 + 업종 평균 수준 → 적정가 중간값
     * 성장성 낮음 + 업종 대비 고평가 → 적정가 하한 또는 현재가 유지
     * 업종 평균 PER을 추론하여 목표가 합리성 검증
   - 상승/하락 여력
   - 투자 매력도
   - 주의 사항

출력 형식 (JSON):
{
  "reasoning_steps": [
    {
      "step": 1,
      "name": "데이터 이해",
      "observation": "확인한 주요 데이터",
      "thinking": "이 데이터가 의미하는 것"
    },
    {
      "step": 2,
      "name": "지표 해석",
      "observation": "ROE, 부채비율 등 지표",
      "thinking": "각 지표의 좋고 나쁨 판단"
    },
    {
      "step": 3,
      "name": "업종 맥락",
      "observation": "업종 특성, 경쟁사",
      "thinking": "이 업종의 일반적 PER 수준 추론"
    },
    {
      "step": 4,
      "name": "시계열 추세",
      "observation": "8개 분기 변화",
      "thinking": "성장 가속/둔화, 개선/악화"
    },
    {
      "step": 5,
      "name": "상대 평가",
      "observation": "대상 PER vs 업종 추정 PER",
      "thinking": "저평가/적정/고평가 판단 근거"
    },
    {
      "step": 6,
      "name": "종합 판단",
      "observation": "펀더멘털, 밸류에이션, 추세 종합",
      "thinking": "투자 매력도 최종 평가"
    },
    {
      "step": 7,
      "name": "목표가 산출",
      "observation": "적정가 범위, 성장성, 상대 밸류",
      "thinking": "상한/중간/하한 중 선택 근거"
    }
  ],
  
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
  
  "analyst_sentiment": {
    "rating": "매우 긍정|긍정|중립|부정|매우 부정",
    "tone_analysis": "증권사 리포트 어조 분석 (자신감 있는지, 방어적인지)",
    "mentioned_risks": ["리스크 요인1", "리스크 요인2"],
    "consensus_view": "시장 컨센서스 요약"
  },
  
  "fundamental_score": "매우 긍정|긍정|중립|부정|매우 부정",
  "summary": "종합 의견 (3-5문장)",
  "confidence": 0.0-1.0,
  "reasoning": "상세 분석 근거 (7단계 추론 포함)"
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
                peer_text += f"**업종 특성을 고려하여 평균 PER 수준을 추론하고 상대 평가하세요**\n"
                
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
            
            # 증권사 리포트 (RAG 검색 또는 SQL)
            from src.storage.models import ResearchReport
            from datetime import timedelta
            
            report_text = ""
            use_rag = True
            
            if use_rag:
                try:
                    from src.rag.vector_store import VectorStore
                    
                    # RAG 검색 (주제별)
                    vs = VectorStore()
                    
                    rag_results = vs.search_reports(
                        query=f"{stock.name} 목표주가 밸류에이션 실적 전망",
                        ticker=ticker,
                        top_k=20  # 많이 가져옴
                    )
                    
                    # RAG 결과를 DB 객체로 매핑하고 시간 필터링
                    if rag_results:
                        cutoff = datetime.now().date() - timedelta(days=90)  # 최근 3개월
                        rag_ids = [r['id'].replace('report_', '') for r in rag_results if r['id'].startswith('report_')]
                        
                        reports = (
                            session.query(ResearchReport)
                            .filter(
                                ResearchReport.id.in_([int(i) for i in rag_ids if i.isdigit()]),
                                ResearchReport.report_date >= cutoff
                            )
                            .order_by(ResearchReport.report_date.desc())
                            .limit(5)
                            .all()
                        )
                        
                        logger.info(f"[FundamentalsAgent] RAG 검색: {len(reports)}개 리포트 (최근 90일)")
                    else:
                        reports = []
                    
                    if not reports:
                        logger.warning(f"[FundamentalsAgent] RAG 결과 없음, SQL fallback")
                        use_rag = False
                
                except Exception as e:
                    logger.warning(f"[FundamentalsAgent] RAG 실패 ({e}), SQL fallback")
                    use_rag = False
            
            if not use_rag:
                # Fallback: SQL (최신순)
                reports = (
                    session.query(ResearchReport)
                    .filter(ResearchReport.stock_id == stock.id)
                    .order_by(ResearchReport.report_date.desc())
                    .limit(5)
                    .all()
                )
                logger.info(f"[FundamentalsAgent] SQL 검색: {len(reports)}개 리포트")
            
            if reports:
                report_text = "\n\n증권사 리포트 (최근 5개, RAG 검색):\n"
                for r in reports:
                    report_text += f"\n  [{r.report_date}] {r.firm}:\n"
                    report_text += f"    - {r.title}\n"
                    if r.opinion:
                        report_text += f"    - 투자의견: {r.opinion}\n"
                    if r.target_price:
                        report_text += f"    - 목표주가: {r.target_price:,.0f}원\n"
            
            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

종목: {stock.name} ({ticker})
업종: {stock.industry or 'N/A'}

재무제표 (최근 8개 분기 = 2년):
{''.join(financials_text)}{peer_text}{valuation_text}{report_text}

분석 시 중점 사항:
1. YoY (전년 동기 대비) 성장률 계산 및 추세 파악
2. QoQ (전분기 대비) 변화 추이 분석
3. 2년간 성장 가속/둔화 여부
4. 계절성 패턴 존재 여부
5. 수익성/안정성 지표의 시계열 추이
6. **밸류에이션 분석** (핵심!)
   - 제공된 PER, 적정가 범위 참조
   - **업종 특성 고려**: 동종업계 정보로 업종 평균 PER 수준 추론
   - **상대 평가**: 대상 PER vs 추론한 업종 평균 비교
   - 성장성/수익성 우수한데 PER 낮으면 → 진짜 저평가
   - 실적 부진한데 PER 낮으면 → 가치함정 주의
7. **목표가 설정**
   - 제공된 적정가 범위 내에서 선택
   - 성장성 우수 + 업종 대비 저평가 → 상한
   - 성장성 보통 + 업종 평균 → 중간
   - 성장성 낮음 + 업종 대비 고평가 → 하한

━━━━━━━━━━━━━━━━━━━━━━
분석 지시사항:
━━━━━━━━━━━━━━━━━━━━━━

1. **반드시 7단계 프로세스를 순서대로 따르세요**
   - 각 단계에서 observation (관찰)과 thinking (추론)을 명확히 구분
   - reasoning_steps 배열에 7개 단계 모두 채우기

2. **각 단계별 예시:**
   
   Step 1 예시:
   "observation": "매출 236억, 순이익 53억, ROE 15.1%, PER 10.77배 확인"
   "thinking": "중소형주치고 ROE가 높은 편. PER은 10배대로 낮은 편"
   
   Step 3 예시:
   "observation": "화장품 업종, 경쟁사는 아모레퍼시픽, LG생활건강"
   "thinking": "화장품은 경기소비재로 일반적 PER 12-15배. 대형사는 브랜드 파워로 더 높을 수 있음"
   
   Step 5 예시:
   "observation": "대상 PER 10.77, 추정 업종 평균 12-15"
   "thinking": "업종 대비 약 10-20% 낮음. 성장률 32%로 높은 편이므로 저평가 판단"

3. **최종 JSON에 reasoning_steps를 반드시 포함**

4. **증권사 리포트 Sentiment 분석** (리포트가 있는 경우):
   - **어조 분석**: 애널리스트의 어조가 자신감 있는지, 방어적인지 판단
     * 자신감: "적극 매수", "강력 추천", "확신", "높은 성장 기대"
     * 방어적: "신중 접근", "리스크 상존", "불확실성", "보수적 추정"
   - **리스크 요인**: 리포트에서 명시적으로 언급된 리스크 추출
   - **컨센서스 뷰**: 여러 증권사의 의견이 일치하는지, 엇갈리는지
   - **목표가 분포**: 증권사들의 목표가가 현재가 대비 어느 정도인지
   - analyst_sentiment 필드에 반영

5. **최종 평가 (fundamental_score)**:
   - 재무 건전성 + 성장성 + 밸류에이션 + 증권사 컨센서스 종합
   - **매우 긍정**: 펀더멘털 우수 + 저평가 + 증권사 강력 추천
   - **긍정**: 펀더멘털 양호 + 적정가 이하 + 증권사 긍정적
   - **중립**: 펀더멘털 보통 + 적정가 수준 + 증권사 중립
   - **부정**: 펀더멘털 부진 or 고평가 or 증권사 부정적
   - **매우 부정**: 펀더멘털 악화 + 고평가 + 증권사 매도 의견

위 재무 데이터, 동종업계 비교, 밸류에이션, 증권사 리포트를 종합하여 **마크다운 형식**으로 분석 결과를 작성하세요.

반드시 다음 내용을 포함하되, 자유로운 형식으로 작성하십시오:
- 7단계 추론 과정 (Chain-of-Thought)
- 밸류에이션 평가 (저평가/적정/고평가)
- 증권사 sentiment (매우 긍정 ~ 매우 부정)
- 펀더멘털 종합 점수 (5단계)
- YoY/QoQ 비교 및 추세 분석

마크다운 헤더(##, ###)와 강조(**bold**)를 적극 활용하세요.
"""

            try:
                response_text = self.generate(prompt)
                
                # 텍스트에서 간단한 정보 추출
                valuation = "undervalued"  # 기본값
                if any(word in response_text for word in ["저평가", "undervalued", "매력적"]):
                    valuation = "undervalued"
                elif any(word in response_text for word in ["고평가", "overvalued", "과대평가"]):
                    valuation = "overvalued"
                elif any(word in response_text for word in ["적정", "fair", "중립"]):
                    valuation = "fair"
                
                result = {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "valuation": {"rating": valuation},
                    "fundamental_score": "긍정",  # 기본값
                    "confidence": 0.85,
                    "summary": response_text,  # 전체 마크다운 텍스트
                    "analyzed_at": datetime.now().isoformat()
                }

                logger.info(
                    f"[FundamentalsAgent] {ticker} 분석 완료: {valuation}"
                )

                return result

            except Exception as e:
                logger.error(f"[FundamentalsAgent] {ticker} 분석 실패: {e}")
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "error": str(e),
                }
