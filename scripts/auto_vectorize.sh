#!/bin/bash
# 자동 증분 벡터화 스크립트

set -e

cd "$(dirname "$0")/.."

echo "[$(date)] 증분 벡터화 시작"

/Library/Developer/CommandLineTools/usr/bin/python3 scripts/incremental_vectorize.py

echo "[$(date)] 증분 벡터화 완료"
