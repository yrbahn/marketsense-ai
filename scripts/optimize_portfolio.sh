#!/bin/bash
# 포트폴리오 최적화 및 텔레그램 전송

set -e

cd "$(dirname "$0")/.."

# .env 파일 로드
export $(grep -v '^#' .env | xargs)

echo "[$(date)] 포트폴리오 최적화 시작"

# 포트폴리오 최적화 실행 (상위 200개 종목)
OUTPUT_FILE="cache/portfolio_$(date +%Y%m%d).json"

/Library/Developer/CommandLineTools/usr/bin/python3 -m src.optimize_portfolio \
    --top 200 \
    --method max_sharpe \
    --lookback 252 \
    --min-weight 0.005 \
    --max-weight 0.05 \
    --output "$OUTPUT_FILE"

echo "[$(date)] 포트폴리오 최적화 완료"
echo "결과 파일: $OUTPUT_FILE"
