#!/bin/bash
# 아침에 수집 상태 확인

cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "📊 MarketSenseAI 수집 상태"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. 백그라운드 프로세스 확인
echo "1️⃣ 백그라운드 프로세스:"
if ps aux | grep "collect_fundamentals_batch" | grep -v grep > /dev/null; then
    echo "   ✅ 재무제표 수집 실행 중"
else
    echo "   ⚠️  재무제표 수집 종료됨"
fi
echo ""

# 2. 최근 로그 확인
echo "2️⃣ 최근 로그 (마지막 10줄):"
tail -10 logs/fundamentals_postgresql_*.log 2>/dev/null | grep -E "배치|진행|완료" || echo "   (로그 없음)"
echo ""

# 3. DB 데이터 확인
echo "3️⃣ 데이터베이스 현황:"
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import Stock, FinancialStatement, NewsArticle, PriceData
from src.utils.helpers import load_config

db = init_db(load_config())
with db.get_session() as s:
    stocks = s.query(Stock).count()
    financials = s.query(FinancialStatement).count()
    fs_stocks = s.query(FinancialStatement.stock_id).distinct().count()
    news = s.query(NewsArticle).count()
    prices = s.query(PriceData).count()
    
    print(f'   종목: {stocks:,}개')
    print(f'   재무제표: {financials:,}건 ({fs_stocks}개 종목)')
    print(f'   뉴스: {news:,}건')
    print(f'   주가: {prices:,}건')
" 2>&1 | grep -v Warning
echo ""

# 4. 예상 완료 시간
echo "4️⃣ 상태 요약:"
if ps aux | grep "collect_fundamentals_batch" | grep -v grep > /dev/null; then
    echo "   🔄 수집 진행 중 (완료까지 몇 시간 소요 가능)"
else
    echo "   ✅ 수집 완료"
fi
echo ""
echo "═══════════════════════════════════════════════════════"
