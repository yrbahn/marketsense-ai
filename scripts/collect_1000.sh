#!/bin/bash
# 시총 상위 1,000개 주가 + 뉴스 수집 (10개 배치)

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "🚀 시총 상위 1,000개 주가 + 뉴스 수집"
echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1,000개를 100개씩 10개 배치로 나누기
$PYTHON -c "
import FinanceDataReader as fdr
df = fdr.StockListing('KRX')
df = df.nlargest(1000, 'Marcap')

batch_size = 100
for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i+batch_size]
    tickers = ' '.join(batch['Code'].tolist())
    with open(f'/tmp/batch_{i//batch_size}.txt', 'w') as f:
        f.write(tickers)

print(f'✅ {len(df)}개 종목을 {(len(df)-1)//batch_size + 1}개 배치로 분할')
" 2>&1 | grep -v Warning

echo ""

# 배치별로 주가 + 뉴스 동시 수집
for batch_file in /tmp/batch_*.txt; do
    batch_num=$(basename $batch_file .txt | cut -d_ -f2)
    tickers=$(cat $batch_file)
    
    echo "📦 배치 #$batch_num 수집 중..."
    
    # 주가 수집
    $PYTHON -m src.pipeline --collector dynamics --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료" || true
    
    # 뉴스 수집
    $PYTHON -m src.pipeline --collector news --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료" || true
    
    echo "  ✅ 배치 #$batch_num 완료"
    echo ""
done

echo "🎉 완료: $(date '+%Y-%m-%d %H:%M:%S')"

# 최종 통계
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import PriceData, NewsArticle
from src.utils.helpers import load_config

db = init_db(load_config())
with db.get_session() as s:
    prices = s.query(PriceData).count()
    price_stocks = s.query(PriceData.stock_id).distinct().count()
    news = s.query(NewsArticle).count()
    news_stocks = s.query(NewsArticle.stock_id).distinct().count()
    
    print(f'\\n📊 최종 수집 결과:')
    print(f'   주가: {prices:,}건 ({price_stocks}개 종목)')
    print(f'   뉴스: {news:,}건 ({news_stocks}개 종목)')
" 2>&1 | grep -v Warning

# 임시 파일 정리
rm -f /tmp/batch_*.txt
