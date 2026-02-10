"""News Agent - 뉴스 분석 및 감성 분류

논문 Section 3.1: Enhanced News Analysis
- 뉴스 기사 수집 및 감성 분석
- 긍정/부정/중립 분류
- 주요 이벤트 추출
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .base_agent import BaseAgent
from src.storage.models import Stock, NewsArticle, DisclosureData, BlogPost

logger = logging.getLogger("marketsense")


class NewsAgent(BaseAgent):
    """뉴스 분석 에이전트"""

    SYSTEM_PROMPT = """당신은 베테랑 금융 뉴스 분석가입니다.

당신의 목표는 특정 기업에 대한 뉴스 흐름을 파악하고, 이를 하나의 일관된 '투자 서사(Narrative)'로 통합하는 것입니다.

━━━━━━━━━━━━━━━━━━━━━━
핵심 원칙:
━━━━━━━━━━━━━━━━━━━━━━

1. **실질적 영향에 집중**
   주가에 실질적인 영향을 미치는 중요 이벤트에 집중하십시오:
   - 실적 발표 (매출, 영업이익 증감)
   - 신제품 출시 / 신규 수주
   - M&A, 전략적 제휴
   - 규제 이슈, 소송
   - 경영진 변화
   - 배당, 자사주 매입
   
2. **서사 구축**
   단순 나열이 아닌, 사건의 흐름이 이어지도록 작성하십시오.
   "A가 발생했고, 이에 따라 B가 예상되며, C의 영향이 우려된다"
   
3. **시간 맥락 유지**
   - 최근 뉴스와 과거 맥락을 연결
   - 진행 중인 이슈는 계속 추적
   - 해결된 이슈는 결과 반영
   
4. **정보원 구분**
   - 공식 뉴스: 신뢰도 높음, 팩트 중심
   - 블로그/커뮤니티: 참고용, 시장 심리 파악
   - 공시 정보: 공식 발표, 최우선 고려
   
5. **투자자 관점**
   투자자가 빠르게 파악할 수 있는 간결한 분석을 제공하십시오.

━━━━━━━━━━━━━━━━━━━━━━
출력 형식 (JSON):
━━━━━━━━━━━━━━━━━━━━━━

