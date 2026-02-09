#!/bin/bash
# 전체 데이터 순차 수집 스크립트

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo "🚀 MarketSenseAI 전체 데이터 수집 시작"
echo "   시작 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. 뉴스 수집
echo "📰 [1/3] 뉴스 수집 중..."
$PYTHON -m src.pipeline --collector news 2>&1 | tee "$LOG_DIR/news_$(date +%Y%m%d_%H%M%S).log"
echo "✅ 뉴스 수집 완료"
echo ""

# 2. 주가/기술지표 수집
echo "📈 [2/3] 주가 및 기술지표 수집 중..."
$PYTHON -m src.pipeline --collector dynamics 2>&1 | tee "$LOG_DIR/dynamics_$(date +%Y%m%d_%H%M%S).log"
echo "✅ 주가 수집 완료"
echo ""

# 3. 매크로 경제 수집
echo "🌍 [3/3] 매크로 경제 데이터 수집 중..."
$PYTHON -m src.pipeline --collector macro 2>&1 | tee "$LOG_DIR/macro_$(date +%Y%m%d_%H%M%S).log"
echo "✅ 매크로 수집 완료"
echo ""

echo "🎉 전체 수집 완료!"
echo "   종료 시각: $(date '+%Y-%m-%d %H:%M:%S')"

# DB 통계
echo ""
echo "📊 수집 결과:"
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import Stock, NewsArticle, PriceData, MacroReport
from src.utils.helpers import load_config
db = init_db(load_config())
with db.get_session() as s:
    stocks = s.query(Stock).count()
    news = s.query(NewsArticle).count()
    prices = s.query(PriceData).count()
    macro = s.query(MacroReport).count()
    print(f'   종목: {stocks:,}개')
    print(f'   뉴스: {news:,}건')
    print(f'   주가: {prices:,}건')
    print(f'   매크로: {macro:,}건')
"
