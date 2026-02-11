"""OpenDartReader를 사용한 DART API 클라이언트"""
import os
import logging
from typing import Dict, Optional
from datetime import date
import OpenDartReader

logger = logging.getLogger("marketsense")


class OpenDartClient:
    """OpenDartReader 기반 DART API 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DART_API_KEY")
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다")
        
        self.dart = OpenDartReader(self.api_key)
        logger.info("[OpenDart] API 초기화 완료")
    
    def get_corp_code_list(self) -> Dict[str, str]:
        """전체 기업 고유번호 목록 다운로드
        
        Returns:
            {stock_code: corp_code, ...}
        """
        try:
            # OpenDartReader는 내부적으로 corp_code 매핑 관리
            df = self.dart.list()  # 전체 상장법인 목록
            corp_map = {}
            
            for _, row in df.iterrows():
                stock_code = row.get('stock_code')
                corp_code = row.get('corp_code')
                if stock_code and corp_code:
                    corp_map[stock_code.strip()] = corp_code.strip()
            
            logger.info(f"[OpenDart] 기업 고유번호 {len(corp_map)}개 로드")
            return corp_map
        
        except Exception as e:
            logger.error(f"[OpenDart] 고유번호 목록 다운로드 실패: {e}")
            return {}
    
    def get_financial_statements(self, corp_code: str, year: int, reprt_code: str) -> Dict:
        """재무제표 조회 (OpenDartReader 사용)
        
        Args:
            corp_code: DART 고유번호
            year: 사업연도 (YYYY)
            reprt_code: 보고서 코드
                - 11011: 사업보고서
                - 11012: 반기보고서
                - 11013: 1분기보고서
                - 11014: 3분기보고서
        
        Returns:
            {
                "손익계산서": {계정명: 금액, ...},
                "재무상태표": {계정명: 금액, ...},
                "현금흐름표": {계정명: 금액, ...}
            }
        """
        try:
            # finstate_all: 전체 재무제표 조회
            df = self.dart.finstate_all(corp_code, year, reprt_code=reprt_code, fs_div='CFS')
            
            if df is None or df.empty:
                return {}
            
            # 재무제표별로 구분하여 저장
            result = {}
            
            for _, row in df.iterrows():
                sj_nm = row.get('sj_nm', '')  # 재무제표명
                account_nm = row.get('account_nm', '')  # 계정명
                thstrm_amount = row.get('thstrm_amount', '')  # 당기금액
                
                if sj_nm and account_nm and thstrm_amount:
                    try:
                        # 금액 파싱
                        if str(thstrm_amount).strip() and str(thstrm_amount).strip() != '-':
                            amount = float(str(thstrm_amount).replace(',', ''))
                            
                            # 재무제표별로 구분
                            if sj_nm not in result:
                                result[sj_nm] = {}
                            result[sj_nm][account_nm] = amount
                    except (ValueError, AttributeError):
                        continue
            
            return result
        
        except Exception as e:
            logger.warning(f"[OpenDart] {corp_code} {year} {reprt_code} 조회 실패: {e}")
            return {}
