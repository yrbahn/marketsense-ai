#!/usr/bin/env python3
"""일일 시장 리포트 생성 및 Telegram 전송

매일 오후 4시 실행:
- 상위 종목 AI 분석
- 투자 신호 생성
- Telegram으로 리포트 전송
"""
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from src.storage.database import init_db
from src.storage.models import Stock, PriceData
from src.agents.signal_agent import SignalAgent
from src.notifications.telegram_notifier import get_notifier
from src.utils.helpers import load_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("marketsense")


def get_top_stocks(db, limit: int = 50) -> List[Tuple[str, str]]:
    """시총 상위 종목 조회
    
    Args:
        db: 데이터베이스
        limit: 조회할 종목 수
        
    Returns:
        [(ticker, name), ...] 리스트
    """
    with db.get_session() as session:
        stocks = session.query(Stock).filter(
            Stock.market_cap.isnot(None)
        ).order_by(Stock.market_cap.desc()).limit(limit).all()
        
        return [(s.ticker, s.name) for s in stocks]


def get_market_summary(db) -> dict:
    """시장 현황 조회
    
    Args:
        db: 데이터베이스
        
    Returns:
        {'kospi': ..., 'kosdaq': ...}
    """
    # 실제로는 지수 데이터를 수집해야 하지만, 임시로 더미 데이터
    return {
        "kospi": "상승세",
        "kosdaq": "보합세"
    }


def analyze_and_rank(db, stocks: List[Tuple[str, str]], 
                    top_n: int = 10) -> List[Tuple[str, str, str, float]]:
    """종목 분석 및 순위화
    
    Args:
        db: 데이터베이스
        stocks: 분석할 종목 리스트
        top_n: 상위 몇 개 반환
        
    Returns:
        [(ticker, name, signal, confidence), ...] 리스트
    """
    config = load_config()
    signal_agent = SignalAgent(config)
    
    results = []
    
    for ticker, name in stocks:
        try:
            logger.info(f"[{ticker}] {name} 분석 중...")
            
            # AI 분석 실행
            analysis = signal_agent.analyze(ticker, db)
            
            if analysis:
                signal = analysis.get("signal", "HOLD")
                confidence = analysis.get("confidence", 0.0)
                
                # BUY 신호이고 신뢰도가 높은 것만
                if signal == "BUY" and confidence >= 0.7:
                    results.append((ticker, name, signal, confidence))
                    logger.info(f"[{ticker}] {signal} ({confidence*100:.0f}%)")
            
        except Exception as e:
            logger.error(f"[{ticker}] 분석 실패: {e}")
            continue
    
    # 신뢰도 순으로 정렬
    results.sort(key=lambda x: x[3], reverse=True)
    
    return results[:top_n]


def main():
    """메인 실행"""
    logger.info("=" * 60)
    logger.info("📊 일일 시장 리포트 생성")
    logger.info("=" * 60)
    
    # 설정 로드
    config = load_config()
    db = init_db(config)
    
    # 상위 종목 조회
    logger.info("시총 상위 50개 종목 조회...")
    stocks = get_top_stocks(db, limit=50)
    logger.info(f"종목 {len(stocks)}개 조회 완료")
    
    # AI 분석 및 순위화
    logger.info("AI 분석 시작...")
    top_signals = analyze_and_rank(db, stocks, top_n=10)
    logger.info(f"상위 신호 {len(top_signals)}개 추출")
    
    if not top_signals:
        logger.warning("매수 신호 없음")
        return
    
    # 시장 요약
    market_summary = get_market_summary(db)
    
    # Telegram 전송
    logger.info("Telegram 리포트 전송...")
    notifier = get_notifier()
    
    success = notifier.send_daily_report(top_signals, market_summary)
    
    if success:
        logger.info("✅ 리포트 전송 완료")
        
        # 개별 신호 알림 (상위 3개만)
        for ticker, name, signal, conf in top_signals[:3]:
            logger.info(f"[{ticker}] 신호 알림 전송...")
            # 여기서 더 상세한 분석 결과를 가져와서 전송 가능
            notifier.send_signal_alert(
                ticker=ticker,
                stock_name=name,
                signal=signal,
                confidence=conf,
                reasons={}  # 실제로는 상세 분석 결과 전달
            )
    else:
        logger.error("❌ 리포트 전송 실패")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎉 일일 리포트 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
