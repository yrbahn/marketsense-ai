"""LLM 기반 검색 쿼리 확장

종목 정보를 기반으로 LLM이 최적의 검색 키워드를 생성합니다.
"""
import os
import json
import logging
from typing import List, Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

logger = logging.getLogger("marketsense")


class QueryExpander:
    """LLM 기반 검색 쿼리 확장기"""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경변수가 필요합니다")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-flash-latest")
    
    def expand_query(self, stock_info: Dict[str, Any]) -> List[str]:
        """종목 정보로 검색 키워드 생성
        
        Args:
            stock_info: {
                'name': '제닉',
                'ticker': '123330',
                'sector': '화장품',
                'market_cap': 197200000000,
                'industry': '화장품'
            }
        
        Returns:
            ['제닉', '제닉 화장품', '마스크팩', 'K-뷰티', '하이드로겔']
        """
        name = stock_info.get('name', '')
        sector = stock_info.get('sector', '')
        market_cap = stock_info.get('market_cap', 0)
        industry = stock_info.get('industry', '')
        
        # 시가총액 포맷팅
        if market_cap > 1e12:
            mc_str = f"{market_cap / 1e12:.1f}조원"
        elif market_cap > 1e8:
            mc_str = f"{market_cap / 1e8:.0f}억원"
        else:
            mc_str = "N/A"
        
        prompt = f"""당신은 한국 증시 뉴스 검색 전문가입니다.

다음 종목의 관련 뉴스를 검색하기 위한 최적의 검색 키워드를 생성하세요.

종목 정보:
- 종목명: {name}
- 업종: {sector or industry or 'N/A'}
- 시가총액: {mc_str}

요구사항:
1. 5-7개의 검색 키워드 생성
2. 첫 번째는 반드시 종목명
3. 업종 특성을 반영한 키워드 포함
4. 관련 제품/기술/트렌드 키워드 포함
5. 한국어로 생성

출력 형식 (JSON 배열만):
["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]

예시:
종목: 삼성전자, 업종: 반도체
→ ["삼성전자", "삼성 반도체", "HBM", "파운드리", "반도체 투자"]

종목: 제닉, 업종: 화장품
→ ["제닉", "제닉 화장품", "마스크팩", "하이드로겔", "K-뷰티 수출"]

이제 위 종목의 키워드를 JSON 배열로만 출력하세요:"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # JSON 파싱
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            keywords = json.loads(text)
            
            if not isinstance(keywords, list):
                logger.warning(f"[QueryExpander] 잘못된 형식: {text}")
                return self._fallback_keywords(stock_info)
            
            # 종목명이 첫 번째인지 확인
            if keywords and keywords[0].lower() != name.lower():
                keywords.insert(0, name)
            
            logger.info(f"[QueryExpander] {name}: {len(keywords)}개 키워드 생성")
            return keywords[:7]  # 최대 7개
            
        except Exception as e:
            logger.error(f"[QueryExpander] {name} 실패: {e}")
            return self._fallback_keywords(stock_info)
    
    def _fallback_keywords(self, stock_info: Dict[str, Any]) -> List[str]:
        """폴백: 기본 키워드 생성"""
        keywords = [stock_info['name']]
        
        if stock_info.get('sector'):
            keywords.append(f"{stock_info['name']} {stock_info['sector']}")
            keywords.append(stock_info['sector'])
        
        return keywords
