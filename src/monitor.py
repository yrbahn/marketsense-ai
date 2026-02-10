#!/usr/bin/env python3
"""실시간 주가 모니터링 및 급등/급락 알림

5분마다 주가를 체크하고 급등/급락 발생 시 Telegram 알림
"""
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

import FinanceDataReader as fdr

from src.storage.database import Database
from src.storage.models import Stock, PriceData
from src.notifications.telegram_notifier import get_notifier
from src.utils.helpers import load_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("marketsense")


class PriceMonitor:
    """주가 모니터링"""
    
    def __init__(self, db: Database, 
                 price_threshold: float = 5.0,
                 volume_threshold: float = 2.0):
        """
        Args:
            db: 데이터베이스
            price_threshold: 급등/급락 기준 (%)
            volume_threshold: 거래량 급증 기준 (배수)
        """
        self.db = db
        self.price_threshold = price_threshold
        self.volume_threshold = volume_threshold
        self.notifier = get_notifier()
        self.last_prices = {}  # {ticker: (price, volume)}
    
    def get_watchlist(self, limit: int = 100) -> List[Tuple[str, str]]:
        """모니터링 대상 종목 조회
        
        Args:
            limit: 조회할 종목 수
            
        Returns:
            [(ticker, name), ...] 리스트
        """
        with self.db.get_session() as session:
            stocks = session.query(Stock).filter(
                Stock.market_cap.isnot(None)
            ).order_by(Stock.market_cap.desc()).limit(limit).all()
            
            return [(s.ticker, s.name) for s in stocks]
    
    def get_current_price(self, ticker: str) -> Optional[Tuple[float, float]]:
        """현재 주가 조회
        
        Args:
            ticker: 종목 코드
            
        Returns:
            (price, volume) 또는 None
        """
        try:
            # 실시간 데이터 조회 (최근 1일)
            df = fdr.DataReader(ticker, datetime.now() - timedelta(days=1))
            
            if df.empty:
                return None
            
            last = df.iloc[-1]
            price = float(last['Close'])
            volume = float(last['Volume'])
            
            return (price, volume)
            
        except Exception as e:
            logger.error(f"[{ticker}] 가격 조회 실패: {e}")
            return None
    
    def get_average_volume(self, ticker: str, days: int = 20) -> Optional[float]:
        """평균 거래량 조회
        
        Args:
            ticker: 종목 코드
            days: 평균 기간
            
        Returns:
            평균 거래량 또는 None
        """
        with self.db.get_session() as session:
            # 최근 N일 거래량
            cutoff = datetime.now() - timedelta(days=days)
            
            records = session.query(PriceData).join(Stock).filter(
                Stock.ticker == ticker,
                PriceData.date >= cutoff.date()
            ).all()
            
            if not records:
                return None
            
            volumes = [r.volume for r in records if r.volume]
            
            if not volumes:
                return None
            
            return sum(volumes) / len(volumes)
    
    def check_price_change(self, ticker: str, name: str) -> bool:
        """급등/급락 체크
        
        Args:
            ticker: 종목 코드
            name: 종목명
            
        Returns:
            알림 전송 여부
        """
        # 현재 가격
        current = self.get_current_price(ticker)
        if not current:
            return False
        
        curr_price, curr_volume = current
        
        # 이전 가격
        if ticker not in self.last_prices:
            self.last_prices[ticker] = (curr_price, curr_volume)
            return False
        
        last_price, last_volume = self.last_prices[ticker]
        
        # 가격 변동률 계산
        price_change = ((curr_price - last_price) / last_price) * 100
        
        # 거래량 비율 계산
        avg_volume = self.get_average_volume(ticker)
        if avg_volume and avg_volume > 0:
            volume_ratio = (curr_volume / avg_volume) * 100
        else:
            volume_ratio = 100
        
        # 급등/급락 감지
        if abs(price_change) >= self.price_threshold:
            logger.info(f"[{ticker}] 급변동 감지: {price_change:+.1f}%")
            
            # Telegram 알림
            self.notifier.send_price_alert(
                ticker=ticker,
                stock_name=name,
                change_pct=price_change,
                volume_ratio=volume_ratio
            )
            
            # 가격 업데이트
            self.last_prices[ticker] = (curr_price, curr_volume)
            
            return True
        
        # 가격 업데이트 (변동 없어도)
        self.last_prices[ticker] = (curr_price, curr_volume)
        
        return False
    
    def run(self, interval: int = 300):
        """모니터링 실행
        
        Args:
            interval: 체크 주기 (초)
        """
        logger.info("=" * 60)
        logger.info("🔍 실시간 주가 모니터링 시작")
        logger.info(f"   체크 주기: {interval}초")
        logger.info(f"   급등/급락 기준: ±{self.price_threshold}%")
        logger.info("=" * 60)
        
        # 감시 종목
        watchlist = self.get_watchlist(limit=100)
        logger.info(f"감시 종목: {len(watchlist)}개")
        
        try:
            while True:
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 체크 시작...")
                
                alert_count = 0
                
                for ticker, name in watchlist:
                    try:
                        if self.check_price_change(ticker, name):
                            alert_count += 1
                    except Exception as e:
                        logger.error(f"[{ticker}] 체크 오류: {e}")
                        continue
                
                if alert_count > 0:
                    logger.info(f"✅ 알림 {alert_count}건 전송")
                else:
                    logger.info("📊 변동 없음")
                
                # 대기
                logger.info(f"다음 체크까지 {interval}초 대기...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n모니터링 중단")
            sys.exit(0)


def main():
    """메인 실행"""
    config = load_config()
    db = Database(config)
    
    # 모니터 생성
    monitor = PriceMonitor(
        db=db,
        price_threshold=5.0,  # ±5% 급등/급락
        volume_threshold=2.0   # 거래량 2배 이상
    )
    
    # 실행 (5분 주기)
    monitor.run(interval=300)


if __name__ == "__main__":
    main()
