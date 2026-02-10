"""DART 공시 정보 수집기

금융감독원 전자공시시스템(DART) API를 사용하여
주요 공시 정보를 수집합니다.

주요 공시 유형:
- 실적 발표 (잠정실적, 영업실적)
- 유상증자
- 자사주 취득/처분
- 주식분할/병합
- 배당 결정
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

from .base_collector import BaseCollector
from src.storage.database import Database
from src.storage.models import Stock, DisclosureData

logger = logging.getLogger("marketsense")


class DisclosureCollector(BaseCollector):
    """DART 공시 정보 수집기"""

    # 주요 공시 키워드
    MAJOR_KEYWORDS = [
        "실적",
        "잠정실적",
        "영업실적",
        "유상증자",
        "무상증자",
        "자사주",
        "주식분할",
        "주식병합",
        "배당",
    ]

    def __init__(self, config: Dict, db: Database):
        super().__init__(config, db)
        self.api_key = os.getenv("DART_API_KEY")
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경변수가 필요합니다")
        
        self.base_url = "https://opendart.fss.or.kr/api"
        self.lookback_days = config.get("disclosure", {}).get("lookback_days", 30)
        
        # 회사코드 매핑 로드
        self._load_corp_mapping()

    def collect(self, tickers: list = None, **kwargs):
        """주요 공시 수집"""
        with self.db.get_session() as session:
            run = self._start_run(session)
            total = 0
            
            try:
                # 최근 30일 공시 수집
                end_date = datetime.now()
                start_date = end_date - timedelta(days=self.lookback_days)
                
                logger.info(f"[Disclosure] {start_date.date()} ~ {end_date.date()} 공시 수집")
                
                # DART API로 공시 목록 조회
                page = 1
                while True:
                    disclosures = self._fetch_disclosures(
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d"),
                        page
                    )
                    
                    if not disclosures:
                        break
                    
                    for disclosure in disclosures:
                        # 주요 공시 필터링
                        if not self._is_major_disclosure(disclosure):
                            continue
                        
                        # 종목 매칭
                        corp_code = disclosure.get("corp_code")
                        stock = self._find_stock_by_corp_code(session, corp_code)
                        
                        if not stock:
                            continue
                        
                        # 중복 체크
                        rcept_no = disclosure.get("rcept_no")
                        exists = session.query(DisclosureData).filter_by(
                            rcept_no=rcept_no
                        ).first()
                        
                        if exists:
                            continue
                        
                        # 공시 저장
                        disclosure_type = self._classify_disclosure(disclosure)
                        
                        disclosure_data = DisclosureData(
                            stock_id=stock.id,
                            rcept_no=rcept_no,
                            rcept_dt=datetime.strptime(disclosure["rcept_dt"], "%Y%m%d").date(),
                            corp_code=corp_code,
                            corp_name=disclosure.get("corp_name"),
                            report_nm=disclosure.get("report_nm"),
                            flr_nm=disclosure.get("flr_nm"),
                            rm=disclosure.get("rm"),
                            disclosure_type=disclosure_type,
                            disclosure_category="major"
                        )
                        
                        session.add(disclosure_data)
                        total += 1
                    
                    # 다음 페이지
                    page += 1
                    
                    if page > 100:  # 최대 100페이지
                        break
                    
                    session.flush()
                
                # 실시간 벡터화
                if total > 0:
                    try:
                        logger.info(f"[Disclosure] 즉시 벡터화 시작: {total}건")
                        self._vectorize_collected_disclosures(session, run.started_at)
                        logger.info(f"[Disclosure] 벡터화 완료")
                    except Exception as ve:
                        logger.error(f"[Disclosure] 벡터화 실패: {ve}")
                
                self._finish_run(run, total)
                logger.info(f"[Disclosure] 완료: {total}건 수집")
                
            except Exception as e:
                self._finish_run(run, total, str(e))
                raise
    
    def _fetch_disclosures(self, start_date: str, end_date: str, page: int) -> List[Dict]:
        """DART API로 공시 목록 조회"""
        try:
            url = f"{self.base_url}/list.json"
            params = {
                "crtfc_key": self.api_key,
                "bgn_de": start_date,
                "end_de": end_date,
                "page_no": page,
                "page_count": 100
            }
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code != 200:
                logger.warning(f"[Disclosure] API 오류: {resp.status_code}")
                return []
            
            data = resp.json()
            
            if data.get("status") != "000":
                logger.warning(f"[Disclosure] API 응답 오류: {data.get('message')}")
                return []
            
            return data.get("list", [])
            
        except Exception as e:
            logger.error(f"[Disclosure] API 호출 실패: {e}")
            return []
    
    def _is_major_disclosure(self, disclosure: Dict) -> bool:
        """주요 공시 여부 판단"""
        report_nm = disclosure.get("report_nm", "")
        
        for keyword in self.MAJOR_KEYWORDS:
            if keyword in report_nm:
                return True
        
        return False
    
    def _classify_disclosure(self, disclosure: Dict) -> str:
        """공시 유형 분류"""
        report_nm = disclosure.get("report_nm", "")
        
        if "잠정실적" in report_nm or "영업실적" in report_nm:
            return "실적발표"
        elif "유상증자" in report_nm:
            return "유상증자"
        elif "무상증자" in report_nm:
            return "무상증자"
        elif "자사주" in report_nm:
            if "취득" in report_nm or "매입" in report_nm:
                return "자사주취득"
            elif "처분" in report_nm or "소각" in report_nm:
                return "자사주처분"
            return "자사주"
        elif "주식분할" in report_nm:
            return "주식분할"
        elif "주식병합" in report_nm:
            return "주식병합"
        elif "배당" in report_nm:
            return "배당"
        
        return "기타"
    
    def _load_corp_mapping(self):
        """회사코드 매핑 로드"""
        import json
        from pathlib import Path
        
        cache_file = Path(__file__).parent.parent.parent / 'cache' / 'dart_corp_mapping.json'
        
        if not cache_file.exists():
            logger.warning("[Disclosure] 매핑 파일 없음. scripts/build_dart_mapping.py 실행 필요")
            self.corp_mapping = {}
            return
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            self.corp_mapping = json.load(f)
        
        logger.info(f"[Disclosure] 회사코드 매핑 로드 완료: {len(self.corp_mapping)}개")
    
    def _find_stock_by_corp_code(self, session, corp_code: str):
        """DART 회사코드로 종목 찾기"""
        # 매핑 조회
        if corp_code not in self.corp_mapping:
            return None
        
        ticker = self.corp_mapping[corp_code]['ticker']
        
        # DB에서 종목 조회
        stock = session.query(Stock).filter_by(ticker=ticker).first()
        
        return stock

    def _vectorize_collected_disclosures(self, session, started_at):
        """수집된 공시 즉시 벡터화"""
        from src.rag.vector_store import VectorStore
        
        # 이번 수집 이후 공시만 가져오기
        new_disclosures = session.query(DisclosureData).filter(
            DisclosureData.collected_at >= started_at
        ).all()
        
        if not new_disclosures:
            return
        
        # 배치 단위로 벡터화
        vs = VectorStore()
        batch_size = 1000
        
        for i in range(0, len(new_disclosures), batch_size):
            batch = new_disclosures[i:i + batch_size]
            disc_data = []
            
            for disc in batch:
                stock = session.query(Stock).filter_by(id=disc.stock_id).first()
                ticker = stock.ticker if stock else ''
                
                disc_data.append({
                    'id': str(disc.id),
                    'stock_id': disc.stock_id,
                    'ticker': ticker,
                    'report_nm': disc.report_nm or '',
                    'disclosure_type': disc.disclosure_type or '',
                    'rcept_dt': disc.rcept_dt
                })
            
            vs.add_disclosures(disc_data)
            logger.info(f"  → 공시 벡터화: {i + len(batch)}/{len(new_disclosures)}")
