#!/bin/bash
# 수급 데이터 수집 (백그라운드 실행)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/supply_demand_bg_$(date +%Y%m%d_%H%M%S).log"

echo "[$(date)] 수급 데이터 수집 백그라운드 시작" | tee -a "$LOG_FILE"

# nohup으로 백그라운드 실행
nohup bash "$SCRIPT_DIR/collect_supply_demand.sh" >> "$LOG_FILE" 2>&1 &

PID=$!
echo "[$(date)] PID: $PID" | tee -a "$LOG_FILE"
echo "[$(date)] 로그: $LOG_FILE" | tee -a "$LOG_FILE"

# 프로세스 확인
sleep 2
if ps -p $PID > /dev/null; then
    echo "[$(date)] ✅ 백그라운드 실행 중" | tee -a "$LOG_FILE"
else
    echo "[$(date)] ❌ 실행 실패" | tee -a "$LOG_FILE"
    exit 1
fi