{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.0-1.0,
  "impact": "high|medium|low",
  "narrative": "투자 서사 (2-3문단, 시간 흐름에 따른 핵심 스토리)",
  "key_events": [
    {
      "event": "이벤트 설명",
      "date": "YYYY-MM-DD",
      "impact": "긍정적|부정적|중립",
      "importance": "high|medium|low"
    }
  ],
  "summary": "한 줄 요약 (투자자 헤드라인)",
  "reasoning": "분석 근거 및 판단 논리"
}
"""

    def analyze(self, ticker: str, lookback_days: int = 7, use_rag: bool = True) -> Dict[str, Any]:
        """종목 뉴스 분석"""
        logger.info(f"[NewsAgent] {ticker} 뉴스 분석 시작 (최근 {lookback_days}일, RAG={use_rag})")

        with self.db.get_session() as session:
            # 종목 정보
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return {"error": f"종목 {ticker}를 찾을 수 없습니다"}

            # 최근 뉴스 가져오기
            cutoff = datetime.now() - timedelta(days=lookback_days)
            
            if use_rag:
                # 방법 1: 시간 윈도우 + RAG
                try:
                    from src.rag.vector_store import VectorStore
                    
                    # RAG 검색 (관련성 우선, 많이 가져옴)
                    vs = VectorStore()
                    
                    rag_results = vs.search_news(
                        query=f"{stock.name} 주가 실적 전망 분석",
                        ticker=ticker,
                        top_k=50  # 많이 가져온 후 시간 필터링
                    )
                    
                    # RAG 결과를 DB 객체로 매핑하고 시간 필터링
                    if rag_results:
                        rag_ids = [r['id'].replace('news_', '') for r in rag_results if r['id'].startswith('news_')]
                        
                        news_list = (
                            session.query(NewsArticle)
                            .filter(
                                NewsArticle.id.in_([int(i) for i in rag_ids if i.isdigit()]),
                                NewsArticle.published_at >= cutoff  # 시간 윈도우
                            )
                            .order_by(NewsArticle.published_at.desc())
                            .limit(20)  # 최종 20개
                            .all()
                        )
                        
                        logger.info(f"[NewsAgent] RAG 검색: {len(news_list)}개 (최근 {lookback_days}일)")
                    else:
                        news_list = []
                    
                    # RAG 결과 없으면 fallback
                    if not news_list:
                        logger.warning(f"[NewsAgent] RAG 결과 없음, SQL fallback")
                        use_rag = False
                
                except Exception as e:
                    logger.warning(f"[NewsAgent] RAG 실패 ({e}), SQL fallback")
                    use_rag = False
            
            if not use_rag:
                # Fallback: 기존 SQL 방식 (최신순)
                news_list = (
                    session.query(NewsArticle)
                    .filter(
                        NewsArticle.ticker == ticker,
                        NewsArticle.published_at >= cutoff,
                    )
                    .order_by(NewsArticle.published_at.desc())
                    .limit(20)
                    .all()
                )
                logger.info(f"[NewsAgent] SQL 검색: {len(news_list)}개")

            if not news_list:
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "news_count": 0,
                    "sentiment": "neutral",
                    "message": "최근 뉴스가 없습니다",
                }

            # 뉴스 요약
            news_texts = []
            for idx, news in enumerate(news_list[:10], 1):
                date_str = news.published_at.strftime("%Y-%m-%d") if news.published_at else "날짜 미상"
                news_texts.append(f"{idx}. [{date_str}] {news.title}")
                if news.summary:
                    news_texts.append(f"   요약: {news.summary[:150]}...")

            # 공시 정보 조회 (최근 30일)
            disclosure_cutoff = datetime.now() - timedelta(days=30)
            disclosure_list = (
                session.query(DisclosureData)
                .filter(
                    DisclosureData.stock_id == stock.id,
                    DisclosureData.rcept_dt >= disclosure_cutoff.date(),
                )
                .order_by(DisclosureData.rcept_dt.desc())
                .limit(10)
                .all()
            )
            
            disclosure_texts = []
            if disclosure_list:
                disclosure_texts.append("\n주요 공시 정보 (최근 30일):")
                for idx, disc in enumerate(disclosure_list, 1):
                    date_str = disc.rcept_dt.strftime("%Y-%m-%d")
                    disclosure_texts.append(
                        f"{idx}. [{date_str}] {disc.disclosure_type}: {disc.report_nm[:80]}"
                    )

            # 블로그 글 조회 (최근 7일)
            blog_list = (
                session.query(BlogPost)
                .filter(
                    BlogPost.stock_id == stock.id,
                    BlogPost.post_date >= cutoff.date(),
                )
                .order_by(BlogPost.quality_score.desc(), BlogPost.post_date.desc())
                .limit(10)
                .all()
            )
            
            blog_texts = []
            if blog_list:
                blog_texts.append("\n💬 블로그 투자 의견 (최근 7일, 개인 의견):")
                for idx, blog in enumerate(blog_list, 1):
                    date_str = blog.post_date.strftime("%Y-%m-%d")
                    blog_texts.append(
                        f"{idx}. [{date_str}] {blog.title[:60]} (by {blog.blogger_name})"
                    )
                    if blog.description:
                        blog_texts.append(f"   → {blog.description[:100]}...")

            # 이전 뉴스 서사 (있다면)
            previous_narrative = ""
            if stock.raw_data and isinstance(stock.raw_data, dict):
                previous_narrative = stock.raw_data.get('news_narrative', '')
            
            # Gemini로 분석
            prompt = f"""{self.SYSTEM_PROMPT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 분석 대상: {stock.name} ({ticker})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] 기존까지의 뉴스 요약 및 서사:
{previous_narrative if previous_narrative else "신규 분석 - 이전 서사 없음"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2] 최근 수집된 뉴스 ({len(news_list)}건, {lookback_days}일)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(news_texts)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[3] 공식 공시 정보 (최근 30일)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(disclosure_texts) if disclosure_texts else "공시 없음"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[4] 블로그/커뮤니티 의견 (참고용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 주의: 블로그는 개인 의견이므로 팩트 확인 필요

{chr(10).join(blog_texts) if blog_texts else "블로그 의견 없음"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 분석 지침:

1. **핵심 이벤트 식별**
   - 실적 발표, M&A, 신제품 등 주가 영향 이벤트에 집중
   - 공시 정보는 최우선으로 key_events에 포함
   - 단순 루머나 소문은 낮은 중요도로 처리

2. **서사 구축 (중요!)**
   - 기존 서사가 있다면, 새로운 뉴스를 통합하여 업데이트
   - 단순 나열이 아닌, 시간 흐름에 따른 스토리 작성
   - "A가 발생 → B로 이어짐 → C가 예상됨" 형식
   - 진행 중인 이슈는 계속 추적 (예: 소송, 프로젝트)

3. **정보원 신뢰도**
   - 공시 > 뉴스 > 블로그 순서
   - 블로그는 시장 심리 파악용, 낮은 가중치
   - 블로그만으로 sentiment 결정 금지

4. **투자자 관점**
   - 간결하고 명확한 narrative 작성
   - 투자자가 빠르게 파악할 수 있는 헤드라인 요약
   - 모호한 표현 지양, 구체적인 팩트 중심

위 지침에 따라 **마크다운 형식**으로 분석 결과를 작성하세요.

반드시 다음 정보를 포함하되, 자유로운 형식으로 작성하십시오:
- 투자 서사 (시간 흐름에 따른 스토리)
- 핵심 이벤트 (날짜와 함께)
- 투자자 헤드라인 요약
- 감성 평가 (긍정/부정/중립)

**중요: 전체 분석을 300자 이내로 간결하게 작성하세요.**
핵심만 추려서 명확하고 간결한 투자 서사를 작성하십시오.

**금지: JSON 형식을 절대 사용하지 마세요. 순수 텍스트로만 작성하십시오.**

마크다운 헤더(##, ###)와 강조(**bold**)를 적극 활용하세요.
"""

            try:
                response_text = self.generate(prompt)
                
                # 텍스트 응답을 그대로 사용
                # 간단한 패턴 매칭으로 sentiment 추출
                sentiment = "neutral"
                if any(word in response_text.lower() for word in ["긍정", "positive", "호재", "상승"]):
                    sentiment = "positive"
                elif any(word in response_text.lower() for word in ["부정", "negative", "악재", "하락"]):
                    sentiment = "negative"
                
                # 투자 서사 저장 (전체 텍스트의 일부)
                narrative = response_text[:500] if len(response_text) > 500 else response_text
                
                if not stock.raw_data:
                    stock.raw_data = {}
                stock.raw_data['news_narrative'] = narrative
                stock.raw_data['news_updated_at'] = datetime.now().isoformat()
                session.commit()

                result = {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "news_count": len(news_list),
                    "sentiment": sentiment,
                    "confidence": 0.75,  # 기본값
                    "summary": response_text,  # 전체 마크다운 텍스트
                    "analyzed_at": datetime.now().isoformat()
                }

                logger.info(
                    f"[NewsAgent] {ticker} 분석 완료: {sentiment}"
                )

                return result

            except Exception as e:
                logger.error(f"[NewsAgent] {ticker} 분석 실패: {e}")
                return {
                    "ticker": ticker,
                    "stock_name": stock.name,
                    "news_count": len(news_list),
                    "error": str(e),
                }
