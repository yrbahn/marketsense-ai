#!/bin/bash
# 전체 2,884개 재무제표 수집 (20개 배치)

set -e
cd "$(dirname "$0")/.."

PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"

echo "🚀 전체 2,884개 재무제표 수집"
echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "⚠️  DART API가 느려서 오래 걸립니다 (예상: 8-12시간)"
echo ""

# 전체 KRX 종목 추출
$PYTHON -c "
import FinanceDataReader as fdr

df = fdr.StockListing('KRX')
df = df.nlargest(2884, 'Marcap')

print(f'✅ 전체 {len(df)}개 종목 추출')

# 100개씩 배치로 나누기
batch_size = 100
for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i+batch_size]
    tickers = ' '.join(batch['Code'].tolist())
    with open(f'/tmp/batch_fund_{i//batch_size}.txt', 'w') as f:
        f.write(tickers)

num_batches = (len(df) - 1) // batch_size + 1
print(f'✅ {num_batches}개 배치로 분할')
" 2>&1 | grep -v Warning

echo ""

# 배치별로 재무제표 수집
for batch_file in /tmp/batch_fund_*.txt; do
    batch_num=$(basename $batch_file .txt | sed 's/batch_fund_//')
    tickers=$(cat $batch_file)
    
    echo "📦 배치 #$batch_num 수집 중..."
    
    # 재무제표 수집
    $PYTHON -m src.pipeline --collector fundamentals --tickers $tickers 2>&1 | grep -E "INFO.*수집|완료" | tail -3 || true
    
    echo "  ✅ 배치 #$batch_num 완료"
    
    # 진행률
    current=$((($batch_num + 1) * 100))
    total=2884
    progress=$((current * 100 / total))
    echo "  진행: $current/$total ($progress%)"
    echo ""
done

echo "🎉 완료: $(date '+%Y-%m-%d %H:%M:%S')"

# 최종 통계
$PYTHON -c "
from src.storage.database import init_db
from src.storage.models import FinancialStatement
from src.utils.helpers import load_config

db = init_db(load_config())
with db.get_session() as s:
    total = s.query(FinancialStatement).count()
    stocks = s.query(FinancialStatement.stock_id).distinct().count()
    
    print(f'\\n📊 재무제표 최종:')
    print(f'   총 건수: {total:,}건')
    print(f'   종목 수: {stocks:,}개')
" 2>&1 | grep -v Warning

# 임시 파일 정리
rm -f /tmp/batch_fund_*.txt
