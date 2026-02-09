#!/bin/bash
# 일일 데이터 업데이트 (뉴스 + 주가)

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"
LOG_DIR="logs"
DATE=$(date +%Y%m%d)

echo "📅 MarketSenseAI 일일 업데이트 - $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 뉴스 업데이트
echo "📰 뉴스 업데이트 중..."
$PYTHON -m src.pipeline --collector news > "$LOG_DIR/news_$DATE.log" 2>&1
echo "✅ 뉴스 완료"

# 2. 주가 업데이트
echo "📈 주가 업데이트 중..."
$PYTHON -m src.pipeline --collector dynamics > "$LOG_DIR/dynamics_$DATE.log" 2>&1
echo "✅ 주가 완료"

echo "🎉 업데이트 완료 - $(date '+%Y-%m-%d %H:%M:%S')"
