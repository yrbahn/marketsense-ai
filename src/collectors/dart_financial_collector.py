#!/usr/bin/env python3
"""OpenDartReader 기반 재무제표 수집기

빠르고 정확한 분기별 재무제표 수집
"""
import logging
import OpenDartReader
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.storage.models import Stock, FinancialStatement

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("marketsense")


class DartFinancialCollector:
    """OpenDartReader 기반 재무제표 수집기"""
    
    # 보고서 코드
    REPORT_CODES = {
        '11013': '1분기',
        '11012': '반기',
        '11014': '3분기',
        '11011': '연간'
    }
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: DART API 키
        """
        self.dart = OpenDartReader(api_key)
        logger.info("OpenDartReader 초기화 완료")
    
    def get_financial_statement(self, ticker: str, year: int, quarter: str) -> Optional[Dict]:
        """재무제표 가져오기
        
        Args:
            ticker: 종목 코드
            year: 연도
            quarter: 분기 코드 ('11013', '11012', '11014', '11011')
            
        Returns:
            {'revenue': float, 'operating_income': float, ...}
        """
        try:
            # 재무제표 조회
            df = self.dart.finstate(ticker, year, reprt_code=quarter)
            
            if df.empty:
                logger.warning(f"[{ticker}] {year} {self.REPORT_CODES.get(quarter)} 데이터 없음")
                return None
            
            # 계정 항목 추출
            data = {
                'year': year,
                'quarter': self.REPORT_CODES.get(quarter, quarter),
                'report_code': quarter
            }
            
            # 주요 항목 매핑
            mappings = {
                '매출액': 'revenue',
                '영업이익': 'operating_income',
                '당기순이익(손실)': 'net_income',
                '자산총계': 'total_assets',
                '부채총계': 'total_liabilities',
                '자본총계': 'total_equity',
                '유동자산': 'current_assets',
                '유동부채': 'current_liabilities',
                '영업활동현금흐름': 'operating_cash_flow',
            }
            
            for account_name, field_name in mappings.items():
                row = df[df['account_nm'] == account_name]
                if not row.empty:
                    value_str = row.iloc[0]['thstrm_amount']
                    try:
                        # 쉼표 제거 후 숫자로 변환
                        value = float(value_str.replace(',', ''))
                        data[field_name] = value
                    except:
                        pass
            
            # 기본 지표 계산
            if 'net_income' in data and 'total_equity' in data and data['total_equity'] > 0:
                # ROE (%)
                data['roe'] = (data['net_income'] / data['total_equity']) * 100
            
            if 'total_liabilities' in data and 'total_equity' in data and data['total_equity'] > 0:
                # 부채비율 (%)
                data['debt_ratio'] = (data['total_liabilities'] / data['total_equity']) * 100
            
            if 'current_assets' in data and 'current_liabilities' in data and data['current_liabilities'] > 0:
                # 유동비율 (%)
                data['current_ratio'] = (data['current_assets'] / data['current_liabilities']) * 100
            
            if 'operating_income' in data and 'revenue' in data and data['revenue'] > 0:
                # 영업이익률 (%)
                data['operating_margin'] = (data['operating_income'] / data['revenue']) * 100
            
            if 'net_income' in data and 'revenue' in data and data['revenue'] > 0:
                # 순이익률 (%)
                data['net_margin'] = (data['net_income'] / data['revenue']) * 100
            
            logger.debug(f"[{ticker}] {year} {self.REPORT_CODES.get(quarter)} 수집: {list(data.keys())}")
            return data
            
        except Exception as e:
            logger.error(f"[{ticker}] {year} {quarter} 수집 오류: {e}")
            return None
    
    def get_recent_quarters(self, count: int = 4) -> List[tuple]:
        """최근 N개 분기 목록
        
        Args:
            count: 분기 개수
            
        Returns:
            [(year, quarter_code), ...]
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # 현재 분기 결정
        if current_month <= 3:
            current_quarter = '11011'  # 전년 연간
            current_year -= 1
        elif current_month <= 5:
            current_quarter = '11013'  # 1분기
        elif current_month <= 8:
            current_quarter = '11012'  # 반기
        elif current_month <= 11:
            current_quarter = '11014'  # 3분기
        else:
            current_quarter = '11011'  # 연간
        
        quarters = []
        quarter_sequence = ['11011', '11014', '11012', '11013']  # 역순
        
        year = current_year
        quarter_idx = quarter_sequence.index(current_quarter)
        
        for _ in range(count):
            quarters.append((year, quarter_sequence[quarter_idx]))
            
            # 다음 분기 (과거로)
            quarter_idx += 1
            if quarter_idx >= len(quarter_sequence):
                quarter_idx = 0
                year -= 1
        
        return quarters
    
    def collect_stock_financials(self, db, ticker: str, stock_id: int, quarters: int = 4) -> int:
        """종목 재무제표 수집
        
        Args:
            db: 데이터베이스
            ticker: 종목 코드
            stock_id: Stock ID
            quarters: 수집할 분기 수
            
        Returns:
            수집된 개수
        """
        quarter_list = self.get_recent_quarters(quarters)
        collected = 0
        
        with db.get_session() as session:
            for year, quarter_code in quarter_list:
                # 분기 종료일 계산
                quarter_name = self.REPORT_CODES.get(quarter_code)
                if quarter_code == '11013':  # 1분기
                    period_end = datetime(year, 3, 31).date()
                elif quarter_code == '11012':  # 반기
                    period_end = datetime(year, 6, 30).date()
                elif quarter_code == '11014':  # 3분기
                    period_end = datetime(year, 9, 30).date()
                else:  # 11011 연간
                    period_end = datetime(year, 12, 31).date()
                
                # 이미 존재하는지 확인
                existing = session.query(FinancialStatement).filter(
                    FinancialStatement.stock_id == stock_id,
                    FinancialStatement.period_end == period_end,
                    FinancialStatement.source == 'opendartreader'
                ).first()
                
                if existing:
                    logger.debug(f"[{ticker}] {year} {quarter_name} 이미 존재")
                    continue
                
                # 재무제표 수집
                data = self.get_financial_statement(ticker, year, quarter_code)
                
                if not data:
                    continue
                
                # 데이터베이스 저장
                stmt = FinancialStatement(
                    stock_id=stock_id,
                    statement_type='dart_comprehensive',
                    period_type='quarterly' if quarter_code != '11011' else 'annual',
                    fiscal_quarter=quarter_name,
                    period_end=period_end,
                    revenue=data.get('revenue'),
                    operating_income=data.get('operating_income'),
                    net_income=data.get('net_income'),
                    total_assets=data.get('total_assets'),
                    total_liabilities=data.get('total_liabilities'),
                    total_equity=data.get('total_equity'),
                    operating_cash_flow=data.get('operating_cash_flow'),
                    raw_data=data,
                    collected_at=datetime.now(),
                    source='opendartreader'
                )
                
                session.add(stmt)
                collected += 1
            
            session.commit()
        
        if collected > 0:
            logger.info(f"[{ticker}] {collected}개 분기 재무제표 수집 완료")
        
        return collected
    
    def collect_all(self, db, limit: Optional[int] = None, skip_existing: bool = True):
        """전체 종목 재무제표 수집
        
        Args:
            db: 데이터베이스
            limit: 수집할 종목 수 제한 (None = 전체)
            skip_existing: 이미 데이터가 있는 종목 건너뛰기
        """
        # 종목 리스트 가져오기 (ticker, id만)
        with db.get_session() as session:
            query = session.query(Stock.ticker, Stock.id, Stock.name)
            
            if limit:
                query = query.limit(limit)
            
            stock_list = [(ticker, stock_id, name) for ticker, stock_id, name in query.all()]
            total = len(stock_list)
        
        logger.info(f"총 {total}개 종목 재무제표 수집 시작...")
        
        collected_stocks = 0
        collected_quarters = 0
        
        for i, (ticker, stock_id, name) in enumerate(stock_list):
            # 이미 데이터 있는지 확인
            if skip_existing:
                with db.get_session() as session:
                    existing_count = session.query(FinancialStatement).filter(
                        FinancialStatement.stock_id == stock_id,
                        FinancialStatement.source == 'opendartreader'
                    ).count()
                    
                    if existing_count >= 4:
                        logger.debug(f"[{ticker}] 이미 {existing_count}개 분기 데이터 존재, 스킵")
                        continue
            
            # 수집
            count = self.collect_stock_financials(db, ticker, stock_id)
            
            if count > 0:
                collected_stocks += 1
                collected_quarters += count
            
            # 진행 상황
            if (i + 1) % 10 == 0:
                logger.info(f"진행: {i+1}/{total} (수집: {collected_stocks}개 종목, {collected_quarters}개 분기)")
            
            # API 제한 방지 (초당 1개)
            if i % 5 == 0 and i > 0:
                import time
                time.sleep(1)
        
        logger.info(f"✅ 재무제표 수집 완료: {collected_stocks}개 종목, {collected_quarters}개 분기")


