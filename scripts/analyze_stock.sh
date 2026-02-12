#!/bin/bash
# 종목 AI 분석 스크립트

if [ -z "$1" ]; then
    echo "사용법: $0 <종목코드>"
    echo "예: $0 005930"
    exit 1
fi

TICKER="$1"

cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs)

/Library/Developer/CommandLineTools/usr/bin/python3 << PYTHON_EOF
import sys
sys.path.insert(0, ".")

from src.storage.database import init_db
from src.agents.signal_agent import SignalAgent
from src.utils.helpers import load_config
import logging

# 경고 메시지 숨기기
logging.getLogger().setLevel(logging.WARNING)

config = load_config()
db = init_db(config)

ticker = "$TICKER"

print(f"\n📊 {ticker} AI 종합 분석\n")
print("=" * 60)
print("\n분석 중... (약 1-2분 소요)\n")

signal_agent = SignalAgent(config, db)

try:
    analysis = signal_agent.analyze(ticker)
    
    if analysis and 'summary' in analysis:
        print("\n" + "=" * 60)
        print(f"\n🎯 투자 신호: {analysis['signal']}")
        print(f"📈 확신도: {analysis['confidence']*100:.0f}%\n")
        print("=" * 60)
        print("\n💡 AI 통합 분석:\n")
        print(analysis['summary'])
        print("\n" + "=" * 60)
        
        # 개별 에이전트 요약
        print("\n📋 개별 분석 요약:\n")
        
        agent_results = analysis.get('agent_results', {})
        
        # 뉴스
        news = agent_results.get('news', {})
        if 'summary' in news:
            print(f"📰 뉴스: {news.get('sentiment', 'N/A')}")
            print(f"   {news['summary'][:200]}...")
            print()
        
        # 재무
        fundamentals = agent_results.get('fundamentals', {})
        if 'summary' in fundamentals:
            print(f"💼 재무: {fundamentals.get('valuation', 'N/A')}")
            print(f"   {fundamentals['summary'][:200]}...")
            print()
        
        # 기술적
        dynamics = agent_results.get('dynamics', {})
        if 'summary' in dynamics:
            print(f"📈 기술적: {dynamics.get('signal', 'N/A')}")
            print(f"   {dynamics['summary'][:200]}...")
            print()
        
        # 거시경제
        macro = agent_results.get('macro', {})
        if 'summary' in macro:
            print(f"🌍 거시경제: {macro.get('market_outlook', 'N/A')}")
            print(f"   {macro['summary'][:200]}...")
            print()
        
        print("=" * 60)
        
    elif 'error' in analysis:
        print(f"\n❌ 분석 실패: {analysis['error']}\n")
    else:
        print("\n❌ 분석 결과 없음\n")

except Exception as e:
    print(f"\n❌ 오류: {e}\n")
    import traceback
    traceback.print_exc()

PYTHON_EOF
