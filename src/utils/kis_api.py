"""한국투자증권 OpenAPI 클라이언트

공매도, 신용잔고 등의 데이터를 수집합니다.

References:
- https://apiportal.koreainvestment.com/
- https://github.com/koreainvestment/open-trading-api
"""
import os
import json
import logging
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
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
        self.token_file = Path(__file__).parent.parent.parent / "cache" / "kis_token.json"
        
    def _load_cached_token(self) -> Optional[str]:
        """캐시된 토큰 로드"""
        if not self.token_file.exists():
            return None
        
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
            
            # 만료 시간 확인 (24시간)
            expires_at = datetime.fromisoformat(data.get('expires_at'))
            if datetime.now() < expires_at:
                logger.info("[KIS] 캐시된 토큰 사용")
                return data.get('access_token')
            else:
                logger.info("[KIS] 토큰 만료, 재발급 필요")
                return None
                
        except Exception as e:
            logger.debug(f"[KIS] 캐시 로드 실패: {e}")
            return None
    
    def _save_token(self, token: str):
        """토큰 캐시 저장"""
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'access_token': token,
                'expires_at': (datetime.now() + timedelta(hours=23)).isoformat()
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
                
        except Exception as e:
            logger.debug(f"[KIS] 토큰 캐시 저장 실패: {e}")
        
    def _get_access_token(self) -> str:
        """접근 토큰 발급 (캐싱)"""
        # 메모리 캐시 확인
        if self.access_token:
            return self.access_token
        
        # 파일 캐시 확인
        cached_token = self._load_cached_token()
        if cached_token:
            self.access_token = cached_token
            return self.access_token
        
        # 새로 발급
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
                
                # 캐시 저장
                self._save_token(self.access_token)
                
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
    
    def get_stock_price(self, ticker: str) -> Optional[Dict]:
        """주식 현재가 조회
        
        Args:
            ticker: 종목코드 (6자리)
        
        Returns:
            Dict with price info
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = self._get_headers("FHKST01010100")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                
                if result.get("rt_cd") == "0":
                    return result.get("output")
                else:
                    logger.warning(f"[KIS] 현재가 조회 오류: {result.get('msg1')}")
                    return None
            else:
                logger.error(f"[KIS] API 호출 실패: {resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"[KIS] 현재가 조회 오류: {e}")
            return None
    
    def get_investor_trading(self, ticker: str, start_date: str, end_date: str = None) -> Optional[List[Dict]]:
        """투자자별 매매동향 조회
        
        Args:
            ticker: 종목코드 (6자리)
            start_date: YYYYMMDD
            end_date: YYYYMMDD (기본값: start_date)
        
        Returns:
            List of dicts with investor trading info
            필드: prsn_ntby_qty, frgn_ntby_qty, orgn_ntby_qty (개인/외국인/기관 순매수)
        """
        if not end_date:
            end_date = start_date
        
        # KIS API: 국내주식 투자자별 매매동향
        # TR ID: FHKST01010900
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        
        headers = self._get_headers("FHKST01010900")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
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
    
    def get_investor_trend_daily(self, ticker: str, days: int = 30) -> Optional[List[Dict]]:
        """투자자별 매매동향 조회 (기간)
        
        Args:
            ticker: 종목코드 (6자리)
            days: 조회 일수 (기본값: 30일)
        
        Returns:
            List of dicts with daily investor trading
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        
        headers = self._get_headers("FHKST03010100")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                
                if result.get("rt_cd") == "0":
                    return result.get("output2", [])
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
