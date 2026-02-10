#!/bin/bash
# 전체 2,884개 중 나머지 1,884개 수집 (뉴스 + 주가)

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "🚀 나머지 1,884개 종목 수집"
echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1,001위 ~ 2,884위 추출
$PYTHON -c "
import FinanceDataReader as fdr

# 전체 KRX
df = fdr.StockListing('KRX')
df = df.nlargest(2884, 'Marcap')

# 1,001위부터 (이미 1,000개는 수집 완료)
remaining = df.iloc[1000:]

print(f'✅ 나머지 {len(remaining)}개 종목 추출')
print(f'   1,001위: {remaining.iloc[0][\"Name\"]} ({remaining.iloc[0][\"Code\"]})')
print(f'   2,884위: {remaining.iloc[-1][\"Name\"]} ({remaining.iloc[-1][\"Code\"]})')

# 100개씩 배치로 나누기
batch_size = 100
num_batches = (len(remaining) - 1) // batch_size + 1

for i in range(0, len(remaining), batch_size):
    batch = remaining.iloc[i:i+batch_size]
    tickers = ' '.join(batch['Code'].tolist())
    batch_num = i // batch_size + 10  # 10부터 시작 (0-9는 이미 완료)
    with open(f'/tmp/batch_remain_{batch_num}.txt', 'w') as f:
        f.write(tickers)

print(f'✅ {num_batches}개 배치로 분할 (배치 #10~#{9+num_batches})')
" 2>&1 | grep -v Warning

echo ""

# 배치별로 주가 + 뉴스 수집
for batch_file in /tmp/batch_remain_*.txt; do
    batch_num=$(basename $batch_file .txt | sed 's/batch_remain_//')
    tickers=$(cat $batch_file)
    
    echo "📦 배치 #$batch_num 수집 중..."
    
    # 주가 수집
    $PYTHON -m src.pipeline --collector dynamics --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료" | tail -3 || true
    
    # 뉴스 수집
    $PYTHON -m src.pipeline --collector news --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료" | tail -3 || true
    
    echo "  ✅ 배치 #$batch_num 완료"
    
    # 진행률 표시
    current=$((($batch_num - 9) * 100))
    total=1884
    progress=$((current * 100 / total))
    echo "  진행: $current/$total ($progress%)"
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
rm -f /tmp/batch_remain_*.txt
