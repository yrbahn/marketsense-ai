#!/usr/bin/env python3
"""준실시간 주가 모니터링

네이버 금융 크롤링으로 1초~10초 주기 실시간 모니터링
계좌 없이 사용 가능!
"""
import sys
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import json

from src.notifications.telegram_notifier import get_notifier

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("realtime")


class RealtimeMonitor:
    """준실시간 주가 모니터링"""
    
    def __init__(self, 
                 interval: int = 5,
                 price_threshold: float = 2.0,
                 volume_threshold: float = 1.5):
        """
        Args:
            interval: 체크 주기 (초)
            price_threshold: 급변동 기준 (%)
            volume_threshold: 거래량 급증 기준 (배수)
        """
        self.interval = interval
        self.price_threshold = price_threshold
        self.volume_threshold = volume_threshold
        self.notifier = get_notifier()
        self.last_prices = {}  # {ticker: (price, volume, timestamp)}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_realtime_price(self, ticker: str) -> Optional[Dict]:
        """네이버 금융에서 실시간 시세 가져오기
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {'price': float, 'change': float, 'volume': int, 'time': str}
        """
        try:
            # 네이버 금융 Polling API
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{ticker}"
            
            response = self.session.get(url, timeout=3)
            
            if response.status_code != 200:
                logger.warning(f"[{ticker}] 가격 조회 실패: {response.status_code}")
                return None
            
            data = response.json()
            
            # JSON 파싱
            if not data or 'result' not in data:
                return None
            
            result = data['result']
            if 'areas' not in result or not result['areas']:
                return None
            
            area = result['areas'][0]
            if 'datas' not in area or not area['datas']:
                return None
            
            item = area['datas'][0]
            
            return {
                'price': float(item.get('nv', 0)),  # 현재가
                'change': float(item.get('cv', 0)),  # 전일대비
                'change_rate': float(item.get('cr', 0)),  # 등락률
                'volume': int(item.get('aq', 0)),  # 거래량
                'time': datetime.now().strftime('%H:%M:%S')  # 현재 시간
            }
            
        except Exception as e:
            logger.error(f"[{ticker}] 실시간 가격 조회 오류: {e}")
            return None
    
    def check_price_change(self, ticker: str, name: str, 
                          current: Dict, last: Optional[Tuple]) -> bool:
        """가격 변동 체크 및 알림
        
        Args:
            ticker: 종목 코드
            name: 종목명
            current: 현재 데이터
            last: 이전 데이터 (price, volume, timestamp)
            
        Returns:
            알림 전송 여부
        """
        if not last:
            return False
        
        last_price, last_volume, last_time = last
        curr_price = current['price']
        curr_volume = current['volume']
        
        # 가격 변동률 계산 (이전 체크 대비)
        if last_price > 0:
            price_change = ((curr_price - last_price) / last_price) * 100
        else:
            return False
        
        # 거래량 비율 계산
        if last_volume > 0:
            volume_ratio = (curr_volume / last_volume) * 100
        else:
            volume_ratio = 100
        
        # 급변동 감지
        if abs(price_change) >= self.price_threshold:
            logger.warning(f"[{ticker}] 급변동: {price_change:+.2f}% ({last_time} → {current['time']})")
            
            # Telegram 알림
            self.notifier.send_price_alert(
                ticker=ticker,
                stock_name=name,
                change_pct=price_change,
                volume_ratio=volume_ratio
            )
            
            return True
        
        return False
    
    def monitor_stocks(self, watchlist: List[Tuple[str, str]]):
        """종목 모니터링 시작
        
        Args:
            watchlist: [(ticker, name), ...] 리스트
        """
        logger.info("=" * 60)
        logger.info("⚡ 준실시간 주가 모니터링 시작")
        logger.info(f"   체크 주기: {self.interval}초")
        logger.info(f"   급변동 기준: ±{self.price_threshold}%")
        logger.info(f"   감시 종목: {len(watchlist)}개")
        logger.info("=" * 60)
        
        # 시작 시간 기록
        start_time = datetime.now()
        check_count = 0
        alert_count = 0
        
        try:
            while True:
                check_count += 1
                logger.info(f"\n[{datetime.now().strftime('%H:%M:%S')}] 체크 #{check_count} 시작...")
                
                for ticker, name in watchlist:
                    try:
                        # 실시간 가격 조회
                        current = self.get_realtime_price(ticker)
                        
                        if not current:
                            continue
                        
                        # 가격 변동 체크
                        last = self.last_prices.get(ticker)
                        
                        if self.check_price_change(ticker, name, current, last):
                            alert_count += 1
                        
                        # 현재 가격 표시 (변동 있는 경우만)
                        if current['change_rate'] != 0:
                            logger.info(
                                f"  [{ticker}] {name}: "
                                f"{current['price']:,.0f}원 "
                                f"({current['change_rate']:+.2f}%) "
                                f"거래량 {current['volume']:,}"
                            )
                        
                        # 가격 업데이트
                        self.last_prices[ticker] = (
                            current['price'],
                            current['volume'],
                            current['time']
                        )
                        
                    except Exception as e:
                        logger.error(f"[{ticker}] 모니터링 오류: {e}")
                        continue
                
                # 통계 출력
                if check_count % 10 == 0:
                    elapsed = (datetime.now() - start_time).seconds
                    logger.info(
                        f"\n📊 통계: {elapsed}초 경과 | "
                        f"체크 {check_count}회 | "
                        f"알림 {alert_count}건"
                    )
                
                # 대기
                logger.info(f"다음 체크까지 {self.interval}초 대기...")
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            logger.info("\n\n⏹️  모니터링 중단")
            logger.info(f"총 체크: {check_count}회")
            logger.info(f"총 알림: {alert_count}건")
            sys.exit(0)


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='준실시간 주가 모니터링')
    parser.add_argument('--interval', type=int, default=5,
                       help='체크 주기 (초, 기본: 5)')
    parser.add_argument('--threshold', type=float, default=2.0,
                       help='급변동 기준 (%, 기본: 2.0)')
    parser.add_argument('--tickers', nargs='+',
                       help='감시할 종목 코드 (예: 005930 000660)')
    parser.add_argument('--top', type=int,
                       help='시총 상위 N개 감시')
    
    args = parser.parse_args()
    
    # 감시 종목 설정
    watchlist = []
    
    if args.tickers:
        # 직접 지정한 종목
        from src.storage.database import init_db
        from src.storage.models import Stock
        from src.utils.helpers import load_config
        
        db = init_db(load_config())
        
        with db.get_session() as session:
            for ticker in args.tickers:
                stock = session.query(Stock).filter_by(ticker=ticker).first()
                if stock:
                    watchlist.append((ticker, stock.name))
                else:
                    logger.warning(f"종목 {ticker} 없음")
    
    elif args.top:
        # 시총 상위 N개
        from src.storage.database import init_db
        from src.storage.models import Stock
        from src.utils.helpers import load_config
        
        db = init_db(load_config())
        
        with db.get_session() as session:
            stocks = session.query(Stock).filter(
                Stock.market_cap.isnot(None)
            ).order_by(Stock.market_cap.desc()).limit(args.top).all()
            
            watchlist = [(s.ticker, s.name) for s in stocks]
    
    else:
        # 기본: 주요 10개
        watchlist = [
            ('005930', '삼성전자'),
            ('000660', 'SK하이닉스'),
            ('005380', '현대차'),
            ('373220', 'LG에너지솔루션'),
            ('207940', '삼성바이오로직스'),
            ('005935', '삼성전자우'),
            ('051910', 'LG화학'),
            ('006400', '삼성SDI'),
            ('035420', 'NAVER'),
            ('000270', '기아')
        ]
    
    if not watchlist:
        logger.error("감시할 종목이 없습니다")
        sys.exit(1)
    
    # 모니터 시작
    monitor = RealtimeMonitor(
        interval=args.interval,
        price_threshold=args.threshold
    )
    
    monitor.monitor_stocks(watchlist)


if __name__ == "__main__":
    main()
