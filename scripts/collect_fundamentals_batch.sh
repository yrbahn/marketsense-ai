#!/bin/bash
# 시총 상위 1,000개 재무제표 배치 수집

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "🚀 시총 상위 1,000개 재무제표 배치 수집"
echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')"

# FinanceDataReader로 시총 상위 1,000개 추출
$PYTHON -c "
import FinanceDataReader as fdr
df = fdr.StockListing('KRX')
df = df.nlargest(1000, 'Marcap')
tickers = df['Code'].tolist()

# 100개씩 배치로 나누기
batch_size = 100
for i in range(0, len(tickers), batch_size):
    batch = tickers[i:i+batch_size]
    with open(f'/tmp/batch_{i//batch_size}.txt', 'w') as f:
        f.write(' '.join(batch))

print(f'총 {len(tickers)}개를 {(len(tickers)-1)//batch_size + 1}개 배치로 분할')
" 2>&1 | grep -v Warning

# 배치별로 순차 실행
for batch_file in /tmp/batch_*.txt; do
    batch_num=$(basename $batch_file .txt | cut -d_ -f2)
    tickers=$(cat $batch_file)
    
    echo ""
    echo "📦 배치 #$batch_num 수집 중..."
    $PYTHON -m src.pipeline --collector fundamentals --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료"
    
    # 배치 간 대기 (API rate limit)
    sleep 2
done

echo ""
echo "🎉 완료: $(date '+%Y-%m-%d %H:%M:%S')"

# 통계
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import FinancialStatement
from src.utils.helpers import load_config
db = init_db(load_config())
with db.get_session() as s:
    total = s.query(FinancialStatement).count()
    stocks = s.query(FinancialStatement.stock_id).distinct().count()
    print(f'\\n📊 수집 결과:')
    print(f'   재무제표: {total:,}건')
    print(f'   종목 수: {stocks:,}개')
" 2>&1 | grep -v Warning

# 임시 파일 정리
rm -f /tmp/batch_*.txt
