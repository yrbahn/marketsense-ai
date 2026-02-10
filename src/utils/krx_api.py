"""KRX 정보데이터시스템 직접 수집

OTP 생성 → 데이터 다운로드 방식으로
공매도, 신용잔고 등의 데이터를 수집합니다.

References:
- http://data.krx.co.kr/
"""
import io
import logging
import requests
import pandas as pd
from datetime import datetime
from typing import Optional

logger = logging.getLogger("marketsense")


class KRXDataAPI:
    """KRX 정보데이터시스템 API"""
    
    OTP_URL = "http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
    DOWNLOAD_URL = "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://data.krx.co.kr/"
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # 세션 초기화 (메인 페이지 방문)
        self._init_session()
    
    def _init_session(self):
        """세션 초기화 (쿠키 획득)"""
        try:
            # KRX 메인 페이지 방문
            self.session.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", timeout=10)
        except Exception as e:
            logger.debug(f"[KRX] 세션 초기화 실패: {e}")
    
    def _generate_otp(self, params: dict) -> str:
        """OTP 생성"""
        try:
            resp = self.session.post(self.OTP_URL, data=params, timeout=10)
            if resp.status_code == 200:
                return resp.text
            else:
                logger.warning(f"[KRX] OTP 생성 실패: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"[KRX] OTP 생성 오류: {e}")
            return None
    
    def _download_csv(self, otp: str) -> Optional[pd.DataFrame]:
        """CSV 다운로드"""
        try:
            resp = self.session.post(
                self.DOWNLOAD_URL,
                data={'code': otp},
                timeout=30
            )
            
            if resp.status_code != 200:
                logger.warning(f"[KRX] CSV 다운로드 실패: {resp.status_code}")
                return None
            
            # CSV 파싱 (EUC-KR 인코딩)
            df = pd.read_csv(io.BytesIO(resp.content), encoding='EUC-KR')
            return df
            
        except Exception as e:
            logger.error(f"[KRX] CSV 다운로드 오류: {e}")
            return None
    
    def get_shorting_balance(self, date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
        """공매도 잔고 조회
        
        Args:
            date: YYYYMMDD 형식
            market: ALL, STK (주식), ETF, ETN, ELW
        
        Returns:
            DataFrame with columns: 종목코드, 종목명, 공매도잔고, etc.
        """
        params = {
            "locale": "ko_KR",
            "tboxisuCd_finder_stkisu0_0": "",
            "isuCd": "",
            "isuCd2": "",
            "codeNmisuCd_finder_stkisu0_0": "",
            "param1isuCd_finder_stkisu0_0": "",
            "trdDd": date,
            "mktsel": market,
            "money": "1",
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": "dbms/MDC/STAT/standard/MDCSTAT03901"
        }
        
        otp = self._generate_otp(params)
        if not otp:
            return None
        
        return self._download_csv(otp)
    
    def get_shorting_volume(self, date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
        """공매도 거래량 조회
        
        Args:
            date: YYYYMMDD 형식
            market: ALL, STK, ETF, ETN, ELW
        
        Returns:
            DataFrame with columns: 종목코드, 종목명, 공매도거래량, 공매도거래대금, etc.
        """
        params = {
            "locale": "ko_KR",
            "tboxisuCd_finder_stkisu0_0": "",
            "isuCd": "",
            "isuCd2": "",
            "codeNmisuCd_finder_stkisu0_0": "",
            "param1isuCd_finder_stkisu0_0": "",
            "trdDd": date,
            "mktsel": market,
            "money": "3",
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": "dbms/MDC/STAT/standard/MDCSTAT03701"
        }
        
        otp = self._generate_otp(params)
        if not otp:
            return None
        
        return self._download_csv(otp)
    
    def get_margin_trading(self, date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
        """신용거래 (융자/대주) 조회
        
        Args:
            date: YYYYMMDD 형식
            market: ALL, STK, ETF
        
        Returns:
            DataFrame with columns: 종목코드, 종목명, 융자매수, 융자상환, 융자잔고, etc.
        """
        params = {
            "locale": "ko_KR",
            "tboxisuCd_finder_secuprodisu1_0": "",
            "isuCd": "",
            "isuCd2": "",
            "codeNmisuCd_finder_secuprodisu1_0": "",
            "param1isuCd_finder_secuprodisu1_0": "",
            "trdDd": date,
            "money": "1",
            "csvxls_isNo": "false",
            "name": "fileDown",
            "url": "dbms/MDC/STAT/standard/MDCSTAT04001"
        }
        
        otp = self._generate_otp(params)
        if not otp:
            return None
        
        return self._download_csv(otp)


# 편의 함수
def get_krx_shorting_balance(date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
    """공매도 잔고 조회 (편의 함수)"""
    api = KRXDataAPI()
    return api.get_shorting_balance(date, market)


def get_krx_shorting_volume(date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
    """공매도 거래량 조회 (편의 함수)"""
    api = KRXDataAPI()
    return api.get_shorting_volume(date, market)


def get_krx_margin_trading(date: str, market: str = "ALL") -> Optional[pd.DataFrame]:
    """신용거래 조회 (편의 함수)"""
    api = KRXDataAPI()
    return api.get_margin_trading(date, market)
