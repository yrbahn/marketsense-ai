#!/usr/bin/env python3
"""
MarketSenseAI 2.0 - 종목 분석 CLI

Usage:
  python3 -m src.analyze --ticker 005930                    # 삼성전자 전체 분석
  python3 -m src.analyze --ticker 005930 --agent news      # 뉴스만
  python3 -m src.analyze --ticker 005930 --agent dynamics  # 기술적 분석만
  python3 -m src.analyze --macro                            # 거시경제만
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
from dotenv import load_dotenv

# .env 로드
load_dotenv()

from src.storage.database import init_db
from src.utils.helpers import load_config
from src.agents import (
    NewsAgent,
    FundamentalsAgent,
    DynamicsAgent,
    MacroAgent,
    SignalAgent,
)


def analyze_stock(ticker: str, agent_type: str = "all"):
    """종목 분석"""
    config = load_config()
    db = init_db(config)

    print(f"📊 MarketSenseAI 2.0 - {ticker} 분석")
    print("=" * 60)

    results = {}

    if agent_type in ("all", "news"):
        print("\n📰 뉴스 분석 중...")
        agent = NewsAgent(config, db)
        results["news"] = agent.analyze(ticker)
        print(json.dumps(results["news"], ensure_ascii=False, indent=2))

    if agent_type in ("all", "fundamentals"):
        print("\n💰 재무 분석 중...")
        agent = FundamentalsAgent(config, db)
        results["fundamentals"] = agent.analyze(ticker)
        print(json.dumps(results["fundamentals"], ensure_ascii=False, indent=2))

    if agent_type in ("all", "dynamics"):
        print("\n📈 기술적 분석 중...")
        agent = DynamicsAgent(config, db)
        results["dynamics"] = agent.analyze(ticker)
        print(json.dumps(results["dynamics"], ensure_ascii=False, indent=2))

    if agent_type == "all":
        print("\n🌍 거시경제 분석 중...")
        agent = MacroAgent(config, db)
        results["macro"] = agent.analyze()
        print(json.dumps(results["macro"], ensure_ascii=False, indent=2))

        print("\n🎯 최종 신호 통합 중...")
        agent = SignalAgent(config, db)
        results["signal"] = agent.aggregate(
            ticker,
            news_result=results.get("news"),
            fundamentals_result=results.get("fundamentals"),
            dynamics_result=results.get("dynamics"),
            macro_result=results.get("macro"),
        )
        print("\n" + "=" * 60)
        print("🎯 최종 투자 신호")
        print("=" * 60)
        signal = results["signal"]
        print(f"종목: {ticker}")
        print(f"신호: {signal.get('signal', 'N/A')}")
        print(f"신뢰도: {signal.get('confidence', 0):.2%}")
        print(f"리스크: {signal.get('risk_level', 'N/A')}")
        print(f"투자기간: {signal.get('time_horizon', 'N/A')}")
        print(f"\n요약: {signal.get('summary', 'N/A')}")
        print(f"\n분석근거:\n{signal.get('reasoning', 'N/A')}")

    return results


def analyze_macro():
    """거시경제 분석"""
    config = load_config()
    db = init_db(config)

    print("🌍 MarketSenseAI 2.0 - 거시경제 분석")
    print("=" * 60)

    agent = MacroAgent(config, db)
    result = agent.analyze()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="MarketSenseAI 2.0 종목 분석")
    parser.add_argument("--ticker", help="종목 코드 (예: 005930)")
    parser.add_argument(
        "--agent",
        choices=["all", "news", "fundamentals", "dynamics"],
        default="all",
        help="실행할 에이전트",
    )
    parser.add_argument("--macro", action="store_true", help="거시경제 분석만")
    args = parser.parse_args()

    if args.macro:
        analyze_macro()
    elif args.ticker:
        analyze_stock(args.ticker, args.agent)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
