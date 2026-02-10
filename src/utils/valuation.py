#!/usr/bin/env python3
"""밸류에이션 계산 유틸리티

TTM 기반 PER/PBR/EPS 계산
"""
from typing import Dict, Optional
from datetime import datetime, timedelta


def calculate_ttm_metrics(session, stock_id: int, current_price: float, market_cap: float = None) -> Optional[Dict]:
    """TTM (Trailing 12 Months) 기반 밸류에이션 지표 계산
    
    Args:
        session: SQLAlchemy 세션
        stock_id: Stock ID
        current_price: 현재가
        market_cap: 시가총액 (없으면 계산)
        
    Returns:
        {
            'ttm_revenue': float,
            'ttm_net_income': float,
            'ttm_operating_income': float,
            'shares_outstanding': float,
            'eps': float,
            'per': float,
            'bps': float,
            'pbr': float,
        }
    """
    from src.storage.models import FinancialStatement, Stock
    
    # 최근 4분기 재무제표 (OpenDartReader 우선)
    statements = (
        session.query(FinancialStatement)
        .filter(FinancialStatement.stock_id == stock_id)
        .filter(FinancialStatement.source == 'opendartreader')
        .order_by(FinancialStatement.period_end.desc())
        .limit(4)
        .all()
    )
    
    if len(statements) < 4:
        # 4분기 미만이면 계산 불가
        return None
    
    # TTM 합산
    ttm_revenue = 0
    ttm_net_income = 0
    ttm_operating_income = 0
    latest_equity = None
    
    for stmt in statements:
        if stmt.raw_data:
            data = stmt.raw_data
            ttm_revenue += data.get('revenue', 0)
            ttm_net_income += data.get('net_income', 0)
            ttm_operating_income += data.get('operating_income', 0)
            
            # 최신 자본총계
            if latest_equity is None and data.get('total_equity'):
                latest_equity = data['total_equity']
    
    # 시가총액 확보
    if not market_cap:
        stock = session.query(Stock).get(stock_id)
        if stock and stock.market_cap:
            market_cap = stock.market_cap
        else:
            # 시가총액 없으면 계산 불가
            return None
    
    # 주식수 계산
    shares_outstanding = market_cap / current_price if current_price > 0 else 0
    
    if shares_outstanding <= 0:
        return None
    
    # EPS 계산
    eps = ttm_net_income / shares_outstanding if shares_outstanding > 0 else 0
    
    # PER 계산
    per = current_price / eps if eps > 0 else None
    
    # BPS 계산
    bps = latest_equity / shares_outstanding if latest_equity and shares_outstanding > 0 else 0
    
    # PBR 계산
    pbr = current_price / bps if bps > 0 else None
    
    result = {
        'ttm_revenue': ttm_revenue,
        'ttm_net_income': ttm_net_income,
        'ttm_operating_income': ttm_operating_income,
        'shares_outstanding': shares_outstanding,
        'eps': eps,
        'per': per,
        'bps': bps,
        'pbr': pbr,
        'total_equity': latest_equity,
        'quarters_used': len(statements),
    }
    
    return result


def calculate_fair_value(eps: float, per_range: tuple = (10, 15)) -> Dict:
    """적정가 범위 계산
    
    Args:
        eps: 주당순이익
        per_range: PER 범위 (하한, 상한)
        
    Returns:
        {
            'conservative': float (PER 하한),
            'fair': float (PER 중간),
            'optimistic': float (PER 상한)
        }
    """
    per_low, per_high = per_range
    per_mid = (per_low + per_high) / 2
    
    return {
        'conservative': eps * per_low,
        'fair': eps * per_mid,
        'optimistic': eps * per_high,
    }


def get_valuation_summary(session, stock_id: int, current_price: float, market_cap: float = None) -> Optional[Dict]:
    """종목 밸류에이션 요약
    
    Args:
        session: SQLAlchemy 세션
        stock_id: Stock ID
        current_price: 현재가
        market_cap: 시가총액
        
    Returns:
        TTM 지표 + 적정가 범위
    """
    ttm = calculate_ttm_metrics(session, stock_id, current_price, market_cap)
    
    if not ttm or not ttm.get('eps') or ttm['eps'] <= 0:
        return None
    
    # 적정가 범위 (PER 10-15배)
    fair_values = calculate_fair_value(ttm['eps'], per_range=(10, 15))
    
    # 성장주 범위 (PER 15-20배)
    growth_values = calculate_fair_value(ttm['eps'], per_range=(15, 20))
    
    result = {
        **ttm,
        'fair_value_range': fair_values,
        'growth_value_range': growth_values,
        'current_price': current_price,
        'upside_conservative': ((fair_values['conservative'] - current_price) / current_price * 100) if current_price > 0 else None,
        'upside_fair': ((fair_values['fair'] - current_price) / current_price * 100) if current_price > 0 else None,
        'upside_optimistic': ((fair_values['optimistic'] - current_price) / current_price * 100) if current_price > 0 else None,
    }
    
    return result


def format_valuation_text(valuation: Dict) -> str:
    """밸류에이션 텍스트 포맷
    
    Args:
        valuation: get_valuation_summary() 결과
        
    Returns:
        포맷된 텍스트
    """
    if not valuation:
        return "밸류에이션 계산 불가 (데이터 부족)"
    
    text = f"""
TTM 기반 밸류에이션 ({valuation['quarters_used']}개 분기):

매출: {valuation['ttm_revenue']/1e8:.0f}억원
영업이익: {valuation['ttm_operating_income']/1e8:.0f}억원
순이익: {valuation['ttm_net_income']/1e8:.0f}억원

주식수: {valuation['shares_outstanding']:,.0f}주
EPS: {valuation['eps']:,.0f}원
PER: {valuation['per']:.2f}배

BPS: {valuation['bps']:,.0f}원
PBR: {valuation['pbr']:.2f}배

적정가 범위 (PER 10-15배):
  보수적 (PER 10): {valuation['fair_value_range']['conservative']:,.0f}원 ({valuation['upside_conservative']:+.1f}%)
  중립적 (PER 12.5): {valuation['fair_value_range']['fair']:,.0f}원 ({valuation['upside_fair']:+.1f}%)
  낙관적 (PER 15): {valuation['fair_value_range']['optimistic']:,.0f}원 ({valuation['upside_optimistic']:+.1f}%)
"""
    
    return text


def main():
    """테스트"""
    import sys
    from src.storage.database import init_db
    from src.storage.models import Stock, PriceData
    from src.utils.helpers import load_config
    
    config = load_config()
    db = init_db(config)
    
    ticker = sys.argv[1] if len(sys.argv) > 1 else '123330'
    
    with db.get_session() as session:
        stock = session.query(Stock).filter(Stock.ticker == ticker).first()
        
        if not stock:
            print(f"종목 {ticker} 없음")
            return
        
        # 현재가
        price = session.query(PriceData).filter(
            PriceData.stock_id == stock.id
        ).order_by(PriceData.date.desc()).first()
        
        if not price:
            print("주가 데이터 없음")
            return
        
        print(f"\n{stock.name} ({ticker})")
        print("=" * 60)
        
        # 밸류에이션 계산
        valuation = get_valuation_summary(
            session,
            stock.id,
            price.close,
            stock.market_cap
        )
        
        if valuation:
            print(format_valuation_text(valuation))
        else:
            print("밸류에이션 계산 불가 (4분기 데이터 부족)")


if __name__ == "__main__":
    main()
