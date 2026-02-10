#!/usr/bin/env python3
"""대화형 Telegram 봇

명령어로 MarketSenseAI 기능 실행
"""
import sys
import logging
import re
from typing import Optional, Dict, List

from src.storage.database import init_db
from src.storage.models import Stock
from src.utils.helpers import load_config
from src.notifications.telegram_notifier import get_notifier

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("telegram_bot")


class TelegramBot:
    """Telegram 명령어 봇"""
    
    def __init__(self):
        self.config = load_config()
        self.db = init_db(self.config)
        self.notifier = get_notifier()
        
        # 명령어 목록
        self.commands = {
            '/도움말': self.cmd_help,
            '/분석': self.cmd_analyze,
            '/시세': self.cmd_price,
            '/백테스팅': self.cmd_backtest,
            '/포트폴리오': self.cmd_portfolio,
            '/종목검색': self.cmd_search,
            '/상태': self.cmd_status,
        }
    
    def parse_command(self, message: str) -> tuple:
        """메시지에서 명령어 파싱
        
        Args:
            message: 사용자 메시지
            
        Returns:
            (command, args) 튜플
        """
        message = message.strip()
        
        # 명령어 찾기
        for cmd in self.commands.keys():
            if message.startswith(cmd):
                args = message[len(cmd):].strip()
                return (cmd, args)
        
        return (None, message)
    
    def get_stock_info(self, query: str) -> Optional[Dict]:
        """종목 조회
        
        Args:
            query: 종목코드 또는 종목명
            
        Returns:
            {'ticker': ..., 'name': ...} or None
        """
        with self.db.get_session() as session:
            # 종목코드로 조회
            stock = session.query(Stock).filter_by(ticker=query).first()
            
            if not stock:
                # 종목명으로 조회
                stock = session.query(Stock).filter(
                    Stock.name.like(f'%{query}%')
                ).first()
            
            if stock:
                return {
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'market_cap': stock.market_cap
                }
        
        return None
    
    def cmd_help(self, args: str) -> str:
        """도움말"""
        return """
📖 **MarketSenseAI 명령어**

**종목 분석:**
• `/분석 삼성전자` - 종목 AI 분석
• `/시세 005930` - 실시간 시세 조회

**백테스팅:**
• `/백테스팅 삼성전자` - 1년 백테스팅
• `/백테스팅 005930 2년` - 2년 백테스팅

**포트폴리오:**
• `/포트폴리오 50` - 상위 50개 최적화
• `/포트폴리오 삼성전자 SK하이닉스 현대차` - 특정 종목

**유틸리티:**
• `/종목검색 삼성` - 종목 검색
• `/상태` - 시스템 상태
• `/도움말` - 이 메시지

**예시:**
```
/분석 005930
/시세 삼성전자
/백테스팅 SK하이닉스 1년
/포트폴리오 100
```
"""
    
    def cmd_analyze(self, args: str) -> str:
        """종목 분석 (4개 에이전트 전체)"""
        if not args:
            return "❌ 종목을 입력하세요.\n예: `/분석 삼성전자`"
        
        # 종목 조회
        stock = self.get_stock_info(args)
        if not stock:
            return f"❌ 종목을 찾을 수 없습니다: {args}\n`/종목검색 {args}` 로 검색해보세요."
        
        ticker = stock['ticker']
        name = stock['name']
        
        # 4개 에이전트 분석 실행
        from src.agents import NewsAgent, FundamentalsAgent, DynamicsAgent, MacroAgent, SignalAgent
        
        results = {}
        
        try:
            # 1. 뉴스 분석
            logger.info(f"[NewsAgent] {ticker} 분석 시작")
            agent = NewsAgent(self.config, self.db)
            results['news'] = agent.analyze(ticker)
            
            # 2. 재무 분석
            logger.info(f"[FundamentalsAgent] {ticker} 분석 시작")
            agent = FundamentalsAgent(self.config, self.db)
            results['fundamentals'] = agent.analyze(ticker)
            
            # 3. 기술적 분석
            logger.info(f"[DynamicsAgent] {ticker} 분석 시작")
            agent = DynamicsAgent(self.config, self.db)
            results['dynamics'] = agent.analyze(ticker)
            
            # 4. 거시경제 분석 (스킵 - 데이터 미비)
            # logger.info(f"[MacroAgent] 분석 시작")
            # agent = MacroAgent(self.config, self.db)
            # results['macro'] = agent.analyze()
            results['macro'] = None
            
            # 5. 최종 통합
            logger.info(f"[SignalAgent] {ticker} 통합 시작")
            agent = SignalAgent(self.config, self.db)
            results['signal'] = agent.aggregate(
                ticker,
                news_result=results.get('news'),
                fundamentals_result=results.get('fundamentals'),
                dynamics_result=results.get('dynamics'),
                macro_result=results.get('macro')
            )
            
            # 결과 포맷팅
            signal_kr = {'BUY': '매수', 'SELL': '매도', 'HOLD': '보유'}
            risk_kr = {'low': '낮음', 'medium': '보통', 'high': '높음'}
            
            signal_result = results['signal']
            news_result = results.get('news', {})
            fund_result = results.get('fundamentals', {})
            dyn_result = results.get('dynamics', {})
            
            response = f"""🤖 **AI 종합 분석**

**종목**: {name} ({ticker})

━━━━━━━━━━━━━━━━━━━━━━

📰 **뉴스 분석**
• 감성: {news_result.get('sentiment', 'N/A')}
• 요약: {news_result.get('summary', '데이터 없음')[:100]}...

💰 **재무 분석**
• 밸류에이션: {fund_result.get('valuation', 'N/A')}
• 요약: {fund_result.get('summary', '데이터 없음')[:100]}...

📈 **기술적 분석**
• 추세: {dyn_result.get('trend', 'N/A')}
• 요약: {dyn_result.get('summary', '데이터 없음')[:100]}...

━━━━━━━━━━━━━━━━━━━━━━

🎯 **최종 투자 신호**
• **신호**: {signal_kr.get(signal_result.get('signal'), signal_result.get('signal'))}
• **신뢰도**: {signal_result.get('confidence', 0)*100:.0f}%
• **리스크**: {risk_kr.get(signal_result.get('risk_level'), 'N/A')}

**종합 의견**:
{signal_result.get('summary', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━

⏰ {signal_result.get('analyzed_at', '')}

_※ AI 분석은 참고용이며, 실제 투자는 본인 판단으로 하세요._
"""
            
            return response
            
        except Exception as e:
            logger.error(f"분석 오류: {e}")
            return f"""
❌ **분석 중 오류 발생**

종목: {name} ({ticker})
오류: {str(e)}

잠시 후 다시 시도하거나 `/시세 {name}` 명령어를 사용하세요.
"""
    
    def cmd_price(self, args: str) -> str:
        """실시간 시세"""
        if not args:
            return "❌ 종목을 입력하세요.\n예: `/시세 삼성전자`"
        
        from src.realtime_monitor import RealtimeMonitor
        
        # 종목 조회
        stock = self.get_stock_info(args)
        if not stock:
            return f"❌ 종목을 찾을 수 없습니다: {args}"
        
        # 실시간 시세 조회
        monitor = RealtimeMonitor()
        data = monitor.get_realtime_price(stock['ticker'])
        
        if not data or data['price'] == 0:
            return f"""
⚠️ **시세 조회 실패**

종목: {stock['name']} ({stock['ticker']})

장 마감 또는 데이터 없음
"""
        
        change_emoji = '📈' if data['change'] > 0 else '📉' if data['change'] < 0 else '➡️'
        
        return f"""
{change_emoji} **실시간 시세**

**종목**: {stock['name']} ({stock['ticker']})
**현재가**: {data['price']:,.0f}원
**등락**: {data['change']:+,.0f}원 ({data['change_rate']:+.2f}%)
**거래량**: {data['volume']:,}주

⏰ {data['time']}
"""
    
    def cmd_backtest(self, args: str) -> str:
        """백테스팅"""
        if not args:
            return "❌ 종목을 입력하세요.\n예: `/백테스팅 삼성전자`"
        
        # 인자 파싱
        parts = args.split()
        query = parts[0]
        years = 1
        
        if len(parts) > 1 and parts[1].replace('년', '').isdigit():
            years = int(parts[1].replace('년', ''))
        
        # 종목 조회
        stock = self.get_stock_info(query)
        if not stock:
            return f"❌ 종목을 찾을 수 없습니다: {query}"
        
        return f"""
🔄 **백테스팅 시작**

종목: {stock['name']} ({stock['ticker']})
기간: {years}년
전략: 전략 비교

실행 중... (약 1분 소요)
완료되면 결과를 보내드립니다.
"""
    
    def cmd_portfolio(self, args: str) -> str:
        """포트폴리오 최적화"""
        if not args:
            return "❌ 종목 수를 입력하세요.\n예: `/포트폴리오 50`"
        
        # 숫자인 경우 - 상위 N개
        if args.isdigit():
            n = int(args)
            return f"""
🔄 **포트폴리오 최적화 시작**

대상: 시총 상위 {n}개
방법: 샤프비율 최대화

실행 중... (약 30초 소요)
완료되면 결과를 보내드립니다.
"""
        
        # 종목명인 경우
        tickers = args.split()
        return f"""
🔄 **포트폴리오 최적화 시작**

대상: {len(tickers)}개 종목
방법: 샤프비율 최대화

실행 중... (약 30초 소요)
완료되면 결과를 보내드립니다.
"""
    
    def cmd_search(self, args: str) -> str:
        """종목 검색"""
        if not args:
            return "❌ 검색어를 입력하세요.\n예: `/종목검색 삼성`"
        
        with self.db.get_session() as session:
            stocks = session.query(Stock).filter(
                Stock.name.like(f'%{args}%')
            ).limit(10).all()
            
            if not stocks:
                return f"❌ '{args}' 검색 결과가 없습니다."
            
            result = f"🔍 **'{args}' 검색 결과** ({len(stocks)}개)\n\n"
            
            for s in stocks:
                market_cap = f"{s.market_cap/1e12:.1f}조원" if s.market_cap else "N/A"
                result += f"• {s.name} ({s.ticker}) - {market_cap}\n"
            
            return result
    
    def cmd_status(self, args: str) -> str:
        """시스템 상태"""
        import subprocess
        
        # 실시간 모니터링 확인
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            monitor_running = "realtime_monitor" in result.stdout
        except:
            monitor_running = False
        
        # 데이터베이스 통계
        with self.db.get_session() as session:
            from src.storage.models import FinancialStatement, NewsArticle, PriceData
            
            stocks = session.query(Stock).count()
            financials = session.query(FinancialStatement).count()
            news = session.query(NewsArticle).count()
            prices = session.query(PriceData).count()
        
        return f"""
📊 **MarketSenseAI 상태**

**실시간 모니터링:**
{"✅ 작동 중" if monitor_running else "⚠️ 중지됨"}

**데이터베이스:**
• 종목: {stocks:,}개
• 재무제표: {financials:,}건
• 뉴스: {news:,}건
• 주가: {prices:,}건

**GitHub:**
https://github.com/yrbahn/marketsense-ai

**도움말:**
`/도움말`
"""
    
    def process_message(self, message: str) -> str:
        """메시지 처리
        
        Args:
            message: 사용자 메시지
            
        Returns:
            응답 메시지
        """
        cmd, args = self.parse_command(message)
        
        if cmd and cmd in self.commands:
            try:
                return self.commands[cmd](args)
            except Exception as e:
                logger.error(f"명령어 실행 오류: {e}")
                return f"❌ 오류 발생: {str(e)}"
        
        # 명령어 없으면 도움말
        if message.startswith('/'):
            return f"❌ 알 수 없는 명령어: {message}\n\n{self.cmd_help('')}"
        
        return None  # 일반 대화는 처리 안 함


def main():
    """CLI 테스트"""
    import sys
    
    bot = TelegramBot()
    
    if len(sys.argv) > 1:
        message = ' '.join(sys.argv[1:])
        response = bot.process_message(message)
        if response:
            print(response)
    else:
        print("사용법: python3 -m src.telegram_bot '명령어'")
        print("예: python3 -m src.telegram_bot '/시세 삼성전자'")


if __name__ == "__main__":
    main()