def main():
    """테스트/실행"""
    import sys
    from src.storage.database import init_db
    from src.utils.helpers import load_config
    
    config = load_config()
    db = init_db(config)
    
    # API 키
    api_key = config.get('dart_api_key')
    if not api_key:
        logger.error("DART API 키가 설정되지 않았습니다")
        return
    
    collector = DartFinancialCollector(api_key)
    
    if len(sys.argv) > 1:
        # 특정 종목 테스트
        ticker = sys.argv[1]
        
        with db.get_session() as session:
            stock = session.query(Stock).filter(Stock.ticker == ticker).first()
            
            if not stock:
                print(f"종목 {ticker} 없음")
                return
        
        print(f"\n{stock.name} ({ticker}) 재무제표 수집...\n")
        count = collector.collect_stock_financials(db, ticker, stock.id, quarters=4)
        print(f"\n✅ {count}개 분기 수집 완료")
        
        # 결과 출력
        with db.get_session() as session:
            stmts = session.query(FinancialStatement).filter(
                FinancialStatement.stock_id == stock.id
            ).order_by(
                FinancialStatement.fiscal_year.desc(),
                FinancialStatement.fiscal_quarter.desc()
            ).limit(4).all()
            
            print(f"\n수집된 재무제표 ({len(stmts)}개):")
            for stmt in stmts:
                print(f"  {stmt.fiscal_year} {stmt.fiscal_quarter}: 매출 {stmt.revenue/1e12:.2f}조원" if stmt.revenue else f"  {stmt.fiscal_year} {stmt.fiscal_quarter}: 데이터 없음")
    else:
        # 전체 수집
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--limit', type=int, help='수집할 종목 수')
        parser.add_argument('--no-skip', action='store_true', help='기존 데이터 무시하고 재수집')
        args = parser.parse_args()
        
        collector.collect_all(db, limit=args.limit, skip_existing=not args.no_skip)


if __name__ == "__main__":
    main()
