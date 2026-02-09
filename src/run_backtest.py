#!/usr/bin/env python3
"""
백테스팅 CLI

Usage:
  # Buy & Hold
  python3 -m src.run_backtest --ticker 005930 --years 2
  
  # 전략 백테스트
  python3 -m src.run_backtest --ticker 005930 --strategy sma_crossover --years 2
  
  # 벤치마크 비교
  python3 -m src.run_backtest --ticker 000660 --strategy rsi \
    --benchmark 005930 --years 1
  
  # 여러 전략 비교
  python3 -m src.run_backtest --ticker 035420 --compare-strategies --years 3
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
from datetime import datetime, timedelta
from typing import List

from src.storage.database import init_db
from src.storage.models import Stock
from src.backtest import BacktestEngine, BacktestResult, STRATEGIES
from src.utils.helpers import load_config


def format_result(result: BacktestResult, verbose: bool = True):
    """결과 포맷팅"""
    print("\n" + "=" * 70)
    print(f"📊 백테스트 결과: {result.strategy_name}")
    print("=" * 70)
    
    print(f"\n📅 기간:")
    print(f"  시작: {result.start_date.strftime('%Y-%m-%d')}")
    print(f"  종료: {result.end_date.strftime('%Y-%m-%d')}")
    days = (result.end_date - result.start_date).days
    print(f"  기간: {days}일 ({days/365:.1f}년)")
    
    print(f"\n💰 수익률:")
    print(f"  초기 자금: {result.initial_capital:,.0f}원")
    print(f"  최종 금액: {result.final_value:,.0f}원")
    print(f"  총 수익률: {result.total_return*100:+.2f}%")
    print(f"  연간 수익률: {result.annual_return*100:+.2f}%")
    
    if result.benchmark_return is not None:
        alpha = (result.total_return - result.benchmark_return) * 100
        print(f"  벤치마크: {result.benchmark_return*100:+.2f}%")
        print(f"  알파: {alpha:+.2f}%")
    
    print(f"\n📊 리스크 지표:")
    print(f"  변동성: {result.volatility*100:.2f}%")
    print(f"  최대 낙폭: {result.max_drawdown*100:.2f}%")
    print(f"  샤프비율: {result.sharpe_ratio:.3f}")
    print(f"  승률: {result.win_rate*100:.1f}%")
    
    print(f"\n📝 거래 내역:")
    print(f"  총 거래: {result.num_trades}회")
    
    if verbose and result.trades:
        print(f"\n  최근 5개 거래:")
        for trade in result.trades[-5:]:
            date = trade['date'].strftime('%Y-%m-%d')
            action = trade['action']
            price = trade['price']
            shares = trade['shares']
            value = trade['value']
            emoji = "🟢" if action == 'buy' else "🔴"
            print(f"    {emoji} {date} {action:4s} {shares:8.0f}주 @ {price:,.0f}원 = {value:,.0f}원")


def compare_strategies(
    engine: BacktestEngine,
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    db
) -> List[BacktestResult]:
    """여러 전략 비교"""
    results = []
    
    # Buy & Hold
    print(f"\n🔄 Buy & Hold 실행 중...")
    bh_result = engine.run_buy_hold(ticker, start_date, end_date)
    results.append(bh_result)
    
    # 각 전략
    for strategy_name, strategy_func in STRATEGIES.items():
        print(f"🔄 {strategy_name} 실행 중...")
        try:
            result = engine.run_strategy(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                strategy_func=strategy_func,
                name=strategy_name
            )
            results.append(result)
        except Exception as e:
            print(f"  ⚠️  {strategy_name} 실패: {e}")
    
    return results


def print_comparison_table(results: List[BacktestResult]):
    """전략 비교 테이블"""
    print("\n" + "=" * 100)
    print("📊 전략 비교 (성과순)")
    print("=" * 100)
    
    # 정렬 (총 수익률순)
    sorted_results = sorted(results, key=lambda r: r.total_return, reverse=True)
    
    # 헤더
    print(f"\n{'전략':20s} {'수익률':>10s} {'연수익률':>10s} {'변동성':>8s} {'MDD':>8s} {'샤프':>8s} {'승률':>8s} {'거래':>6s}")
    print("-" * 100)
    
    # 각 전략
    for r in sorted_results:
        name = r.strategy_name[:20]
        total_ret = f"{r.total_return*100:+.1f}%"
        annual_ret = f"{r.annual_return*100:+.1f}%"
        vol = f"{r.volatility*100:.1f}%"
        mdd = f"{r.max_drawdown*100:.1f}%"
        sharpe = f"{r.sharpe_ratio:.2f}"
        win_rate = f"{r.win_rate*100:.0f}%"
        trades = f"{r.num_trades}회"
        
        print(f"{name:20s} {total_ret:>10s} {annual_ret:>10s} {vol:>8s} {mdd:>8s} {sharpe:>8s} {win_rate:>8s} {trades:>6s}")


def main():
    parser = argparse.ArgumentParser(description="백테스팅 엔진")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--ticker", required=True, help="종목 코드")
    
    # 기간
    parser.add_argument("--start", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--years", type=float, help="최근 N년")
    parser.add_argument("--months", type=int, help="최근 N개월")
    
    # 전략
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()),
        help="전략 선택"
    )
    parser.add_argument(
        "--compare-strategies",
        action='store_true',
        help="모든 전략 비교"
    )
    
    # 벤치마크
    parser.add_argument("--benchmark", help="벤치마크 종목 코드")
    
    # 자본
    parser.add_argument(
        "--capital",
        type=float,
        default=10_000_000,
        help="초기 자금 (기본: 1천만원)"
    )
    
    # 출력
    parser.add_argument("--verbose", action='store_true', help="상세 출력")
    parser.add_argument("--output", help="JSON 파일로 저장")
    
    args = parser.parse_args()
    
    # 설정
    config = load_config(args.config)
    db = init_db(config)
    
    # 기간 설정
    end_date = datetime.now()
    if args.end:
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    
    if args.start:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    elif args.years:
        start_date = end_date - timedelta(days=int(args.years * 365))
    elif args.months:
        start_date = end_date - timedelta(days=args.months * 30)
    else:
        start_date = end_date - timedelta(days=365)  # 기본 1년
    
    # 엔진 초기화
    engine = BacktestEngine(db, initial_capital=args.capital)
    
    # 종목 확인
    with db.get_session() as session:
        stock = session.query(Stock).filter_by(ticker=args.ticker).first()
        if not stock:
            print(f"❌ 종목을 찾을 수 없습니다: {args.ticker}")
            sys.exit(1)
        print(f"✅ 종목: {stock.name} ({args.ticker})")
    
    print(f"📅 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 전략 비교 모드
    if args.compare_strategies:
        results = compare_strategies(engine, args.ticker, start_date, end_date, db)
        print_comparison_table(results)
        
        # 최고 성과
        best = max(results, key=lambda r: r.sharpe_ratio)
        print(f"\n🏆 최고 샤프비율: {best.strategy_name} ({best.sharpe_ratio:.3f})")
        
        if args.output:
            output_data = [{
                'strategy': r.strategy_name,
                'total_return': r.total_return,
                'annual_return': r.annual_return,
                'sharpe_ratio': r.sharpe_ratio,
                'max_drawdown': r.max_drawdown
            } for r in results]
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"💾 저장: {args.output}")
        
        return
    
    # 단일 전략
    if args.strategy:
        strategy_func = STRATEGIES[args.strategy]
        print(f"\n🔄 {args.strategy} 전략 실행 중...")
        result = engine.run_strategy(
            ticker=args.ticker,
            start_date=start_date,
            end_date=end_date,
            strategy_func=strategy_func,
            benchmark=args.benchmark,
            name=args.strategy
        )
    else:
        # Buy & Hold
        print(f"\n🔄 Buy & Hold 실행 중...")
        result = engine.run_buy_hold(args.ticker, start_date, end_date)
    
    # 결과 출력
    format_result(result, args.verbose)
    
    # JSON 저장
    if args.output:
        output_data = {
            'strategy': result.strategy_name,
            'ticker': args.ticker,
            'start_date': result.start_date.isoformat(),
            'end_date': result.end_date.isoformat(),
            'initial_capital': result.initial_capital,
            'final_value': result.final_value,
            'total_return': result.total_return,
            'annual_return': result.annual_return,
            'volatility': result.volatility,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'num_trades': result.num_trades
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 저장: {args.output}")


if __name__ == "__main__":
    main()
