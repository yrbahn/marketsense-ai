#!/bin/bash
# 백테스팅 엔진 테스트

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "📊 백테스팅 엔진 테스트"
echo ""

# 1. Buy & Hold (삼성전자, 1년)
echo "🧪 테스트 1: Buy & Hold (삼성전자, 1년)"
$PYTHON -m src.run_backtest --ticker 005930 --years 1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 2. SMA 크로스오버 전략
echo "🧪 테스트 2: SMA 골든크로스 전략 (SK하이닉스, 1년)"
$PYTHON -m src.run_backtest --ticker 000660 --strategy sma_crossover --years 1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 3. 모든 전략 비교
echo "🧪 테스트 3: 전략 비교 (NAVER, 1년)"
$PYTHON -m src.run_backtest --ticker 035420 --compare-strategies --years 1

echo ""
echo "🎉 모든 테스트 완료!"
