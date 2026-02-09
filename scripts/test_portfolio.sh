#!/bin/bash
# 포트폴리오 최적화 테스트

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "📊 포트폴리오 최적화 테스트"
echo ""

# 1. 주요 3개 종목 (삼성전자, SK하이닉스, NAVER)
echo "🧪 테스트 1: 주요 3개 종목"
$PYTHON -m src.optimize_portfolio --tickers 005930 000660 035420 --no-details

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 2. 시총 상위 10개
echo "🧪 테스트 2: 시총 상위 10개"
$PYTHON -m src.optimize_portfolio --top 10 --no-details

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 3. 최소 분산 포트폴리오
echo "🧪 테스트 3: 최소 분산 (시총 상위 10개)"
$PYTHON -m src.optimize_portfolio --top 10 --method min_variance --no-details

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 4. 비중 제약 조건
echo "🧪 테스트 4: 비중 제약 (5%~20%)"
$PYTHON -m src.optimize_portfolio --top 20 --min-weight 0.05 --max-weight 0.2 --no-details

echo ""
echo "🎉 모든 테스트 완료!"
