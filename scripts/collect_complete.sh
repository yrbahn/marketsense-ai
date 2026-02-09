#!/bin/bash
# 주요 종목 완전 수집 (뉴스+재무+주가)

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

# 시총 상위 50개
TICKERS="005930 000660 035420 005380 000270 051910 035720 105560 055550 003670 028260 068270 012330 207940 006400 000810 017670 096770 003550 018260 032830 034730 009150 066570 033780 015760 010130 086790 011200 034020 009540 024110 251270 000720 010140 011070 005490 018880 316140 005830 003490 005387 051900 047050 086280 071050 010950 011780 030200 161390"

echo "🚀 주요 50개 종목 완전 수집"
echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')"

echo ""
echo "📈 [1/2] 재무제표 수집 중..."
$PYTHON -m src.pipeline --collector fundamentals --tickers $TICKERS 2>&1 | grep -E "INFO.*수집|완료"

echo ""
echo "📰 [2/2] 뉴스 업데이트..."
$PYTHON -m src.pipeline --collector news --tickers $TICKERS 2>&1 | grep -E "INFO.*수집|완료"

echo ""
echo "🎉 완료: $(date '+%Y-%m-%d %H:%M:%S')"

# 통계
echo ""
echo "📊 수집 결과:"
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import Stock, NewsArticle, FinancialStatement, PriceData
from src.utils.helpers import load_config
db = init_db(load_config())
with db.get_session() as s:
    stocks = s.query(Stock).count()
    news = s.query(NewsArticle).count()
    financials = s.query(FinancialStatement).count()
    prices = s.query(PriceData).count()
    print(f'   종목: {stocks:,}개')
    print(f'   뉴스: {news:,}건')
    print(f'   재무제표: {financials:,}건')
    print(f'   주가: {prices:,}건')
"
