#!/usr/bin/env python3
"""
포트폴리오 최적화 CLI

Usage:
  # 특정 종목들로 최적화
  python3 -m src.optimize_portfolio --tickers 005930 000660 035420
  
  # 시총 상위 N개로 최적화
  python3 -m src.optimize_portfolio --top 50
  
  # AI 신호 기반 (BUY 신호 종목만)
  python3 -m src.optimize_portfolio --ai-filter buy
  
  # 제약 조건 설정
  python3 -m src.optimize_portfolio --top 20 --min-weight 0.05 --max-weight 0.3
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
from datetime import datetime

from src.storage.database import init_db
from src.storage.models import Stock
from src.portfolio.optimizer import PortfolioOptimizer
from src.utils.helpers import load_config


def get_top_stocks(session, top_n: int) -> list:
    """시총 상위 N개 종목"""
    stocks = session.query(Stock).filter(
        Stock.is_active == True,
        Stock.market_cap.isnot(None)
    ).order_by(Stock.market_cap.desc()).limit(top_n).all()
    
    return [s.ticker for s in stocks]


def format_portfolio_result(portfolio: dict, show_details: bool = True):
    """포트폴리오 결과 포맷팅"""
    print("\n" + "=" * 60)
    print("📊 포트폴리오 최적화 결과")
    print("=" * 60)
    
    print(f"\n🎯 최적화 방법: {portfolio['method']}")
    print(f"📅 최적화 시점: {portfolio['optimized_at'][:19]}")
    print(f"📈 분석 기간: 최근 {portfolio['lookback_days']}일")
    
    print(f"\n💰 포트폴리오 통계:")
    print(f"  기대 수익률: {portfolio['expected_return']*100:.2f}% (연간)")
    print(f"  변동성:      {portfolio['volatility']*100:.2f}% (연간)")
    print(f"  샤프비율:    {portfolio['sharpe_ratio']:.3f}")
    print(f"  무위험 수익률: {portfolio['risk_free_rate']*100:.2f}%")
    
    print(f"\n📊 종목별 비중 (총 {len(portfolio['weights'])}개):")
    
    # 비중 순으로 정렬
    sorted_weights = sorted(
        portfolio['weights'].items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    for ticker, weight in sorted_weights:
        if weight > 0.001:  # 0.1% 이상만 표시
            bar_length = int(weight * 50)
            bar = "█" * bar_length
            print(f"  {ticker:8s} {weight*100:5.2f}%  {bar}")
    
    if show_details:
        print(f"\n📋 JSON 출력:")
        print(json.dumps(portfolio, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="포트폴리오 최적화")
    parser.add_argument("--config", default="config/config.yaml")
    
    # 종목 선택
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", nargs='+', help="종목 코드 리스트")
    group.add_argument("--top", type=int, help="시총 상위 N개")
    
    # 최적화 옵션
    parser.add_argument(
        "--method",
        choices=['max_sharpe', 'min_variance'],
        default='max_sharpe',
        help="최적화 방법"
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=252,
        help="분석 기간 (일)"
    )
    
    # 제약 조건
    parser.add_argument("--min-weight", type=float, default=0.0, help="최소 비중")
    parser.add_argument("--max-weight", type=float, default=1.0, help="최대 비중")
    
    # 출력 옵션
    parser.add_argument("--no-details", action='store_true', help="상세 정보 숨김")
    parser.add_argument("--output", help="JSON 파일로 저장")
    
    args = parser.parse_args()
    
    # 설정 로드
    config = load_config(args.config)
    db = init_db(config)
    
    # 종목 선택
    if args.tickers:
        tickers = args.tickers
    elif args.top:
        with db.get_session() as session:
            tickers = get_top_stocks(session, args.top)
        print(f"✅ 시총 상위 {args.top}개 종목 선택")
    
    print(f"📦 대상 종목: {len(tickers)}개")
    
    # 제약 조건
    constraints = {
        'min_weight': args.min_weight,
        'max_weight': args.max_weight
    }
    
    # 최적화 실행
    print(f"\n⚙️  포트폴리오 최적화 중...")
    print(f"   방법: {args.method}")
    print(f"   기간: {args.lookback}일")
    print(f"   비중 제약: {args.min_weight*100:.1f}% ~ {args.max_weight*100:.1f}%")
    
    optimizer = PortfolioOptimizer(db, risk_free_rate=0.035)
    
    try:
        portfolio = optimizer.optimize(
            tickers=tickers,
            lookback_days=args.lookback,
            method=args.method,
            constraints=constraints
        )
        
        # 결과 출력
        format_portfolio_result(portfolio, not args.no_details)
        
        # 파일 저장
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, indent=2, ensure_ascii=False)
            print(f"\n💾 저장: {args.output}")
        
    except ValueError as e:
        print(f"\n❌ 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
