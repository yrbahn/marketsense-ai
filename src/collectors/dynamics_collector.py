"""주가/기술적 지표 수집기

MarketSenseAI Dynamics Agent에 필요한 데이터:
- 일별 OHLCV 주가 데이터
- 기술적 지표 (SMA, RSI, MACD, BB, ATR)
- 리스크 지표 (변동성, 샤프, MDD)
- 벤치마크 대비 비교 데이터

논문 Section 3.1 (Dynamics Agent):
"Examines historical price movements and contextualizes them against
industry peers and the broader market (i.e., S&P 500). By incorporating
risk metrics like volatility, Sharpe Ratio, and maximum drawdown."
"""
import logging
import time
import numpy as np
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

from .base_collector import BaseCollector
from src.storage.database import Database
from src.storage.models import Stock, PriceData, TechnicalIndicator

logger = logging.getLogger("marketsense")


class DynamicsCollector(BaseCollector):
    """주가 & 기술적 지표 수집기"""

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.dyn_config = config.get("dynamics", {})
        self.lookback_days = self.dyn_config.get("lookback_days", 365)
        self.benchmark = self.dyn_config.get("benchmark", "^GSPC")

    def _is_korean_stock(self, ticker: str) -> bool:
        """한국 종목 여부 확인"""
        # 숫자 6자리면 한국 종목
        return ticker.isdigit() and len(ticker) == 6

    def collect(self, tickers: list = None, **kwargs):
        """주가 + 기술적 지표 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            try:
                if not tickers:
                    tickers = [s.ticker for s in session.query(Stock).filter_by(is_active=True).all()]

                # 벤치마크도 수집
                all_tickers = tickers + [self.benchmark]

                for ticker in all_tickers:
                    stock = session.query(Stock).filter_by(ticker=ticker).first()
                    if not stock and ticker != self.benchmark:
                        continue

                    stock_id = stock.id if stock else None
                    count = self._collect_price_and_indicators(session, ticker, stock_id)
                    total += count
                    time.sleep(0.3)

                self._finish_run(run, total)
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise

    def _collect_price_and_indicators(self, session, ticker: str, stock_id: Optional[int]) -> int:
        """개별 종목 주가 + 지표 수집"""
        count = 0
        try:
            end = datetime.now()
            # 기술적 지표 계산을 위해 추가 기간 포함
            start = end - timedelta(days=self.lookback_days + 250)

            # 한국 종목은 FinanceDataReader, 벤치마크는 yfinance
            if self._is_korean_stock(ticker):
                df = fdr.DataReader(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            else:
                # 벤치마크 (^KS11 등)는 yfinance 사용
                yf_ticker = yf.Ticker(ticker)
                df = yf_ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

            if df.empty:
                logger.warning(f"[{ticker}] 가격 데이터 없음")
                return 0

            df.index = pd.to_datetime(df.index)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            # 기술적 지표 계산
            df = self._calculate_indicators(df)

            # 최근 lookback_days만 저장
            cutoff = end - timedelta(days=self.lookback_days)
            save_df = df[df.index >= cutoff]

            for idx, row in save_df.iterrows():
                row_date = idx.date()

                if stock_id:
                    # 주가 데이터 저장
                    exists = session.query(PriceData).filter_by(
                        stock_id=stock_id, date=row_date
                    ).first()
                    if not exists:
                        price = PriceData(
                            stock_id=stock_id,
                            date=row_date,
                            open=row.get("Open"),
                            high=row.get("High"),
                            low=row.get("Low"),
                            close=row.get("Close"),
                            volume=row.get("Volume"),
                            dividend=row.get("Dividends", 0),
                            stock_split=row.get("Stock Splits", 0),
                        )
                        session.add(price)
                        count += 1

                    # 기술적 지표 저장
                    exists_ti = session.query(TechnicalIndicator).filter_by(
                        stock_id=stock_id, date=row_date
                    ).first()
                    if not exists_ti:
                        ti = TechnicalIndicator(
                            stock_id=stock_id,
                            date=row_date,
                            sma_20=row.get("sma_20"),
                            sma_50=row.get("sma_50"),
                            sma_200=row.get("sma_200"),
                            rsi_14=row.get("rsi_14"),
                            macd=row.get("macd"),
                            macd_signal=row.get("macd_signal"),
                            macd_hist=row.get("macd_hist"),
                            bb_upper=row.get("bb_upper"),
                            bb_middle=row.get("bb_middle"),
                            bb_lower=row.get("bb_lower"),
                            atr_14=row.get("atr_14"),
                            volume_sma_20=row.get("volume_sma_20"),
                            daily_return=row.get("daily_return"),
                            volatility_20d=row.get("volatility_20d"),
                            sharpe_ratio_20d=row.get("sharpe_20d"),
                            max_drawdown_20d=row.get("mdd_20d"),
                        )
                        session.add(ti)
                        count += 1

            logger.debug(f"[{ticker}] 가격+지표 {count}건")

        except Exception as e:
            logger.error(f"[{ticker}] Dynamics 수집 실패: {e}")

        return count

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # SMA
        df["sma_20"] = close.rolling(20).mean()
        df["sma_50"] = close.rolling(50).mean()
        df["sma_200"] = close.rolling(200).mean()

        # RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands (20, 2)
        df["bb_middle"] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std

        # ATR (14)
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(14).mean()

        # Volume SMA
        df["volume_sma_20"] = volume.rolling(20).mean()

        # 수익률 & 리스크
        df["daily_return"] = close.pct_change()
        df["volatility_20d"] = df["daily_return"].rolling(20).std() * np.sqrt(252)

        # 20일 샤프 비율 (연환산)
        rolling_mean = df["daily_return"].rolling(20).mean() * 252
        rolling_std = df["daily_return"].rolling(20).std() * np.sqrt(252)
        df["sharpe_20d"] = rolling_mean / rolling_std.replace(0, np.nan)

        # 20일 MDD
        df["mdd_20d"] = df.apply(
            lambda row: self._calc_mdd(close[:row.name].tail(20)), axis=1
        ) if len(df) > 20 else np.nan

        return df

    @staticmethod
    def _calc_mdd(series: pd.Series) -> float:
        """Maximum Drawdown 계산"""
        if len(series) < 2:
            return 0.0
        cummax = series.cummax()
        drawdown = (series - cummax) / cummax
        return drawdown.min()
