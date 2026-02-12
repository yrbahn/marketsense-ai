"""Base Agent for MarketSenseAI 2.0"""
import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger("marketsense")

# LLM 응답 캐시 (메모리 기반, TTL=1일)
_llm_cache = {}
_cache_ttl = timedelta(days=1)


class BaseAgent:
    """모든 에이전트의 기본 클래스"""

    def __init__(self, config: Dict, db=None):
        self.config = config
        self.db = db

        # Gemini API 설정
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다")

        genai.configure(api_key=api_key)

        # 모델 설정
        llm_config = config.get("llm", {})
        model_name = llm_config.get("gemini_model", "gemini-2.0-flash-exp")
        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_tokens", 4096)

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
        )

        logger.info(f"[{self.__class__.__name__}] Gemini 모델 초기화: {model_name}")

    def generate(self, prompt: str, use_cache: bool = True, **kwargs) -> str:
        """Gemini API 호출 (캐싱 지원)"""
        # 캐시 키 생성 (프롬프트 해시)
        if use_cache:
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
            
            # 캐시 확인
            if cache_key in _llm_cache:
                cached_data = _llm_cache[cache_key]
                # TTL 확인
                if datetime.now() - cached_data['timestamp'] < _cache_ttl:
                    logger.debug(f"[{self.__class__.__name__}] 캐시 히트: {cache_key[:8]}...")
                    return cached_data['response']
                else:
                    # 만료된 캐시 삭제
                    del _llm_cache[cache_key]
        
        # API 호출
        try:
            response = self.model.generate_content(prompt)
            result = response.text
            
            # 캐시 저장
            if use_cache:
                _llm_cache[cache_key] = {
                    'response': result,
                    'timestamp': datetime.now()
                }
                logger.debug(f"[{self.__class__.__name__}] 캐시 저장: {cache_key[:8]}...")
            
            return result
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Gemini API 오류: {e}")
            raise

    def analyze(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """에이전트별 분석 메서드 (서브클래스에서 구현)"""
        raise NotImplementedError("서브클래스에서 analyze()를 구현해야 합니다")
