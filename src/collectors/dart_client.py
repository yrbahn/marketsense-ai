"""DART (전자공시시스템) API 클라이언트

금융감독원 전자공시 API: https://opendart.fss.or.kr/
"""
import os
import time
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("marketsense")


class DartClient:
    """DART API 클라이언트"""

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DART_API_KEY")
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")

    def _get(self, endpoint: str, params: Dict) -> Dict:
        """API GET 요청"""
        params["crtfc_key"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "000":
                error_msg = data.get("message", "Unknown error")
                logger.warning(f"[DART API] {endpoint} 오류: {error_msg}")
                return {}

            return data

        except Exception as e:
            logger.error(f"[DART API] {endpoint} 실패: {e}")
            return {}

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목 코드로 DART 고유번호 조회"""
        # DART 고유번호 목록 (전체 다운로드 필요)
        # 여기서는 API 호출로 대체 - 실제로는 캐싱 필요
        endpoint = "company.json"
        params = {"corp_code": stock_code}
        data = self._get(endpoint, params)
        return data.get("corp_code")

    def get_corp_code_list(self) -> Dict[str, str]:
        """전체 기업 고유번호 목록 다운로드"""
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": self.api_key}

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()

            # ZIP 파일 처리
            import zipfile
            import io
            import xml.etree.ElementTree as ET

            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                with z.open("CORPCODE.xml") as f:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    corp_map = {}
                    for company in root.findall("list"):
                        corp_code = company.find("corp_code").text
                        stock_code = company.find("stock_code").text
                        if stock_code and stock_code.strip():
                            corp_map[stock_code.strip()] = corp_code

                    logger.info(f"[DART] 기업 고유번호 {len(corp_map)}개 로드")
                    return corp_map

        except Exception as e:
            logger.error(f"[DART] 고유번호 목록 다운로드 실패: {e}")
            return {}

    def get_financial_statements(
        self, corp_code: str, year: int, report_code: str = "11011"
    ) -> List[Dict]:
        """재무제표 조회

        Args:
            corp_code: DART 고유번호
            year: 사업연도
            report_code: 보고서 코드
                - 11011: 사업보고서
                - 11012: 반기보고서
                - 11013: 1분기보고서
                - 11014: 3분기보고서
        """
        endpoint = "fnlttSinglAcntAll.json"
        params = {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
        }

        data = self._get(endpoint, params)
        return data.get("list", [])

    def parse_financial_statements(self, raw_data: List[Dict]) -> Dict[str, Dict]:
        """재무제표 데이터 파싱

        Returns:
            {
                "income_statement": {...},
                "balance_sheet": {...},
                "cash_flow": {...}
            }
        """
        result = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        }

        # 재무제표 구분
        fs_map = {
            "IS": "income_statement",  # 손익계산서
            "BS": "balance_sheet",  # 재무상태표
            "CF": "cash_flow",  # 현금흐름표
        }

        for item in raw_data:
            fs_div = item.get("sj_div")  # 재무제표 구분
            account_nm = item.get("account_nm")  # 계정명
            thstrm_amount = item.get("thstrm_amount")  # 당기금액

            if fs_div in fs_map and account_nm and thstrm_amount:
                try:
                    # 금액 파싱 (쉼표 제거)
                    amount = float(thstrm_amount.replace(",", ""))
                    result[fs_map[fs_div]][account_nm] = amount
                except (ValueError, AttributeError):
                    continue

        return result
