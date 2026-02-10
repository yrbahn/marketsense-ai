"""수급 데이터 수집기

공매도, 신용잔고, 투자자별 매매 등 수급 지표 수집

데이터 소스:
- 공매도: pykrx (KRX)
- 신용잔고: pykrx (KRX)
- 투자자별 매매: 네이버 증권 API
- 외국인 보유율: 네이버 증권 API
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

import FinanceDataReader as fdr
from pykrx import stock as pykrx_stock

from .base_collector import BaseCollector
from src.storage.database import Database
from src.storage.models import Stock, SupplyDemandData

logger = logging.getLogger("marketsense")


class SupplyDemandCollector(BaseCollector):
    """수급 지표 수집기"""

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.lookback_days = config.get("supply_demand", {}).get("lookback_days", 30)

    def collect(self, tickers: list = None, **kwargs):
        """수급 데이터 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            
            try:
                if not tickers:
                    # 활성 종목만 (한국 종목: 6자리 숫자)
                    stocks = session.query(Stock).filter_by(is_active=True).all()
                    tickers = [s.ticker for s in stocks if s.ticker.isdigit() and len(s.ticker) == 6]
                
                logger.info(f"[SupplyDemand] {len(tickers)}개 종목 수집 시작")
                
                for idx, ticker in enumerate(tickers):
                    if idx % 100 == 0 and idx > 0:
                        logger.info(f"[SupplyDemand] 진행: {idx}/{len(tickers)} ({total}건)")
                    
                    try:
                        # 거래량 및 외국인 보유율 (네이버)
                        investor_count = self._collect_investor_trading(session, ticker)
                        
                        # 공매도 데이터 (pykrx)
                        short_count = self._collect_short_selling(session, ticker)
                        
                        # 신용잔고 데이터 (pykrx)
                        margin_count = self._collect_margin_trading(session, ticker)
                        
                        total += (investor_count + short_count + margin_count)
                        
                        # Rate limit
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.debug(f"[SupplyDemand] {ticker} 실패: {e}")
                        continue
                
                self._finish_run(run, total)
                logger.info(f"[SupplyDemand] 완료: {total}건 수집")
                
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise
    
    def _collect_short_selling(self, session, ticker: str) -> int:
        """공매도 데이터 수집 (pykrx KRX)"""
        count = 0
        
        try:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 0
            
            # 최근 lookback_days 동안의 공매도 데이터
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            # pykrx로 공매도 현황 조회
            # get_shorting_status_by_ticker(fromdate, todate, ticker)
            df = pykrx_stock.get_shorting_status_by_ticker(
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d'),
                ticker
            )
            
            if df is None or df.empty:
                return 0
            
            # DataFrame 인덱스가 날짜
            for date_idx, row in df.iterrows():
                trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                
                # 기존 레코드 조회 또는 생성
                supply_demand = session.query(SupplyDemandData).filter_by(
                    stock_id=stock.id,
                    date=trade_date
                ).first()
                
                if not supply_demand:
                    supply_demand = SupplyDemandData(
                        stock_id=stock.id,
                        date=trade_date
                    )
                    session.add(supply_demand)
                
                # 공매도 데이터 저장
                # pykrx 컬럼: 거래량, 거래대금, 공매도거래량, 공매도거래대금, 공매도잔고, etc.
                if '공매도거래량' in row:
                    supply_demand.short_selling_volume = row.get('공매도거래량')
                
                if '공매도잔고' in row:
                    supply_demand.short_selling_balance = row.get('공매도잔고')
                
                count += 1
            
            session.flush()
            
        except Exception as e:
            logger.debug(f"[SHORT] {ticker} 실패: {e}")
        
        return count
    
    def _collect_margin_trading(self, session, ticker: str) -> int:
        """신용잔고 데이터 수집 (pykrx KRX)"""
        count = 0
        
        try:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 0
            
            # 최근 lookback_days 동안의 신용잔고 데이터
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            # pykrx로 신용잔고 조회
            # get_market_margin_trading_volume_by_ticker(fromdate, todate, ticker)
            df = pykrx_stock.get_market_margin_trading_volume_by_ticker(
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d'),
                ticker
            )
            
            if df is None or df.empty:
                return 0
            
            # DataFrame 인덱스가 날짜
            for date_idx, row in df.iterrows():
                trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                
                # 기존 레코드 조회 또는 생성
                supply_demand = session.query(SupplyDemandData).filter_by(
                    stock_id=stock.id,
                    date=trade_date
                ).first()
                
                if not supply_demand:
                    supply_demand = SupplyDemandData(
                        stock_id=stock.id,
                        date=trade_date
                    )
                    session.add(supply_demand)
                
                # 신용잔고 데이터 저장
                # pykrx 컬럼: 융자, 대주, 융자잔고, 대주잔고, etc.
                if '융자매수' in row:
                    supply_demand.credit_buy_balance = row.get('융자매수')
                
                if '대주매도' in row:
                    supply_demand.credit_sell_balance = row.get('대주매도')
                
                if '융자잔고' in row:
                    supply_demand.margin_balance = row.get('융자잔고')
                
                # 신용잔고율 계산 (융자잔고 / 상장주식수 * 100)
                # 상장주식수가 필요하지만 일단 보류
                
                count += 1
            
            session.flush()
            
        except Exception as e:
            logger.debug(f"[MARGIN] {ticker} 실패: {e}")
        
        return count
    
    def _collect_investor_trading(self, session, ticker: str) -> int:
        """거래량 및 외국인 보유비중 (네이버 증권 API)"""
        count = 0
        
        try:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 0
            
            # 네이버 증권 API (최근 30일 데이터)
            url = f"https://api.stock.naver.com/chart/domestic/item/{ticker}/day"
            headers = {"User-Agent": "Mozilla/5.0"}
            params = {"count": self.lookback_days}
            
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code != 200:
                return 0
            
            data = resp.json()
            
            # 단일 데이터 또는 리스트
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else []
            
            for item in data:
                date_str = item.get('localDate')
                if not date_str:
                    continue
                
                try:
                    # YYYYMMDD 형식
                    trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                except:
                    continue
                
                # 중복 체크
                supply_demand = session.query(SupplyDemandData).filter_by(
                    stock_id=stock.id,
                    date=trade_date
                ).first()
                
                if not supply_demand:
                    supply_demand = SupplyDemandData(
                        stock_id=stock.id,
                        date=trade_date
                    )
                    session.add(supply_demand)
                
                # 거래량
                supply_demand.volume = item.get('accumulatedTradingVolume')
                
                # 외국인 보유비중
                supply_demand.foreign_ownership = item.get('foreignRetentionRate')
                
                count += 1
            
            session.flush()
            
        except Exception as e:
            logger.debug(f"[INVESTOR] {ticker} 실패: {e}")
        
        return count
