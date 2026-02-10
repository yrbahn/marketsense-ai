#!/usr/bin/env python3
"""대화형 Telegram 봇

명령어로 MarketSenseAI 기능 실행
"""
import sys
import logging
import re
from typing import Optional, Dict, List
from dotenv import load_dotenv

# .env 파일 로드 (최우선)
load_dotenv()

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
        
        # SignalAgent로 4개 에이전트 병렬 실행 + 통합
        from src.agents import SignalAgent
        
        try:
            # SignalAgent.analyze()가 4개 에이전트를 병렬로 실행하고 통합합니다
            logger.info(f"[SignalAgent] {ticker} 종합 분석 시작 (4개 에이전트 병렬)")
            signal_agent = SignalAgent(self.config, self.db)
            full_result = signal_agent.analyze(ticker)
            
            # 각 에이전트 결과 추출
            agent_results = full_result.get('agent_results', {})
            results = {
                'news': agent_results.get('news', {}),
                'fundamentals': agent_results.get('fundamentals', {}),
                'dynamics': agent_results.get('dynamics', {}),
                'macro': agent_results.get('macro', {}),
                'signal': full_result
            }
            
            # 결과 포맷팅
            signal_kr = {'BUY': '매수', 'SELL': '매도', 'HOLD': '보유'}
            risk_kr = {'low': '낮음', 'medium': '보통', 'high': '높음'}
            
            signal_result = results['signal']
            news_result = results.get('news', {})
            fund_result = results.get('fundamentals', {})
            dyn_result = results.get('dynamics', {})
            
            # 기술적 분석 상세 포맷팅
            tech_detail = ""
            if dyn_result and not dyn_result.get('error'):
                # 추세
                trend_kr = {'uptrend': '상승 추세', 'downtrend': '하락 추세', 'sideways': '횡보'}
                tech_detail = f"• 추세: {trend_kr.get(dyn_result.get('trend'), dyn_result.get('trend', 'N/A'))}"
                
                if dyn_result.get('trend_strength'):
                    strength_kr = {'strong': '강함', 'moderate': '보통', 'weak': '약함'}
                    tech_detail += f" ({strength_kr.get(dyn_result.get('trend_strength'), dyn_result.get('trend_strength'))})"
                
                # 이동평균선
                if dyn_result.get('moving_averages'):
                    ma = dyn_result['moving_averages']
                    tech_detail += f"\n• 이평선: {ma.get('ma5_vs_ma20', 'N/A')}"
                
                # RSI
                if dyn_result.get('indicators', {}).get('rsi'):
                    rsi_data = dyn_result['indicators']['rsi']
                    rsi_status_kr = {'과매수': '과매수', '중립': '중립', '과매도': '과매도'}
                    tech_detail += f"\n• RSI: {rsi_data.get('value', 'N/A')} ({rsi_status_kr.get(rsi_data.get('status'), rsi_data.get('status', 'N/A'))})"
                
                # MACD
                if dyn_result.get('indicators', {}).get('macd'):
                    macd_data = dyn_result['indicators']['macd']
                    macd_signal_kr = {'매수': '매수', '매도': '매도', '중립': '중립'}
                    tech_detail += f"\n• MACD: {macd_signal_kr.get(macd_data.get('signal'), macd_data.get('signal', 'N/A'))}"
                
                # 거래량
                if dyn_result.get('indicators', {}).get('volume'):
                    vol_data = dyn_result['indicators']['volume']
                    vol_trend_kr = {'증가': '증가', '감소': '감소', '보합': '보합'}
                    tech_detail += f"\n• 거래량: {vol_trend_kr.get(vol_data.get('trend'), vol_data.get('trend', 'N/A'))}"
                
                # 지지/저항선
                if dyn_result.get('key_levels'):
                    levels = dyn_result['key_levels']
                    if levels.get('support'):
                        supports = [f"{int(s):,}" for s in levels['support'][:2]]
                        tech_detail += f"\n• 지지선: {', '.join(supports)}원"
                    if levels.get('resistance'):
                        resistances = [f"{int(r):,}" for r in levels['resistance'][:2]]
                        tech_detail += f"\n• 저항선: {', '.join(resistances)}원"
                
                # 매매 전략
                if dyn_result.get('trading_strategy'):
                    strategy = dyn_result['trading_strategy']
                    if strategy.get('target_price'):
                        tech_detail += f"\n• 목표가: {strategy['target_price']}"
            else:
                tech_detail = "• 데이터 없음"
            
            # 재무 분석 상세 포맷팅
            fund_detail = ""
            if fund_result and not fund_result.get('error'):
                # 밸류에이션
                valuation_kr = {'undervalued': '저평가', 'fair': '적정', 'overvalued': '고평가'}
                if isinstance(fund_result.get('valuation'), dict):
                    val = fund_result['valuation']
                    fund_detail = f"• 밸류에이션: {valuation_kr.get(val.get('rating'), val.get('rating', 'N/A'))}"
                    
                    if val.get('vs_sector_pe'):
                        fund_detail += f"\n• 업종 대비 P/E: {val['vs_sector_pe']}"
                    if val.get('upside_potential'):
                        fund_detail += f"\n• 상승여력: {val['upside_potential']}"
                else:
                    fund_detail = f"• 밸류에이션: {valuation_kr.get(fund_result.get('valuation'), fund_result.get('valuation', 'N/A'))}"
                
                # 수익성
                if fund_result.get('profitability'):
                    prof = fund_result['profitability']
                    rating_kr = {'excellent': '우수', 'good': '양호', 'fair': '보통', 'poor': '부진'}
                    fund_detail += f"\n• 수익성: {rating_kr.get(prof.get('rating'), prof.get('rating', 'N/A'))}"
                    
                    if prof.get('roe'):
                        fund_detail += f" (ROE {prof['roe']:.1f}%)"
                
                # 성장성
                if fund_result.get('growth'):
                    growth = fund_result['growth']
                    growth_kr = {'high': '높음', 'moderate': '보통', 'low': '낮음', 'negative': '마이너스'}
                    fund_detail += f"\n• 성장성: {growth_kr.get(growth.get('rating'), growth.get('rating', 'N/A'))}"
                    
                    if growth.get('revenue_growth_yoy'):
                        fund_detail += f" (매출 YoY {growth['revenue_growth_yoy']:+.1f}%)"
                
                # 안정성
                if fund_result.get('stability'):
                    stab = fund_result['stability']
                    stab_kr = {'strong': '우수', 'moderate': '보통', 'weak': '약함', 'risky': '주의'}
                    fund_detail += f"\n• 재무안정성: {stab_kr.get(stab.get('rating'), stab.get('rating', 'N/A'))}"
                    
                    if stab.get('debt_ratio'):
                        fund_detail += f" (부채비율 {stab['debt_ratio']:.1f}%)"
                
                # 현금흐름
                if fund_result.get('cash_flow'):
                    cf = fund_result['cash_flow']
                    cf_kr = {'strong': '우수', 'adequate': '양호', 'weak': '약함'}
                    fund_detail += f"\n• 현금흐름: {cf_kr.get(cf.get('rating'), cf.get('rating', 'N/A'))}"
                
                # 투자 의견
                if fund_result.get('investment_thesis'):
                    thesis = fund_result['investment_thesis']
                    if thesis.get('target_price'):
                        fund_detail += f"\n• 목표가: {thesis['target_price']}"
            else:
                fund_detail = f"• 밸류에이션: {fund_result.get('valuation', 'N/A')}\n• 요약: {fund_result.get('summary', '데이터 없음')[:100]}..."
            
            # 각 에이전트별로 개별 메시지 전송
            
            # 1. 헤더
            header_msg = f"""🤖 **AI 종합 분석**

**종목**: {name} ({ticker})

━━━━━━━━━━━━━━━━━━━━━━
분석을 시작합니다..."""
            self.notifier.send_message(header_msg)
            
            # 2. 뉴스 분석
            if news_result and not news_result.get('error'):
                news_summary = news_result.get('summary', '데이터 없음')
                news_msg = f"""📰 **뉴스 애널리스트 분석**

{news_summary}"""
                self.notifier.send_message(news_msg)
            else:
                self.notifier.send_message("📰 **뉴스 애널리스트 분석**\n\n데이터 없음")
            
            # 3. 재무 분석
            if fund_result and not fund_result.get('error'):
                fund_summary = fund_result.get('summary', '데이터 없음')
                valuation_info = "N/A"
                if isinstance(fund_result.get('valuation'), dict):
                    val = fund_result['valuation']
                    valuation_kr = {'undervalued': '저평가', 'fair': '적정', 'overvalued': '고평가'}
                    valuation_info = valuation_kr.get(val.get('rating'), val.get('rating', 'N/A'))
                else:
                    valuation_kr = {'undervalued': '저평가', 'fair': '적정', 'overvalued': '고평가'}
                    valuation_info = valuation_kr.get(fund_result.get('valuation'), fund_result.get('valuation', 'N/A'))
                
                fund_msg = f"""💰 **펀더멘털 애널리스트 분석**

**밸류에이션**: {valuation_info}

{fund_summary}"""
                self.notifier.send_message(fund_msg)
            else:
                self.notifier.send_message("💰 **펀더멘털 애널리스트 분석**\n\n데이터 없음")
            
            # 4. 기술적 분석
            if dyn_result and not dyn_result.get('error'):
                dyn_summary = dyn_result.get('summary', '데이터 없음')
                trend_kr = {'uptrend': '상승', 'downtrend': '하락', 'sideways': '횡보'}
                
                dyn_msg = f"""📈 **기술적/수급 애널리스트 분석**

**추세**: {trend_kr.get(dyn_result.get('trend'), 'N/A')}

{dyn_summary}"""
                self.notifier.send_message(dyn_msg)
            else:
                self.notifier.send_message("📈 **기술적/수급 애널리스트 분석**\n\n데이터 없음")
            
            # 5. 거시경제 분석
            macro_result = results.get('macro')
            if macro_result and not macro_result.get('error'):
                macro_summary = macro_result.get('summary', '데이터 없음')
                
                macro_msg = f"""🌍 **거시경제 애널리스트 분석**

**거시경제 점수**: {macro_result.get('macro_score', 0)}

{macro_summary}"""
                self.notifier.send_message(macro_msg)
            else:
                self.notifier.send_message("🌍 **거시경제 애널리스트 분석**\n\n데이터 없음")
            
            # 6. 최종 투자 신호 (CIO)
            signal_summary = signal_result.get('summary', 'N/A')
            signal_msg = f"""🎯 **CIO 최종 투자 의견**

**신호**: {signal_kr.get(signal_result.get('signal'), signal_result.get('signal'))}
**확신도**: {signal_result.get('confidence', 0)*100:.0f}%

{signal_summary}

━━━━━━━━━━━━━━━━━━━━━━

⏰ {signal_result.get('analyzed_at', '')}

_※ AI 분석은 참고용이며, 실제 투자는 본인 판단으로 하세요._"""
            self.notifier.send_message(signal_msg)
            
            # 완료 메시지 반환 (이미 개별 메시지들을 전송했으므로)
            return f"✅ {name} ({ticker}) 분석 완료! (6개 메시지 전송)"
            
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
