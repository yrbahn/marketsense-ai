#!/usr/bin/env python3
"""네이버 금융 PER/PBR 크롤러

정확한 밸류에이션 지표 수집
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("marketsense")


class NaverPERCollector:
    """네이버 금융 PER/PBR 크롤러"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_valuation_metrics(self, ticker: str) -> Optional[Dict]:
        """PER, PBR, EPS, BPS 가져오기
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {'per': float, 'pbr': float, 'eps': int, 'bps': int, ...}
        """
        try:
            url = f"https://finance.naver.com/item/main.nhn?code={ticker}"
            
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {}
            
            # 종목명
            title = soup.select_one('div.wrap_company h2 a')
            if title:
                data['name'] = title.text.strip()
            
            # 현재가
            price_elem = soup.select_one('p.no_today em span.blind')
            if price_elem:
                try:
                    data['current_price'] = int(price_elem.text.replace(',', ''))
                except:
                    pass
            
            # 시가총액
            market_sum = soup.select_one('em#_market_sum')
            if market_sum:
                try:
                    # "1조 2,345억" 형태
                    mc_text = market_sum.text.strip()
                    data['market_cap_text'] = mc_text
                    
                    # 억원으로 변환
                    if '조' in mc_text:
                        parts = mc_text.replace('억', '').replace(',', '').split('조')
                        trillion = float(parts[0].strip())
                        billion = float(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 0
                        data['market_cap'] = (trillion * 10000 + billion) * 100000000
                    elif '억' in mc_text:
                        billion = float(mc_text.replace('억', '').replace(',', '').strip())
                        data['market_cap'] = billion * 100000000
                except Exception as e:
                    logger.debug(f"[{ticker}] 시가총액 파싱 오류: {e}")
            
            # 주요 투자지표 테이블
            # PER, PBR 등이 있는 테이블 (특정 패턴으로 찾기)
            all_tables = soup.select('table')
            
            for table in all_tables:
                table_text = table.text
                
                # PER, PBR이 포함된 테이블 찾기
                if 'PER' not in table_text or 'PBR' not in table_text:
                    continue
                
                rows = table.select('tr')
                for row in rows:
                    row_text = row.text
                    
                    # "PER(배)" 행 찾기
                    if 'PER' in row_text and '배' in row_text:
                        # PER 값 추출 (10.75배 같은 형식)
                        per_match = re.search(r'(\d+\.?\d*)배', row_text)
                        if per_match:
                            try:
                                data['per'] = float(per_match.group(1))
                            except:
                                pass
                        
                        # EPS 값 추출 (2,297원 같은 형식)
                        eps_match = re.search(r'([\d,]+)원', row_text)
                        if eps_match:
                            try:
                                data['eps'] = int(eps_match.group(1).replace(',', ''))
                            except:
                                pass
                    
                    # "PBR(배)" 행 찾기
                    if 'PBR' in row_text and '배' in row_text:
                        # PBR 값 추출
                        pbr_match = re.search(r'(\d+\.?\d*)배', row_text)
                        if pbr_match:
                            try:
                                data['pbr'] = float(pbr_match.group(1))
                            except:
                                pass
                        
                        # BPS 값 추출
                        bps_match = re.search(r'([\d,]+)원', row_text)
                        if bps_match:
                            try:
                                data['bps'] = int(bps_match.group(1).replace(',', ''))
                            except:
                                pass
            
            if data and any(k in data for k in ['per', 'pbr', 'eps']):
                logger.info(f"[{ticker}] 밸류에이션 지표 수집: {list(data.keys())}")
                return data
            else:
                logger.warning(f"[{ticker}] PER/PBR 데이터 파싱 실패")
                return None
                
        except Exception as e:
            logger.error(f"[{ticker}] 크롤링 오류: {e}")
            return None
    
    def collect_all_tickers(self, db, tickers: list):
        """여러 종목 PER/PBR 수집
        
        Args:
            db: 데이터베이스
            tickers: 종목 코드 리스트
        """
        logger.info(f"네이버 금융에서 {len(tickers)}개 종목 PER/PBR 수집 시작...")
        
        collected = 0
        
        with db.get_session() as session:
            from src.storage.models import Stock
            
            for i, ticker in enumerate(tickers):
                # 종목 조회
                stock = session.query(Stock).filter(Stock.ticker == ticker).first()
                
                if not stock:
                    continue
                
                # 데이터 수집
                data = self.get_valuation_metrics(ticker)
                
                if data:
                    # Stock 테이블 업데이트
                    if data.get('market_cap'):
                        stock.market_cap = data['market_cap']
                    
                    # 메타 데이터로 저장 (나중에 FundamentalsAgent에서 사용)
                    # raw_data JSON에 저장
                    if not stock.raw_data:
                        stock.raw_data = {}
                    
                    stock.raw_data['naver_valuation'] = {
                        'per': data.get('per'),
                        'pbr': data.get('pbr'),
                        'eps': data.get('eps'),
                        'bps': data.get('bps'),
                        'roe': data.get('roe'),
                        'current_price': data.get('current_price'),
                        'collected_at': str(datetime.now())
                    }
                    
                    collected += 1
                    
                    if collected % 10 == 0:
                        session.commit()
                        logger.info(f"진행: {i+1}/{len(tickers)} (수집: {collected})")
                
                # 너무 빠른 요청 방지
                if i % 10 == 0 and i > 0:
                    import time
                    time.sleep(1)
            
            session.commit()
        
        logger.info(f"✅ PER/PBR 수집 완료: {collected}/{len(tickers)}개")


def main():
    """테스트"""
    import sys
    from src.storage.database import init_db
    from src.utils.helpers import load_config
    
    collector = NaverPERCollector()
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        
        print(f"네이버 금융에서 {ticker} PER/PBR 수집...\n")
        data = collector.get_valuation_metrics(ticker)
        
        if data:
            print("수집된 데이터:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print("데이터 수집 실패")
    else:
        # 테스트 종목들
        test_tickers = ['005930', '123330', '000660']
        
        for ticker in test_tickers:
            print(f"\n{'='*60}")
            print(f"종목: {ticker}")
            print('='*60)
            
            data = collector.get_valuation_metrics(ticker)
            if data:
                for key, value in data.items():
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    from datetime import datetime
    main()
