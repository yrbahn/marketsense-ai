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
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from dotenv import load_dotenv

# .env 파일 로드 (최우선)
load_dotenv()

from src.storage.database import init_db
from src.storage.models import Stock, PriceData
from src.agents.signal_agent import SignalAgent
from src.agents.macro_agent import MacroAgent
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
    """시장 현황 조회 (실시간)
    
    Args:
        db: 데이터베이스
        
    Returns:
        {'kospi': ..., 'kosdaq': ...}
    """
    import yfinance as yf
    
    summary = {}
    
    try:
        # 코스피 지수
        kospi = yf.Ticker('^KS11')
        kospi_data = kospi.history(period='2d')
        
        if len(kospi_data) >= 2:
            today_close = kospi_data.iloc[-1]['Close']
            yesterday_close = kospi_data.iloc[-2]['Close']
            change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
            
            if change_pct > 0.5:
                trend = f"상승세 (+{change_pct:.2f}%)"
            elif change_pct < -0.5:
                trend = f"하락세 ({change_pct:.2f}%)"
            else:
                trend = f"보합세 ({change_pct:+.2f}%)"
            
            summary['kospi'] = trend
            summary['kospi_value'] = f"{today_close:,.2f}"
            summary['kospi_change'] = f"{change_pct:+.2f}%"
        else:
            summary['kospi'] = "데이터 없음"
    except Exception as e:
        logger.error(f"코스피 지수 조회 실패: {e}")
        summary['kospi'] = "조회 실패"
    
    try:
        # 코스닥 지수
        kosdaq = yf.Ticker('^KQ11')
        kosdaq_data = kosdaq.history(period='2d')
        
        if len(kosdaq_data) >= 2:
            today_close = kosdaq_data.iloc[-1]['Close']
            yesterday_close = kosdaq_data.iloc[-2]['Close']
            change_pct = ((today_close - yesterday_close) / yesterday_close) * 100
            
            if change_pct > 0.5:
                trend = f"상승세 (+{change_pct:.2f}%)"
            elif change_pct < -0.5:
                trend = f"하락세 ({change_pct:.2f}%)"
            else:
                trend = f"보합세 ({change_pct:+.2f}%)"
            
            summary['kosdaq'] = trend
            summary['kosdaq_value'] = f"{today_close:,.2f}"
            summary['kosdaq_change'] = f"{change_pct:+.2f}%"
        else:
            summary['kosdaq'] = "데이터 없음"
    except Exception as e:
        logger.error(f"코스닥 지수 조회 실패: {e}")
        summary['kosdaq'] = "조회 실패"
    
    return summary


def analyze_single_stock(args: Tuple[str, str]) -> Optional[Tuple[str, str, str, float]]:
    """단일 종목 분석 (병렬 처리용 워커)
    
    Args:
        args: (ticker, name) 튜플
        
    Returns:
        (ticker, name, signal, confidence) 또는 None
    """
    ticker, name = args
    
    try:
        # 각 프로세스에서 별도로 초기화
        config = load_config()
        db = init_db(config)
        signal_agent = SignalAgent(config, db)
        
        # AI 분석 실행
        analysis = signal_agent.analyze(ticker)
        
        if analysis:
            signal = analysis.get("signal", "HOLD")
            confidence = analysis.get("confidence", 0.0)
            
            # BUY 신호이고 신뢰도가 높은 것만
            if signal == "BUY" and confidence >= 0.7:
                return (ticker, name, signal, confidence)
        
        return None
        
    except Exception as e:
        logger.error(f"[{ticker}] 분석 실패: {e}")
        return None


