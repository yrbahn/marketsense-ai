#!/usr/bin/env python3
"""네이버 금융 재무 데이터 수집기

빠른 재무 지표 수집 (P/E, P/B, ROE 등)
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from datetime import datetime

from src.storage.models import Stock, FinancialStatement

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("marketsense")


class NaverFinanceCollector:
    """네이버 금융 크롤러"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_financial_summary(self, ticker: str) -> Optional[Dict]:
        """종목 재무 요약 가져오기 (FinanceDataReader 사용)
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {'per': float, 'pbr': float, 'market_cap': float, ...}
        """
        try:
            import FinanceDataReader as fdr
            
            # 종목 기본 정보
            kospi = fdr.StockListing('KOSPI')
            kosdaq = fdr.StockListing('KOSDAQ')
            
            stock_info = None
            
            # KOSPI에서 찾기
            stock_data = kospi[kospi['Code'] == ticker]
            if not stock_data.empty:
                stock_info = stock_data.iloc[0]
            else:
                # KOSDAQ에서 찾기
                stock_data = kosdaq[kosdaq['Code'] == ticker]
                if not stock_data.empty:
                    stock_info = stock_data.iloc[0]
            
            if stock_info is None:
                logger.warning(f"[{ticker}] 종목 정보 없음")
                return None
            
            data = {}
            
            # 시가총액
            if 'Marcap' in stock_info:
                data['market_cap'] = float(stock_info['Marcap'])
            
            # 현재가 (필요시)
            if 'Close' in stock_info:
                data['current_price'] = float(stock_info['Close'])
            
            # PER, PBR 등은 네이버 금융 API로 추가 조회
            # 간단한 JSON API 사용
            try:
                api_url = f"https://api.finance.naver.com/service/itemSummary.nhn?itemcode={ticker}"
                response = self.session.get(api_url, timeout=3)
                
                if response.status_code == 200:
                    # XML 또는 JSON 파싱
                    from xml.etree import ElementTree as ET
                    root = ET.fromstring(response.content)
                    
                    # PER, PBR 등 추출
                    for child in root:
                        tag = child.tag.lower()
                        value = child.text
                        
                        if value and value != 'N/A':
                            try:
                                if tag == 'per':
                                    data['per'] = float(value)
                                elif tag == 'pbr':
                                    data['pbr'] = float(value)
                                elif tag == 'roe':
                                    data['roe'] = float(value)
                                elif tag == 'eps':
                                    data['eps'] = float(value)
                            except:
                                pass
            except:
                pass
            
            if data:
                logger.info(f"[{ticker}] FDR 데이터 수집: {list(data.keys())}")
                return data
            else:
                logger.warning(f"[{ticker}] 데이터 없음")
                return None
                
        except Exception as e:
            logger.error(f"[{ticker}] 수집 오류: {e}")
            return None
    
    def collect_all_tickers(self, db, tickers: list):
        """여러 종목 재무 데이터 수집
        
        Args:
            db: 데이터베이스
            tickers: 종목 코드 리스트
        """
        logger.info(f"네이버 금융에서 {len(tickers)}개 종목 수집 시작...")
        
        collected = 0
        
        with db.get_session() as session:
            for i, ticker in enumerate(tickers):
                # 종목 조회
                stock = session.query(Stock).filter(Stock.ticker == ticker).first()
                
                if not stock:
                    continue
                
                # 데이터 수집
                data = self.get_financial_summary(ticker)
                
                if data:
                    # 시가총액 업데이트
                    if data.get('market_cap'):
                        stock.market_cap = data['market_cap']
                    
                    # 간단한 재무 레코드 생성 (현재 시점)
                    # 실제로는 분기별 데이터가 아니지만 스냅샷으로 저장
                    stmt = FinancialStatement(
                        stock_id=stock.id,
                        statement_type='naver_snapshot',
                        period_type='current',
                        period_end=datetime.now().date(),
                        fiscal_quarter='현재',
                        raw_data=data,
                        eps=data.get('eps'),
                        collected_at=datetime.now(),
                        source='naver_finance'
                    )
                    
                    session.add(stmt)
                    collected += 1
                    
                    if collected % 10 == 0:
                        session.commit()
                        logger.info(f"진행: {i+1}/{len(tickers)} (수집: {collected})")
                
                # 너무 빠른 요청 방지
                if i % 10 == 0 and i > 0:
                    import time
                    time.sleep(1)
            
            session.commit()
        
        logger.info(f"✅ 네이버 금융 수집 완료: {collected}/{len(tickers)}개")


def main():
    """테스트"""
    import sys
    from src.storage.database import init_db
    from src.utils.helpers import load_config
    
    collector = NaverFinanceCollector()
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        
        print(f"네이버 금융에서 {ticker} 데이터 수집...")
        data = collector.get_financial_summary(ticker)
        
        if data:
            print("\n수집된 데이터:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print("데이터 수집 실패")
    else:
        # 전체 종목 수집
        config = load_config()
        db = init_db(config)
        
        with db.get_session() as session:
            stocks = session.query(Stock).limit(100).all()
            tickers = [s.ticker for s in stocks]
        
        collector.collect_all_tickers(db, tickers)


if __name__ == "__main__":
    main()
