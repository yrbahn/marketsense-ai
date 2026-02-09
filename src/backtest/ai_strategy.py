"""
AI 에이전트 기반 백테스팅 전략

복합 기술적 지표를 조합한 AI 스코어링 시스템으로
BUY/SELL/HOLD 신호를 생성합니다.

향후 실제 LLM 에이전트 통합 예정.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from src.storage.database import Database
from src.storage.models import Stock, TechnicalIndicator

logger = logging.getLogger("marketsense")


def get_technical_indicators(
    db: Database,
    ticker: str,
    date: datetime
) -> Optional[Dict]:
    """기술적 지표 조회"""
    with db.get_session() as session:
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            return None

        tech = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id,
            TechnicalIndicator.date == date
        ).first()

        if not tech:
            return None

        return {
            'sma_20': tech.sma_20,
            'sma_50': tech.sma_50,
            'sma_200': tech.sma_200,
            'rsi': tech.rsi_14,
            'macd': tech.macd,
            'macd_signal': tech.macd_signal,
            'bb_upper': tech.bb_upper,
            'bb_middle': tech.bb_middle,
            'bb_lower': tech.bb_lower,
        }


def calculate_ai_score(
    price: float,
    indicators: Dict
) -> float:
    """AI 스코어 계산 (복합 지표)
    
    여러 기술적 지표를 종합하여 -1 ~ +1 점수 산출
    - +1: 강한 매수 신호
    - 0: 중립
    - -1: 강한 매도 신호
    """
    score = 0.0
    weight_sum = 0.0
    
    # 1. SMA 추세 (가중치: 0.3)
    if indicators.get('sma_20') and indicators.get('sma_50'):
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        
        if price > sma_20 > sma_50:
            score += 1.0 * 0.3  # 강한 상승
        elif price > sma_20:
            score += 0.5 * 0.3  # 약한 상승
        elif price < sma_20 < sma_50:
            score -= 1.0 * 0.3  # 강한 하락
        elif price < sma_20:
            score -= 0.5 * 0.3  # 약한 하락
        
        weight_sum += 0.3
    
    # 2. RSI (가중치: 0.25)
    if indicators.get('rsi'):
        rsi = indicators['rsi']
        
        if rsi < 30:
            score += 1.0 * 0.25  # 과매도
        elif rsi < 40:
            score += 0.5 * 0.25  # 약한 과매도
        elif rsi > 70:
            score -= 1.0 * 0.25  # 과매수
        elif rsi > 60:
            score -= 0.5 * 0.25  # 약한 과매수
        
        weight_sum += 0.25
    
    # 3. MACD (가중치: 0.25)
    if indicators.get('macd') and indicators.get('macd_signal'):
        macd = indicators['macd']
        signal = indicators['macd_signal']
        
        if macd > signal and macd > 0:
            score += 1.0 * 0.25  # 강한 상승 모멘텀
        elif macd > signal:
            score += 0.5 * 0.25  # 약한 상승 모멘텀
        elif macd < signal and macd < 0:
            score -= 1.0 * 0.25  # 강한 하락 모멘텀
        elif macd < signal:
            score -= 0.5 * 0.25  # 약한 하락 모멘텀
        
        weight_sum += 0.25
    
    # 4. 볼린저 밴드 (가중치: 0.2)
    if indicators.get('bb_upper') and indicators.get('bb_lower'):
        bb_upper = indicators['bb_upper']
        bb_lower = indicators['bb_lower']
        bb_middle = indicators.get('bb_middle', (bb_upper + bb_lower) / 2)
        
        if price < bb_lower:
            score += 1.0 * 0.2  # 하단 돌파 (매수)
        elif price < bb_middle:
            score += 0.3 * 0.2  # 중간 아래
        elif price > bb_upper:
            score -= 1.0 * 0.2  # 상단 돌파 (매도)
        elif price > bb_middle:
            score -= 0.3 * 0.2  # 중간 위
        
        weight_sum += 0.2
    
    # 정규화
    if weight_sum > 0:
        score = score / weight_sum
    
    return max(-1.0, min(1.0, score))


def ai_signal_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    buy_threshold: float = 0.4,
    sell_threshold: float = -0.4,
    **kwargs
) -> str:
    """AI 복합 지표 전략
    
    여러 기술적 지표를 종합한 AI 스코어로 매매 결정
    
    Args:
        date: 현재 날짜
        price: 현재 가격
        cash: 현재 현금
        shares: 현재 보유 주식 수
        ticker: 종목 코드
        db: Database instance
        buy_threshold: 매수 임계값 (기본: 0.4)
        sell_threshold: 매도 임계값 (기본: -0.4)
        
    Returns:
        'buy' | 'sell' | 'hold'
    """
    if not db or not ticker:
        return 'hold'
    
    try:
        # 기술적 지표 조회
        indicators = get_technical_indicators(db, ticker, date)
        
        if not indicators:
            return 'hold'
        
        # AI 스코어 계산
        score = calculate_ai_score(price, indicators)
        
        # 신호 결정
        if score >= buy_threshold and shares == 0:
            return 'buy'  # 강한 매수 신호
        elif score <= sell_threshold and shares > 0:
            return 'sell'  # 강한 매도 신호
        else:
            return 'hold'
        
    except Exception as e:
        logger.warning(f"[AI Signal] {ticker} {date}: {e}")
        return 'hold'
