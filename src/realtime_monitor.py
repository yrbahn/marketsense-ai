#!/usr/bin/env python3
"""준실시간 주가 모니터링

한국투자증권 API로 실시간 시세 모니터링
공식 API 사용으로 안정성 향상!
"""
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import json

from src.notifications.telegram_notifier import get_notifier
from src.utils.kis_api import KISApi

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
        self.kis_api = KISApi()  # KIS API 클라이언트
        logger.info("[모니터] KIS API 초기화 완료")
    
    def get_realtime_price(self, ticker: str) -> Optional[Dict]:
        """KIS API에서 실시간 시세 가져오기
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {'price': int, 'change': int, 'change_pct': float, 'volume': int, 'time': str}
        """
        try:
            # KIS API로 현재가 조회
            data = self.kis_api.get_current_price(ticker)
            
            if not data:
                return None
            
            return {
                'price': data['price'],  # 현재가
                'change': data['change'],  # 전일대비
                'change_rate': data['change_pct'],  # 등락률
                'volume': data['volume'],  # 누적 거래량
                'time': data.get('time', datetime.now().strftime('%H%M%S'))  # 시간
            }
            
        except Exception as e:
            logger.debug(f"[{ticker}] 실시간 가격 조회 오류: {e}")
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
                cycle_start = time.time()
                logger.info(f"\n[{datetime.now().strftime('%H:%M:%S')}] 체크 #{check_count} 시작...")
                
                # 배치 처리: 초당 20건 제한 준수
                for idx, (ticker, name) in enumerate(watchlist):
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
                        
                        # API 호출 제한 준수: 50ms 간격 (초당 20건)
                        # 마지막 종목은 대기 안 함
                        if idx < len(watchlist) - 1:
                            time.sleep(0.05)
                        
                    except Exception as e:
                        logger.error(f"[{ticker}] 모니터링 오류: {e}")
                        continue
                
                # 사이클 소요 시간 계산
                cycle_elapsed = time.time() - cycle_start
                
                # 통계 출력
                if check_count % 10 == 0:
                    elapsed = (datetime.now() - start_time).seconds
                    logger.info(
                        f"\n📊 통계: {elapsed}초 경과 | "
                        f"체크 {check_count}회 | "
                        f"알림 {alert_count}건 | "
                        f"사이클: {cycle_elapsed:.1f}초"
                    )
                
                # interval까지 남은 시간 대기
                remaining = self.interval - cycle_elapsed
                if remaining > 0:
                    logger.info(f"다음 체크까지 {remaining:.1f}초 대기...")
                    time.sleep(remaining)
                else:
                    logger.warning(f"사이클 시간 초과: {cycle_elapsed:.1f}초 (목표: {self.interval}초)")
                
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