def analyze_and_rank(db, stocks: List[Tuple[str, str]], 
                    top_n: int = 10, 
                    max_workers: int = None) -> List[Tuple[str, str, str, float]]:
    """종목 분석 및 순위화 (병렬 처리)
    
    Args:
        db: 데이터베이스
        stocks: 분석할 종목 리스트
        top_n: 상위 몇 개 반환
        max_workers: 병렬 프로세스 수 (None = CPU 코어 수)
        
    Returns:
        [(ticker, name, signal, confidence), ...] 리스트
    """
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    logger.info(f"병렬 처리 시작: {len(stocks)}개 종목, {max_workers}개 프로세스")
    
    results = []
    completed = 0
    
    # ProcessPoolExecutor로 병렬 처리
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 모든 종목 제출
        future_to_stock = {
            executor.submit(analyze_single_stock, (ticker, name)): (ticker, name)
            for ticker, name in stocks
        }
        
        # 완료된 작업 수집
        for future in as_completed(future_to_stock):
            ticker, name = future_to_stock[future]
            completed += 1
            
            try:
                result = future.result()
                if result:
                    results.append(result)
                    ticker, name, signal, confidence = result
                    logger.info(f"[{completed}/{len(stocks)}] {ticker} {name}: {signal} ({confidence*100:.0f}%)")
                else:
                    logger.debug(f"[{completed}/{len(stocks)}] {ticker} {name}: 신호 없음")
                    
            except Exception as e:
                logger.error(f"[{ticker}] 처리 오류: {e}")
    
    logger.info(f"분석 완료: {len(results)}개 매수 신호 발견")
    
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
    logger.info("시총 상위 200개 종목 조회...")
    stocks = get_top_stocks(db, limit=200)
    logger.info(f"종목 {len(stocks)}개 조회 완료")
    
    # 거시경제 분석
    logger.info("거시경제 분석 시작...")
    macro_agent = MacroAgent(config, db)
    macro_analysis = macro_agent.analyze(lookback_days=90)
    logger.info(f"거시경제 분석 완료: {macro_analysis.get('market_outlook', 'N/A')}")
    
    # AI 분석 및 순위화
    logger.info("AI 분석 시작...")
    top_signals = analyze_and_rank(db, stocks, top_n=10, max_workers=5)
    logger.info(f"상위 신호 {len(top_signals)}개 추출")
    
    if not top_signals:
        logger.warning("매수 신호 없음")
        # 매수 신호가 없어도 거시경제 분석은 전송
        notifier = get_notifier()
        notifier.send_macro_report(macro_analysis)
        return
    
    # 시장 요약 (기존 함수 유지)
    market_summary = get_market_summary(db)
    market_summary['macro_analysis'] = macro_analysis
    
    # Telegram 전송
    logger.info("Telegram 리포트 전송...")
    notifier = get_notifier()
    
    success = notifier.send_daily_report(top_signals, market_summary)
    
    if success:
        logger.info("✅ 리포트 전송 완료")
        
        # 개별 신호 알림 (상위 3개만)
        signal_agent = SignalAgent(config, db)
        
        for ticker, name, signal, conf in top_signals[:3]:
            logger.info(f"[{ticker}] 신호 알림 전송...")
            
            # 상세 분석 결과 가져오기
            try:
                detailed_analysis = signal_agent.analyze(ticker)
                
                # reasons 추출 (4개 에이전트)
                reasons = {
                    'macro_summary': detailed_analysis.get('macro_summary', ''),
                    'news_summary': detailed_analysis.get('news_summary', ''),
                    'fundamentals_summary': detailed_analysis.get('fundamentals_summary', ''),
                    'dynamics_summary': detailed_analysis.get('dynamics_summary', ''),
                    'reasoning': detailed_analysis.get('reasoning', '')
                }
                
            except Exception as e:
                logger.error(f"[{ticker}] 상세 분석 실패: {e}")
                reasons = {}
            
            notifier.send_signal_alert(
                ticker=ticker,
                stock_name=name,
                signal=signal,
                confidence=conf,
                reasons=reasons
            )
    else:
        logger.error("❌ 리포트 전송 실패")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎉 일일 리포트 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
