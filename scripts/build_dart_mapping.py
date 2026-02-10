#!/usr/bin/env python3
"""DART 회사코드 매핑 구축

OpenDartReader로 전체 회사 목록을 다운로드하고
회사코드 → 종목코드 매핑을 JSON 파일로 저장합니다.

Usage:
    python scripts/build_dart_mapping.py
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def build_mapping():
    """DART 회사코드 매핑 구축"""
    import requests
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO
    
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY 환경변수가 필요합니다")
    
    logger.info("DART 회사코드 목록 다운로드 중...")
    
    # DART corpCode.xml 다운로드
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    
    resp = requests.get(url, timeout=30)
    
    if resp.status_code != 200:
        logger.error(f"다운로드 실패: {resp.status_code}")
        return
    
    # ZIP 압축 해제
    zip_file = zipfile.ZipFile(BytesIO(resp.content))
    xml_data = zip_file.read('CORPCODE.xml')
    
    logger.info("XML 파싱 중...")
    
    # XML 파싱
    root = ET.fromstring(xml_data)
    
    total_count = len(root.findall('list'))
    logger.info(f"총 {total_count}개 회사 조회 완료")
    
    # 매핑 딕셔너리 생성
    mapping = {}
    listed_count = 0
    
    for item in root.findall('list'):
        corp_code = item.findtext('corp_code')
        stock_code = item.findtext('stock_code')
        corp_name = item.findtext('corp_name')
        
        # 상장사만 (stock_code가 있는 경우)
        if stock_code and stock_code.strip() and stock_code.strip() != ' ':
            stock_code = stock_code.strip()
            
            mapping[corp_code] = {
                'ticker': stock_code,
                'name': corp_name
            }
            
            listed_count += 1
    
    logger.info(f"상장사: {listed_count}개")
    
    logger.info(f"매핑: {len(mapping)}개")
    
    # 저장
    cache_dir = Path(__file__).parent.parent / 'cache'
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / 'dart_corp_mapping.json'
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 저장 완료: {cache_file}")
    logger.info(f"✅ 이후 공시 수집이 빨라집니다!")


if __name__ == "__main__":
    build_mapping()
