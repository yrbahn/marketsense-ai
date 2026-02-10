"""수급 데이터 수집기

거래량, 외국인 보유율, 투자자별 매매 등 수급 지표 수집

데이터 소스:
- 거래량: 네이버 증권 API
- 외국인 보유율: 네이버 증권 API
- 투자자별 매매: 한국투자증권 OpenAPI (개인/외국인/기관 순매수)

TODO:
- 공매도: KIS API 미제공
- 신용잔고: KIS API 미제공
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

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
                        # 1. 거래량 및 외국인 보유율 (네이버)
                        naver_count = self._collect_naver_data(session, ticker)
                        
                        # 2. 투자자별 매매 (KIS API)
                        kis_count = self._collect_kis_investor_trading(session, ticker)
                        
                        total += (naver_count + kis_count)
                        
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
    
    def _collect_kis_investor_trading(self, session, ticker: str) -> int:
        """투자자별 매매 (한국투자증권 OpenAPI)"""
        count = 0
        
        try:
            from src.utils.kis_api import KISApi
            
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 0
            
            # KIS API 초기화
            try:
                api = KISApi()
            except ValueError:
                # API 키가 없으면 skip
                return 0
            
            # 최근 lookback_days 동안의 투자자별 매매
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            # KIS API로 투자자별 매매 조회
            data_list = api.get_investor_trading(
                ticker,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            if not data_list:
                return 0
            
            for item in data_list:
                date_str = item.get('stck_bsop_date')
                if not date_str:
                    continue
                
                try:
                    trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                except:
                    continue
                
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
                
                # 투자자별 순매수 저장
                # prsn_ntby_qty: 개인 순매수 수량
                # frgn_ntby_qty: 외국인 순매수 수량
                # orgn_ntby_qty: 기관 순매수 수량
                
                if 'prsn_ntby_qty' in item:
                    supply_demand.individual_net_buy = float(item.get('prsn_ntby_qty', 0))
                
                if 'frgn_ntby_qty' in item:
                    supply_demand.foreign_net_buy = float(item.get('frgn_ntby_qty', 0))
                
                if 'orgn_ntby_qty' in item:
                    supply_demand.institution_net_buy = float(item.get('orgn_ntby_qty', 0))
                
                count += 1
            
            session.flush()
            
        except Exception as e:
            logger.debug(f"[KIS] {ticker} 투자자 매매 수집 실패: {e}")
        
        return count

    def _collect_naver_data(self, session, ticker: str) -> int:
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
