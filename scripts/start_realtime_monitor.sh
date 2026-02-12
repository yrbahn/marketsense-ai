#!/bin/bash
# KIS API 실시간 모니터링 시작 스크립트

set -e

cd "$(dirname "$0")/.."

# .env 파일 로드
export $(grep -v '^#' .env | xargs)

echo "[$(date)] KIS API 실시간 모니터링 시작"
echo "  대상: 상위 200개 종목"
echo "  간격: 300초 (5분)"
echo "  임계값: ±3.0%"

/Library/Developer/CommandLineTools/usr/bin/python3 -m src.realtime_monitor \
    --top 200 \
    --interval 300 \
    --threshold 3.0

echo "[$(date)] 모니터링 종료"
