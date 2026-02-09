"""Base Agent for MarketSenseAI 2.0"""
import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger("marketsense")


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

    def generate(self, prompt: str, **kwargs) -> str:
        """Gemini API 호출"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Gemini API 오류: {e}")
            raise

    def analyze(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """에이전트별 분석 메서드 (서브클래스에서 구현)"""
        raise NotImplementedError("서브클래스에서 analyze()를 구현해야 합니다")
