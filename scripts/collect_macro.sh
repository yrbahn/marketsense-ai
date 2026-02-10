#!/bin/bash
# 거시경제 데이터 수집 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "[$(date)] 거시경제 데이터 수집 시작"

# .env 로드
set -a
source .env
set +a

# MacroCollector 실행
/Library/Developer/CommandLineTools/usr/bin/python3 -m src.collectors.macro_collector

echo "[$(date)] 거시경제 데이터 수집 완료"
