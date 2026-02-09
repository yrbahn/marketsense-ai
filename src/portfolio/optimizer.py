"""
포트폴리오 최적화 엔진 (Markowitz Modern Portfolio Theory)

주요 기능:
- 효율적 투자선 (Efficient Frontier) 계산
- 샤프비율 최대화 포트폴리오
- 최소 분산 포트폴리오
- AI 신호 기반 제약 조건
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.storage.database import Database
from src.storage.models import Stock, PriceData


class PortfolioOptimizer:
    """포트폴리오 최적화"""

    def __init__(self, db: Database, risk_free_rate: float = 0.035):
        """
        Args:
            db: Database instance
            risk_free_rate: 무위험 수익률 (연율, 한국 국고채 3.5%)
        """
        self.db = db
        self.risk_free_rate = risk_free_rate

    def get_returns(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """종목별 일별 수익률 계산
        
        Returns:
            DataFrame: 날짜 × 종목 수익률 (컬럼: 티커)
        """
        returns_data = {}
        
        with self.db.get_session() as session:
            for ticker in tickers:
                stock = session.query(Stock).filter_by(ticker=ticker).first()
                if not stock:
                    continue

                prices = session.query(PriceData).filter(
                    PriceData.stock_id == stock.id,
                    PriceData.date >= start_date,
                    PriceData.date <= end_date
                ).order_by(PriceData.date).all()

                if len(prices) < 2:
                    continue

                dates = [p.date for p in prices]
                closes = [p.close for p in prices]
                
                # 일별 수익률 계산
                daily_returns = pd.Series(closes, index=dates).pct_change().dropna()
                returns_data[ticker] = daily_returns

        return pd.DataFrame(returns_data)

    def calculate_portfolio_stats(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray
    ) -> Tuple[float, float, float]:
        """포트폴리오 통계 계산
        
        Args:
            weights: 종목별 비중 (합=1)
            mean_returns: 평균 수익률
            cov_matrix: 공분산 행렬
            
        Returns:
            (연간 수익률, 연간 변동성, 샤프비율)
        """
        # 연간 수익률 (252 거래일)
        portfolio_return = np.sum(mean_returns * weights) * 252
        
        # 연간 변동성
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
        
        # 샤프비율
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std
        
        return portfolio_return, portfolio_std, sharpe_ratio

    def max_sharpe_ratio(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """샤프비율 최대화 포트폴리오
        
        Args:
            mean_returns: 평균 수익률
            cov_matrix: 공분산 행렬
            constraints: 제약 조건 (min_weight, max_weight)
            
        Returns:
            최적 포트폴리오 정보
        """
        num_assets = len(mean_returns)
        
        # 목적함수: 샤프비율의 음수 (최소화)
        def neg_sharpe(weights):
            p_ret, p_std, sharpe = self.calculate_portfolio_stats(
                weights, mean_returns, cov_matrix
            )
            return -sharpe

        # 제약 조건
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 비중 합 = 1
        ]
        
        # 개별 종목 비중 제한
        min_weight = constraints.get('min_weight', 0.0) if constraints else 0.0
        max_weight = constraints.get('max_weight', 1.0) if constraints else 1.0
        bounds = tuple((min_weight, max_weight) for _ in range(num_assets))
        
        # 초기값 (균등 분배)
        init_guess = np.array([1.0 / num_assets] * num_assets)
        
        # 최적화 실행
        result = minimize(
            neg_sharpe,
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        optimal_weights = result.x
        ret, std, sharpe = self.calculate_portfolio_stats(
            optimal_weights, mean_returns, cov_matrix
        )
        
        return {
            'weights': optimal_weights,
            'return': ret,
            'volatility': std,
            'sharpe_ratio': sharpe,
            'success': result.success
        }

    def min_variance(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """최소 분산 포트폴리오
        
        Returns:
            최적 포트폴리오 정보
        """
        num_assets = len(mean_returns)
        
        # 목적함수: 분산
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights)) * 252

        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        min_weight = constraints.get('min_weight', 0.0) if constraints else 0.0
        max_weight = constraints.get('max_weight', 1.0) if constraints else 1.0
        bounds = tuple((min_weight, max_weight) for _ in range(num_assets))
        
        init_guess = np.array([1.0 / num_assets] * num_assets)
        
        result = minimize(
            portfolio_variance,
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        optimal_weights = result.x
        ret, std, sharpe = self.calculate_portfolio_stats(
            optimal_weights, mean_returns, cov_matrix
        )
        
        return {
            'weights': optimal_weights,
            'return': ret,
            'volatility': std,
            'sharpe_ratio': sharpe,
            'success': result.success
        }

    def efficient_frontier(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        num_portfolios: int = 100
    ) -> pd.DataFrame:
        """효율적 투자선 계산
        
        Args:
            num_portfolios: 시뮬레이션할 포트폴리오 수
            
        Returns:
            DataFrame: 수익률, 변동성, 샤프비율
        """
        results = []
        num_assets = len(mean_returns)
        
        for _ in range(num_portfolios):
            # 랜덤 가중치
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)
            
            ret, std, sharpe = self.calculate_portfolio_stats(
                weights, mean_returns, cov_matrix
            )
            
            results.append({
                'return': ret,
                'volatility': std,
                'sharpe_ratio': sharpe
            })
        
        return pd.DataFrame(results)

    def optimize(
        self,
        tickers: List[str],
        lookback_days: int = 252,
        method: str = 'max_sharpe',
        constraints: Optional[Dict] = None
    ) -> Dict:
        """포트폴리오 최적화 실행
        
        Args:
            tickers: 종목 리스트
            lookback_days: 과거 데이터 기간 (일)
            method: 'max_sharpe' or 'min_variance'
            constraints: 제약 조건
            
        Returns:
            최적 포트폴리오 + 메타데이터
        """
        # 데이터 기간
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 100)
        
        # 수익률 계산
        returns_df = self.get_returns(tickers, start_date, end_date)
        
        if returns_df.empty or len(returns_df.columns) < 2:
            raise ValueError("충분한 주가 데이터가 없습니다")
        
        # 통계 계산
        mean_returns = returns_df.mean().values
        cov_matrix = returns_df.cov().values
        
        # 최적화 실행
        if method == 'max_sharpe':
            result = self.max_sharpe_ratio(mean_returns, cov_matrix, constraints)
        elif method == 'min_variance':
            result = self.min_variance(mean_returns, cov_matrix, constraints)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # 결과 정리
        portfolio = {
            'method': method,
            'tickers': returns_df.columns.tolist(),
            'weights': dict(zip(returns_df.columns, result['weights'])),
            'expected_return': result['return'],
            'volatility': result['volatility'],
            'sharpe_ratio': result['sharpe_ratio'],
            'risk_free_rate': self.risk_free_rate,
            'lookback_days': lookback_days,
            'optimized_at': datetime.now().isoformat()
        }
        
        return portfolio
