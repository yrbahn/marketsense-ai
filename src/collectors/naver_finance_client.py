"""네이버증권 재무제표 크롤러"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List
import time

logger = logging.getLogger("marketsense")


class NaverFinanceClient:
    """네이버증권 재무제표 크롤러"""
    
    BASE_URL = "https://finance.naver.com/item/coinfo.naver"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        logger.info("[NaverFinance] 크롤러 초기화")
    
    def get_financial_statements(self, ticker: str) -> Dict:
        """재무제표 크롤링
        
        Args:
            ticker: 종목 코드 (6자리)
            
        Returns:
            {
                "분기": [
                    {
                        "period": "2024.09",
                        "손익계산서": {...},
                        "재무상태표": {...},
                        "현금흐름표": {...}
                    },
                    ...
                ]
            }
        """
        try:
            # 재무제표 페이지 요청
            url = f"{self.BASE_URL}?code={ticker}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {}
            
            # 손익계산서 탭
            income_data = self._parse_income_statement(soup, ticker)
            if income_data:
                result["손익계산서"] = income_data
            
            # 재무상태표 탭 (별도 요청 필요할 수 있음)
            balance_data = self._parse_balance_sheet(soup, ticker)
            if balance_data:
                result["재무상태표"] = balance_data
            
            # 현금흐름표 탭
            cashflow_data = self._parse_cashflow_statement(soup, ticker)
            if cashflow_data:
                result["현금흐름표"] = cashflow_data
            
            return result
            
        except Exception as e:
            logger.error(f"[NaverFinance] {ticker} 크롤링 실패: {e}")
            return {}
    
    def _parse_income_statement(self, soup: BeautifulSoup, ticker: str) -> List[Dict]:
        """손익계산서 파싱"""
        try:
            # 네이버증권 구조에 맞춰 파싱
            # 실제 구조는 페이지 확인 후 수정 필요
            data = []
            
            # 분기별 테이블 찾기
            tables = soup.find_all('table', class_='gHead01')
            
            for table in tables:
                # 테이블 헤더에서 분기 정보 추출
                headers = table.find_all('th')
                periods = []
                for th in headers[1:]:  # 첫 번째는 항목명
                    period_text = th.get_text(strip=True)
                    if period_text and '20' in period_text:
                        periods.append(period_text)
                
                # 테이블 행에서 데이터 추출
                rows = table.find_all('tr')
                
                for i, period in enumerate(periods):
                    period_data = {"period": period}
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if not cells:
                            continue
                        
                        # 항목명
                        th = row.find('th')
                        if not th:
                            continue
                        
                        account_name = th.get_text(strip=True)
                        
                        # 해당 분기 값
                        if i + 1 < len(cells):
                            value_text = cells[i + 1].get_text(strip=True)
                            try:
                                # 쉼표 제거하고 숫자로 변환
                                value = float(value_text.replace(',', ''))
                                period_data[account_name] = value
                            except ValueError:
                                continue
                    
                    if len(period_data) > 1:  # period 외에 데이터 있으면
                        data.append(period_data)
                
                break  # 첫 번째 테이블만 사용
            
            return data[:4]  # 최근 4분기
            
        except Exception as e:
            logger.error(f"[NaverFinance] 손익계산서 파싱 실패: {e}")
            return []
    
    def _parse_balance_sheet(self, soup: BeautifulSoup, ticker: str) -> List[Dict]:
        """재무상태표 파싱 (간단 버전 - 추후 구현)"""
        # 재무상태표는 별도 탭이므로 추가 요청 필요
        return []
    
    def _parse_cashflow_statement(self, soup: BeautifulSoup, ticker: str) -> List[Dict]:
        """현금흐름표 파싱 (간단 버전 - 추후 구현)"""
        # 현금흐름표는 별도 탭이므로 추가 요청 필요
        return []
