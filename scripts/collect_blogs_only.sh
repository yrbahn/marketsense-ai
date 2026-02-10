#!/bin/bash
# 블로그만 수집 (2차 수집용)

set -e

cd "$(dirname "$0")/.."

echo "[$(date)] 블로그 수집 시작"

/Library/Developer/CommandLineTools/usr/bin/python3 -m src.pipeline --collect blogs

echo "[$(date)] 블로그 수집 완료"
