"""Telegram 알림 전송

OpenClaw message 기능을 사용하여 Telegram으로 알림 전송
"""
import logging
import subprocess
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger("marketsense")


class TelegramNotifier:
    """Telegram 알림 전송"""

    def __init__(self, channel: str = "telegram", target: Optional[str] = None):
        """
        Args:
            channel: OpenClaw 채널 (기본: telegram)
            target: 수신자 (채널 ID, username, 또는 None)
                   예: "-1001234567890" (채널 ID)
                   예: "@marketsense_alerts" (username)
                   예: None (현재 대화)
        """
        self.channel = channel
        
        # 환경변수에서 채널 읽기 (target이 None일 때만)
        if target is None:
            target = os.getenv("TELEGRAM_ALERT_CHANNEL")
        
        self.target = target
        
        if self.target:
            logger.info(f"[Telegram] 알림 채널: {self.target}")
        else:
            logger.info(f"[Telegram] 현재 대화로 전송")

    def send(self, message: str, silent: bool = False) -> bool:
        """메시지 전송
        
        Args:
            message: 전송할 메시지
            silent: 무음 알림 여부
            
        Returns:
            성공 여부
        """
        try:
            # OpenClaw CLI로 메시지 전송
            cmd = ["openclaw", "message", "send"]
            
            # 채널 지정
            if self.target:
                cmd.extend(["--target", self.target])
            
            # 무음 알림
            if silent:
                cmd.append("--silent")
            
            # 메시지 추가
            cmd.extend(["--message", message])
            
            # 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logger.info(f"[Telegram] 알림 전송 성공")
                return True
            else:
                logger.error(f"[Telegram] 알림 전송 실패: {result.stderr}")
                # 실패해도 콘솔 출력
                print(f"\n[알림 메시지]\n{message}\n")
                return False
                
        except Exception as e:
            logger.error(f"[Telegram] 알림 전송 오류: {e}")
            # 오류 시 콘솔 출력
            print(f"\n[알림 메시지]\n{message}\n")
            return False
    
    def send_to_user(self, chat_id: str, message: str, silent: bool = False) -> bool:
        """특정 사용자에게 메시지 전송
        
        Args:
            chat_id: 텔레그램 chat ID
            message: 전송할 메시지
            silent: 무음 알림 여부
            
        Returns:
            성공 여부
        """
        try:
            # OpenClaw CLI로 메시지 전송
            cmd = ["openclaw", "message", "send", "--target", chat_id]
            
            # 무음 알림
            if silent:
                cmd.append("--silent")
            
            # 메시지 추가
            cmd.extend(["--message", message])
            
            # 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logger.info(f"[Telegram] 사용자({chat_id}) 전송 성공")
                return True
            else:
                logger.error(f"[Telegram] 사용자({chat_id}) 전송 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"[Telegram] 사용자({chat_id}) 전송 오류: {e}")
            return False

    def send_signal_alert(self, ticker: str, stock_name: str, signal: str, 
                         confidence: float, reasons: dict) -> bool:
        """투자 신호 알림
        
        Args:
            ticker: 종목 코드
            stock_name: 종목명
            signal: BUY/SELL/HOLD
            confidence: 신뢰도 (0~1)
            reasons: 각 에이전트별 분석 결과
        """
        # 한글 번역 맵
        signal_kr = {
            "BUY": "매수",
            "SELL": "매도",
            "HOLD": "보유"
        }
        
        sentiment_kr = {
            "POSITIVE": "긍정적",
            "NEGATIVE": "부정적",
            "NEUTRAL": "중립",
            "N/A": "분석불가"
        }
        
        valuation_kr = {
            "UNDERVALUED": "저평가",
            "OVERVALUED": "고평가",
            "FAIR": "적정가",
            "STRONG": "우수",
            "STABLE": "안정적",
            "GOOD": "양호",
            "N/A": "분석불가"
        }
        
        trend_kr = {
            "UPTREND": "상승추세",
            "DOWNTREND": "하락추세",
            "RANGING": "횡보",
            "CONSOLIDATION": "조정",
            "STRONG BUY": "강한 매수세",
            "N/A": "분석불가"
        }
        
        impact_kr = {
            "POSITIVE": "긍정적",
            "NEGATIVE": "부정적",
            "NEUTRAL": "중립",
            "N/A": "분석불가"
        }
        
        emoji_map = {
            "BUY": "🚀",
            "SELL": "⚠️",
            "HOLD": "📊"
        }
        
        emoji = emoji_map.get(signal, "📊")
        signal_text = signal_kr.get(signal, signal)
        
        message = f"""
{emoji} **{signal_text} 신호!**

**종목**: {stock_name} ({ticker})
**신호**: {signal_text}
**신뢰도**: {confidence * 100:.0f}%

**AI 분석**:
"""
        
        # 각 에이전트 결과 추가 (한글로)
        if "news" in reasons:
            news = reasons["news"]
            sentiment = news.get('sentiment', 'N/A').upper()
            sentiment_text = sentiment_kr.get(sentiment, sentiment)
            message += f"📰 뉴스: {sentiment_text}\n"
            
        if "fundamentals" in reasons:
            fund = reasons["fundamentals"]
            valuation = fund.get('valuation', 'N/A').upper()
            valuation_text = valuation_kr.get(valuation, valuation)
            message += f"💰 재무: {valuation_text}\n"
            
        if "dynamics" in reasons:
            dyn = reasons["dynamics"]
            trend = dyn.get('trend', 'N/A').upper()
            trend_text = trend_kr.get(trend, trend)
            message += f"📈 기술: {trend_text}\n"
            
        if "macro" in reasons:
            macro = reasons["macro"]
            impact = macro.get('impact', 'N/A').upper()
            impact_text = impact_kr.get(impact, impact)
            message += f"🌍 매크로: {impact_text}\n"
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return self.send(message)

    def send_daily_report(self, top_signals: list, market_summary: dict) -> bool:
        """일일 시장 리포트
        
        Args:
            top_signals: 상위 신호 리스트 [(ticker, name, signal, confidence), ...]
            market_summary: 시장 요약 {'kospi': ..., 'kosdaq': ..., 'macro_analysis': {...}}
        """
        signal_kr = {
            "BUY": "매수",
            "SELL": "매도",
            "HOLD": "보유"
        }
        
        message = f"""
📊 **MarketSenseAI 일일 리포트**

**시장 현황**:
KOSPI: {market_summary.get('kospi', 'N/A')}
KOSDAQ: {market_summary.get('kosdaq', 'N/A')}
"""
        
        # 거시경제 분석 추가
        macro = market_summary.get('macro_analysis')
        if macro and not macro.get('error'):
            outlook_emoji = {
                'bullish': '📈',
                'bearish': '📉',
                'neutral': '➡️'
            }.get(macro.get('market_outlook', 'neutral'), '➡️')
            
            risk_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🔴'
            }.get(macro.get('risk_level', 'medium'), '🟡')
            
            message += f"""
**거시경제 전망**:
{outlook_emoji} 시장 전망: {macro.get('market_outlook', 'N/A').upper()}
{risk_emoji} 리스크: {macro.get('risk_level', 'N/A').upper()}
신뢰도: {macro.get('confidence', 0)*100:.0f}%

주요 요인:
"""
            for factor in macro.get('key_factors', [])[:3]:
                message += f"• {factor}\n"
            
            if macro.get('summary'):
                message += f"\n{macro.get('summary')}\n"
        
        message += "\n🔥 **오늘의 TOP 신호**:\n"
        
        for i, (ticker, name, signal, conf) in enumerate(top_signals[:5], 1):
            emoji = {"BUY": "🚀", "SELL": "⚠️", "HOLD": "📊"}.get(signal, "📊")
            signal_text = signal_kr.get(signal, signal)
            message += f"{i}. {name} ({ticker}) - {emoji} {signal_text} ({conf*100:.0f}%)\n"
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return self.send(message)

    def send_price_alert(self, ticker: str, stock_name: str, 
                        change_pct: float, volume_ratio: float) -> bool:
        """급등/급락 알림
        
        Args:
            ticker: 종목 코드
            stock_name: 종목명
            change_pct: 변동률 (%)
            volume_ratio: 거래량 비율 (평균 대비)
        """
        if change_pct > 0:
            emoji = "⚡"
            action = "급등"
        else:
            emoji = "🔻"
            action = "급락"
        
        message = f"""
{emoji} **{action} 감지!**

**종목**: {stock_name} ({ticker})
**변동**: {change_pct:+.1f}%
**거래량**: 평균 대비 {volume_ratio:.0f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        return self.send(message)

    def send_backtest_result(self, ticker: str, stock_name: str, 
                            strategy: str, result: dict) -> bool:
        """백테스팅 결과 알림
        
        Args:
            ticker: 종목 코드
            stock_name: 종목명
            strategy: 전략명
            result: 백테스팅 결과 딕셔너리
        """
        message = f"""
