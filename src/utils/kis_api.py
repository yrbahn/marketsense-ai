"""한국투자증권 OpenAPI 클라이언트

공매도, 신용잔고 등의 데이터를 수집합니다.

References:
- https://apiportal.koreainvestment.com/
- https://github.com/koreainvestment/open-trading-api
"""
import os
import logging
import requests
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger("marketsense")


class KISApi:
    """한국투자증권 OpenAPI 클라이언트"""
    
    # 실전투자
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    # 모의투자
    MOCK_URL = "https://openapivts.koreainvestment.com:29443"
    
    def __init__(self, app_key: str = None, app_secret: str = None, mock: bool = False):
        """
        Args:
            app_key: KIS APP KEY
            app_secret: KIS APP SECRET
            mock: 모의투자 여부
        """
        self.app_key = app_key or os.getenv("KIS_APP_KEY")
        self.app_secret = app_secret or os.getenv("KIS_APP_SECRET")
        self.mock = mock or os.getenv("KIS_MOCK", "false").lower() == "true"
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY와 KIS_APP_SECRET 환경변수가 필요합니다")
        
        self.base_url = self.MOCK_URL if self.mock else self.BASE_URL
        self.access_token = None
        
    def _get_access_token(self) -> str:
        """접근 토큰 발급"""
        if self.access_token:
            return self.access_token
        
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                self.access_token = result.get("access_token")
                logger.info("[KIS] 접근 토큰 발급 완료")
                return self.access_token
            else:
                logger.error(f"[KIS] 토큰 발급 실패: {resp.status_code} {resp.text}")
                return None
                
        except Exception as e:
            logger.error(f"[KIS] 토큰 발급 오류: {e}")
            return None
    
    def _get_headers(self, tr_id: str) -> Dict:
        """API 요청 헤더"""
        token = self._get_access_token()
        
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
    
    def get_shorting_balance(self, date: str = None) -> Optional[List[Dict]]:
        """공매도 잔고 조회
        
        Args:
            date: YYYYMMDD 형식 (기본값: 오늘)
        
        Returns:
            List of dicts with shorting balance info
        """
        # KIS API 공매도 조회 TR 코드 확인 필요
        # 예시 코드 (실제 TR 코드는 문서 확인 필요)
        
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        
        # TODO: KIS API 문서에서 공매도 조회 TR 코드 확인
        # 예: FHKST03030100 (가정)
        
        logger.warning("[KIS] 공매도 잔고 조회 API는 문서 확인이 필요합니다")
        return None
    
    def get_investor_trading(self, ticker: str, start_date: str, end_date: str = None) -> Optional[List[Dict]]:
        """투자자별 매매동향 조회
        
        Args:
            ticker: 종목코드 (6자리)
            start_date: YYYYMMDD
            end_date: YYYYMMDD (기본값: start_date)
        
        Returns:
            List of dicts with investor trading info
        """
        if not end_date:
            end_date = start_date
        
        # KIS API: 국내주식 투자자별 매매동향
        # TR ID: FHKST01010900 (예시, 문서 확인 필요)
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        
        headers = self._get_headers("FHKST01010900")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D"  # 일별
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                
                if result.get("rt_cd") == "0":
                    return result.get("output", [])
                else:
                    logger.warning(f"[KIS] API 응답 오류: {result.get('msg1')}")
                    return None
            else:
                logger.error(f"[KIS] API 호출 실패: {resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[KIS] 투자자 매매동향 조회 오류: {e}")
            return None


# 편의 함수
def get_kis_investor_trading(ticker: str, date: str) -> Optional[List[Dict]]:
    """투자자별 매매동향 조회 (편의 함수)"""
    try:
        api = KISApi()
        return api.get_investor_trading(ticker, date)
    except ValueError as e:
        logger.error(f"[KIS] API 초기화 실패: {e}")
        return None
