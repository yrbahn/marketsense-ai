"""
백테스팅 엔진

과거 데이터로 투자 전략을 시뮬레이션하고 성과를 평가합니다.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from src.storage.database import Database
from src.storage.models import Stock, PriceData


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    portfolio_values: pd.Series
    trades: List[Dict]
    benchmark_return: Optional[float] = None


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(
        self,
        db: Database,
        initial_capital: float = 10_000_000,  # 1천만원
        commission: float = 0.0015,  # 0.15% 수수료
        slippage: float = 0.0005,  # 0.05% 슬리피지
    ):
        """
        Args:
            db: Database instance
            initial_capital: 초기 자금
            commission: 거래 수수료 (매수/매도)
            slippage: 슬리피지 (체결가 차이)
        """
        self.db = db
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def get_price_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.Series:
        """종목 가격 데이터 조회
        
        Returns:
            Series: 날짜별 종가 (index: date)
        """
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                raise ValueError(f"종목을 찾을 수 없습니다: {ticker}")

            prices = session.query(PriceData).filter(
                PriceData.stock_id == stock.id,
                PriceData.date >= start_date,
                PriceData.date <= end_date
            ).order_by(PriceData.date).all()

            if not prices:
                raise ValueError(f"{ticker} 가격 데이터가 없습니다")

            dates = [p.date for p in prices]
            closes = [p.close for p in prices]
            
            return pd.Series(closes, index=dates, name=ticker)

    def calculate_metrics(
        self,
        portfolio_values: pd.Series,
        trades: List[Dict],
        benchmark_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.035
    ) -> Dict:
        """성과 지표 계산
        
        Args:
            portfolio_values: 날짜별 포트폴리오 가치
            trades: 거래 기록
            benchmark_returns: 벤치마크 수익률 (옵션)
            risk_free_rate: 무위험 수익률
            
        Returns:
            성과 지표 딕셔너리
        """
        # 기본 통계
        initial_value = portfolio_values.iloc[0]
        final_value = portfolio_values.iloc[-1]
        total_return = (final_value / initial_value) - 1

        # 연간 수익률 (CAGR)
        days = (portfolio_values.index[-1] - portfolio_values.index[0]).days
        years = days / 365.25
        annual_return = (final_value / initial_value) ** (1 / years) - 1 if years > 0 else 0

        # 일별 수익률
        daily_returns = portfolio_values.pct_change().dropna()

        # 변동성 (연율화)
        volatility = daily_returns.std() * np.sqrt(252)

        # 샤프비율
        excess_return = annual_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0

        # 최대 낙폭 (MDD)
        cummax = portfolio_values.cummax()
        drawdown = (portfolio_values - cummax) / cummax
        max_drawdown = drawdown.min()

        # 승률 (수익 일수 / 전체 일수)
        win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0

        # 거래 횟수
        num_trades = len([t for t in trades if t['action'] in ['buy', 'sell']])

        metrics = {
            'initial_capital': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': num_trades,
        }

        # 벤치마크 대비 알파
        if benchmark_returns is not None:
            benchmark_total = (1 + benchmark_returns).prod() - 1
            metrics['benchmark_return'] = benchmark_total
            metrics['alpha'] = total_return - benchmark_total

        return metrics

    def run_buy_hold(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Buy & Hold 전략 (벤치마크)
        
        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일
            
        Returns:
            백테스트 결과
        """
        prices = self.get_price_data(ticker, start_date, end_date)
        
        # 초기 매수
        initial_price = prices.iloc[0]
        shares = self.initial_capital / initial_price
        
        # 보유
        portfolio_values = prices * shares
        
        # 거래 기록
        trades = [
            {
                'date': prices.index[0],
                'action': 'buy',
                'price': initial_price,
                'shares': shares,
                'value': self.initial_capital
            }
        ]
        
        # 성과 계산
        metrics = self.calculate_metrics(portfolio_values, trades)
        
        return BacktestResult(
            strategy_name=f"Buy & Hold ({ticker})",
            start_date=start_date,
            end_date=end_date,
            portfolio_values=portfolio_values,
            trades=trades,
            **metrics
        )

    def run_strategy(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        strategy_func: Callable,
        benchmark: Optional[str] = None,
        **strategy_params
    ) -> BacktestResult:
        """커스텀 전략 백테스트
        
        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일
            strategy_func: 전략 함수 (date, price, position) -> action
            benchmark: 벤치마크 종목 (옵션)
            **strategy_params: 전략 파라미터
            
        Returns:
            백테스트 결과
        """
        prices = self.get_price_data(ticker, start_date, end_date)
        
        cash = self.initial_capital
        shares = 0
        portfolio_values = []
        trades = []
        
        # 전략에 ticker와 db 자동 전달
        strategy_params['ticker'] = ticker
        strategy_params['db'] = self.db
        
        for date, price in prices.items():
            # 전략 신호
            action = strategy_func(
                date=date,
                price=price,
                cash=cash,
                shares=shares,
                **strategy_params
            )
            
            # 매수
            if action == 'buy' and cash > 0:
                # 수수료 + 슬리피지
                effective_price = price * (1 + self.slippage)
                max_shares = cash / effective_price
                buy_shares = max_shares * 0.99  # 99% 매수 (여유)
                cost = buy_shares * effective_price * (1 + self.commission)
                
                if cost <= cash:
                    cash -= cost
                    shares += buy_shares
                    trades.append({
                        'date': date,
                        'action': 'buy',
                        'price': price,
                        'shares': buy_shares,
                        'value': cost
                    })
            
            # 매도
            elif action == 'sell' and shares > 0:
                effective_price = price * (1 - self.slippage)
                revenue = shares * effective_price * (1 - self.commission)
                cash += revenue
                trades.append({
                    'date': date,
                    'action': 'sell',
                    'price': price,
                    'shares': shares,
                    'value': revenue
                })
                shares = 0
            
            # 포트폴리오 가치
            portfolio_value = cash + (shares * price)
            portfolio_values.append(portfolio_value)
        
        portfolio_series = pd.Series(portfolio_values, index=prices.index)
        
        # 벤치마크
        benchmark_returns = None
        if benchmark:
            try:
                benchmark_prices = self.get_price_data(benchmark, start_date, end_date)
                benchmark_returns = benchmark_prices.pct_change().dropna()
            except:
                pass
        
        # 성과 계산
        metrics = self.calculate_metrics(
            portfolio_series,
            trades,
            benchmark_returns
        )
        
        return BacktestResult(
            strategy_name=strategy_params.get('name', 'Custom Strategy'),
            start_date=start_date,
            end_date=end_date,
            portfolio_values=portfolio_series,
            trades=trades,
            **metrics
        )