✅ **백테스팅 완료**

**종목**: {stock_name} ({ticker})
**전략**: {strategy}

**성과**:
📈 수익률: {result.get('return', 0)*100:+.1f}%
📊 샤프비율: {result.get('sharpe', 0):.2f}
📉 최대낙폭: {result.get('max_drawdown', 0)*100:.1f}%
🎯 승률: {result.get('win_rate', 0)*100:.0f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        return self.send(message)


# 전역 인스턴스
    def send_macro_report(self, macro_analysis: dict) -> bool:
        """거시경제 리포트 (매수 신호 없을 때)
        
        Args:
            macro_analysis: 거시경제 분석 결과
        """
        if macro_analysis.get('error'):
            return False
        
        outlook_emoji = {
            'bullish': '📈',
            'bearish': '📉',
            'neutral': '➡️'
        }.get(macro_analysis.get('market_outlook', 'neutral'), '➡️')
        
        risk_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }.get(macro_analysis.get('risk_level', 'medium'), '🟡')
        
        message = f"""
📊 **거시경제 분석 리포트**

{outlook_emoji} **시장 전망**: {macro_analysis.get('market_outlook', 'N/A').upper()}
{risk_emoji} **리스크 수준**: {macro_analysis.get('risk_level', 'N/A').upper()}
📊 **신뢰도**: {macro_analysis.get('confidence', 0)*100:.0f}%

**주요 요인**:
"""
        
        for factor in macro_analysis.get('key_factors', []):
            message += f"• {factor}\n"
        
        if macro_analysis.get('summary'):
            message += f"\n**요약**:\n{macro_analysis.get('summary')}\n"
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        message += "\n\n*오늘은 매수 신호가 없습니다*"
        
        return self.send(message)


_notifier = None


def get_notifier() -> TelegramNotifier:
    """싱글톤 인스턴스 반환"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
