"""동종업계 비교 분석

Peer Comparison for Valuation Analysis
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy import func

from src.storage.models import Stock, FinancialStatement, PriceData

logger = logging.getLogger("marketsense")


def get_peer_stocks(session, ticker: str, limit: int = 10) -> List[Stock]:
    """동종업계 종목 조회
    
    Args:
        session: DB 세션
        ticker: 대상 종목 코드
        limit: 반환할 종목 수
        
    Returns:
        동종업계 종목 리스트
    """
    # 대상 종목
    target_stock = session.query(Stock).filter(Stock.ticker == ticker).first()
    
    if not target_stock or not target_stock.sector or target_stock.sector == '기타':
        return []
    
    # 같은 업종의 다른 종목 (시총 기준 상위)
    peers = session.query(Stock).filter(
        Stock.sector == target_stock.sector,
        Stock.ticker != ticker,
        Stock.market_cap.isnot(None)
    ).order_by(
        Stock.market_cap.desc()
    ).limit(limit).all()
    
    return peers


def calculate_peer_metrics(session, peers: List[Stock]) -> Dict:
    """동종업계 평균 지표 계산
    
    Args:
        session: DB 세션
        peers: 동종업계 종목 리스트
        
    Returns:
        {'avg_pe': float, 'avg_pb': float, ...}
    """
    if not peers:
        return {}
    
    metrics = {
        'count': len(peers),
        'avg_market_cap': 0,
        'avg_pe': None,
        'avg_pb': None,
        'avg_debt_ratio': None,
        'avg_roe': None,
    }
    
    # 시총 평균
    market_caps = [p.market_cap for p in peers if p.market_cap]
    if market_caps:
        metrics['avg_market_cap'] = sum(market_caps) / len(market_caps)
    
    # 재무 지표 평균 (최근 데이터 사용)
    pe_ratios = []
    pb_ratios = []
    debt_ratios = []
    roes = []
    
    for peer in peers:
        # 최근 재무제표
        stmt = session.query(FinancialStatement).filter(
            FinancialStatement.stock_id == peer.id
        ).order_by(
            FinancialStatement.period_end.desc()
        ).first()
        
        if not stmt:
            continue
        
        # 최근 주가
        price_data = session.query(PriceData).filter(
            PriceData.stock_id == peer.id
        ).order_by(
            PriceData.date.desc()
        ).first()
        
        if price_data and stmt.eps and stmt.eps > 0:
            pe = price_data.close / stmt.eps
            if 0 < pe < 100:  # 이상치 제거
                pe_ratios.append(pe)
        
        if price_data and stmt.total_equity and peer.market_cap:
            # P/B 계산
            bps = stmt.total_equity / peer.market_cap if peer.market_cap else 0
            if bps > 0:
                pb = price_data.close / bps
                if 0 < pb < 10:
                    pb_ratios.append(pb)
        
        if stmt.total_liabilities and stmt.total_equity and stmt.total_equity > 0:
            debt_ratio = (stmt.total_liabilities / stmt.total_equity) * 100
            if 0 < debt_ratio < 500:
                debt_ratios.append(debt_ratio)
        
        if stmt.net_income and stmt.total_equity and stmt.total_equity > 0:
            roe = (stmt.net_income / stmt.total_equity) * 100
            if -50 < roe < 100:
                roes.append(roe)
    
    # 평균 계산
    if pe_ratios:
        metrics['avg_pe'] = sum(pe_ratios) / len(pe_ratios)
    
    if pb_ratios:
        metrics['avg_pb'] = sum(pb_ratios) / len(pb_ratios)
    
    if debt_ratios:
        metrics['avg_debt_ratio'] = sum(debt_ratios) / len(debt_ratios)
    
    if roes:
        metrics['avg_roe'] = sum(roes) / len(roes)
    
    return metrics


def compare_with_peers(session, ticker: str) -> Dict:
    """동종업계 대비 밸류에이션 비교
    
    Args:
        session: DB 세션
        ticker: 종목 코드
        
    Returns:
        {
            'sector': str,
            'peers': [...],
            'peer_metrics': {...},
            'comparison': {
                'pe_vs_sector': str,  # '저평가' / '적정' / '고평가'
                'pb_vs_sector': str,
                ...
            }
        }
    """
    # 대상 종목
    target = session.query(Stock).filter(Stock.ticker == ticker).first()
    
    if not target:
        return {}
    
    # 동종업계 종목
    peers = get_peer_stocks(session, ticker, limit=10)
    
    if not peers:
        return {
            'sector': target.sector or '미분류',
            'peers': [],
            'peer_metrics': {},
            'comparison': {}
        }
    
    # 동종업계 평균 지표
    peer_metrics = calculate_peer_metrics(session, peers)
    
    # 대상 종목 지표
    target_stmt = session.query(FinancialStatement).filter(
        FinancialStatement.stock_id == target.id
    ).order_by(
        FinancialStatement.period_end.desc()
    ).first()
    
    target_price = session.query(PriceData).filter(
        PriceData.stock_id == target.id
    ).order_by(
        PriceData.date.desc()
    ).first()
    
    comparison = {}
    
    if target_stmt and target_price and peer_metrics:
        # P/E 비교
        if target_stmt.eps and target_stmt.eps > 0 and peer_metrics.get('avg_pe'):
            target_pe = target_price.close / target_stmt.eps
            avg_pe = peer_metrics['avg_pe']
            
            if target_pe < avg_pe * 0.8:
                comparison['pe_vs_sector'] = '저평가'
            elif target_pe > avg_pe * 1.2:
                comparison['pe_vs_sector'] = '고평가'
            else:
                comparison['pe_vs_sector'] = '적정'
            
            comparison['target_pe'] = target_pe
            comparison['sector_avg_pe'] = avg_pe
        
        # 부채비율 비교
        if (target_stmt.total_liabilities and target_stmt.total_equity and 
            target_stmt.total_equity > 0 and peer_metrics.get('avg_debt_ratio')):
            target_debt = (target_stmt.total_liabilities / target_stmt.total_equity) * 100
            avg_debt = peer_metrics['avg_debt_ratio']
            
            if target_debt < avg_debt * 0.8:
                comparison['debt_vs_sector'] = '우수'
            elif target_debt > avg_debt * 1.2:
                comparison['debt_vs_sector'] = '주의'
            else:
                comparison['debt_vs_sector'] = '평균'
            
            comparison['target_debt_ratio'] = target_debt
            comparison['sector_avg_debt_ratio'] = avg_debt
    
    return {
        'sector': target.sector or '미분류',
        'peers': [{'ticker': p.ticker, 'name': p.name, 'market_cap': p.market_cap} for p in peers],
        'peer_metrics': peer_metrics,
        'comparison': comparison
    }
