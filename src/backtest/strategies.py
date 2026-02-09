"""
백테스팅 전략 모음

다양한 투자 전략을 제공합니다.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional

from src.storage.database import Database
from src.storage.models import Stock, PriceData, TechnicalIndicator


class TradingStrategy:
    """전략 기본 클래스"""

    def __init__(self, db: Database):
        self.db = db
        self.cache = {}

    def get_technical_indicator(
        self,
        ticker: str,
        date: datetime,
        indicator: str
    ) -> Optional[float]:
        """기술적 지표 조회 (캐싱)"""
        cache_key = f"{ticker}_{date}_{indicator}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return None

            tech = session.query(TechnicalIndicator).filter(
                TechnicalIndicator.stock_id == stock.id,
                TechnicalIndicator.date == date
            ).first()

            if not tech:
                return None

            value = getattr(tech, indicator, None)
            self.cache[cache_key] = value
            return value


def sma_crossover_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    **kwargs
) -> str:
    """SMA 골든크로스/데드크로스 전략
    
    - SMA20 > SMA50: 매수
    - SMA20 < SMA50: 매도
    """
    if not db or not ticker:
        return 'hold'

    strategy = TradingStrategy(db)
    
    sma_20 = strategy.get_technical_indicator(ticker, date, 'sma_20')
    sma_50 = strategy.get_technical_indicator(ticker, date, 'sma_50')
    
    if sma_20 is None or sma_50 is None:
        return 'hold'
    
    # 골든크로스: 매수
    if sma_20 > sma_50 and shares == 0:
        return 'buy'
    
    # 데드크로스: 매도
    if sma_20 < sma_50 and shares > 0:
        return 'sell'
    
    return 'hold'


def rsi_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    oversold: float = 30,
    overbought: float = 70,
    **kwargs
) -> str:
    """RSI 과매도/과매수 전략
    
    - RSI < 30: 매수
    - RSI > 70: 매도
    """
    if not db or not ticker:
        return 'hold'

    strategy = TradingStrategy(db)
    rsi = strategy.get_technical_indicator(ticker, date, 'rsi')
    
    if rsi is None:
        return 'hold'
    
    # 과매도: 매수
    if rsi < oversold and shares == 0:
        return 'buy'
    
    # 과매수: 매도
    if rsi > overbought and shares > 0:
        return 'sell'
    
    return 'hold'


def macd_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    **kwargs
) -> str:
    """MACD 크로스오버 전략
    
    - MACD > Signal: 매수
    - MACD < Signal: 매도
    """
    if not db or not ticker:
        return 'hold'

    strategy = TradingStrategy(db)
    macd = strategy.get_technical_indicator(ticker, date, 'macd')
    macd_signal = strategy.get_technical_indicator(ticker, date, 'macd_signal')
    
    if macd is None or macd_signal is None:
        return 'hold'
    
    # MACD 크로스오버: 매수
    if macd > macd_signal and shares == 0:
        return 'buy'
    
    # MACD 크로스언더: 매도
    if macd < macd_signal and shares > 0:
        return 'sell'
    
    return 'hold'


def bollinger_bands_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    **kwargs
) -> str:
    """볼린저 밴드 전략
    
    - 가격 < 하단 밴드: 매수
    - 가격 > 상단 밴드: 매도
    """
    if not db or not ticker:
        return 'hold'

    strategy = TradingStrategy(db)
    bb_upper = strategy.get_technical_indicator(ticker, date, 'bb_upper')
    bb_lower = strategy.get_technical_indicator(ticker, date, 'bb_lower')
    
    if bb_upper is None or bb_lower is None:
        return 'hold'
    
    # 하단 돌파: 매수
    if price < bb_lower and shares == 0:
        return 'buy'
    
    # 상단 돌파: 매도
    if price > bb_upper and shares > 0:
        return 'sell'
    
    return 'hold'


def momentum_strategy(
    date: datetime,
    price: float,
    cash: float,
    shares: float,
    ticker: str = None,
    db: Database = None,
    lookback: int = 20,
    threshold: float = 0.05,
    **kwargs
) -> str:
    """모멘텀 전략
    
    - N일 수익률 > threshold: 매수
    - N일 수익률 < -threshold: 매도
    """
    if not db or not ticker:
        return 'hold'

    with db.get_session() as session:
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            return 'hold'

        # N일 전 가격
        past_date = date - timedelta(days=lookback + 10)
        prices = session.query(PriceData).filter(
            PriceData.stock_id == stock.id,
            PriceData.date >= past_date,
            PriceData.date <= date
        ).order_by(PriceData.date).all()

        if len(prices) < lookback:
            return 'hold'

        past_price = prices[-lookback].close
        momentum = (price / past_price) - 1

        # 강한 상승 모멘텀: 매수
        if momentum > threshold and shares == 0:
            return 'buy'
        
        # 강한 하락 모멘텀: 매도
        if momentum < -threshold and shares > 0:
            return 'sell'
    
    return 'hold'


# 전략 매핑
STRATEGIES = {
    'sma_crossover': sma_crossover_strategy,
    'rsi': rsi_strategy,
    'macd': macd_strategy,
    'bollinger_bands': bollinger_bands_strategy,
    'momentum': momentum_strategy,
}
