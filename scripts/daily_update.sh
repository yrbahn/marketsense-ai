#!/bin/bash
# 일일 데이터 업데이트 (뉴스 + 주가)
# 백그라운드 실행 (타임아웃 없음)

cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"
LOG_DIR="logs"
DATE=$(date +%Y%m%d)

echo "📅 MarketSenseAI 일일 업데이트 - $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 뉴스 업데이트 (백그라운드)
echo "📰 뉴스 업데이트 시작... (백그라운드)"
nohup $PYTHON -m src.pipeline --collector news > "$LOG_DIR/news_$DATE.log" 2>&1 &
NEWS_PID=$!
echo "   PID: $NEWS_PID"

# 2. 주가 업데이트 (백그라운드)
echo "📈 주가 업데이트 시작... (백그라운드)"
nohup $PYTHON -m src.pipeline --collector dynamics > "$LOG_DIR/dynamics_$DATE.log" 2>&1 &
DYNAMICS_PID=$!
echo "   PID: $DYNAMICS_PID"

echo ""
echo "✅ 백그라운드 실행 시작됨"
echo "📝 로그: $LOG_DIR/news_$DATE.log, $LOG_DIR/dynamics_$DATE.log"
echo "🔍 진행 확인: tail -f $LOG_DIR/dynamics_$DATE.log"
echo ""
echo "완료 시 별도 알림을 받게 됩니다."
