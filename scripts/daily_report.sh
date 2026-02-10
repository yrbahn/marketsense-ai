#!/bin/bash
# 일일 시장 리포트 생성 및 전송

set -e

cd "$(dirname "$0")/.."

# .env 파일 로드
export $(grep -v '^#' .env | xargs)

echo "[$(date)] 일일 시장 리포트 생성 시작"

# 일일 리포트 실행
/Library/Developer/CommandLineTools/usr/bin/python3 -m src.daily_report

echo "[$(date)] 일일 리포트 완료"
