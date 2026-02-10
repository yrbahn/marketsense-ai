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
        emoji_map = {
            "BUY": "🚀",
            "SELL": "⚠️",
            "HOLD": "📊"
        }
        
        emoji = emoji_map.get(signal, "📊")
        
        message = f"""
{emoji} **{signal} 신호!**

**종목**: {stock_name} ({ticker})
**신호**: {signal}
**신뢰도**: {confidence * 100:.0f}%

**AI 분석**:
"""
        
        # 각 에이전트 결과 추가
        if "news" in reasons:
            news = reasons["news"]
            message += f"📰 뉴스: {news.get('sentiment', 'N/A').upper()}\n"
            
        if "fundamentals" in reasons:
            fund = reasons["fundamentals"]
            message += f"💰 재무: {fund.get('valuation', 'N/A').upper()}\n"
            
        if "dynamics" in reasons:
            dyn = reasons["dynamics"]
            message += f"📈 기술: {dyn.get('trend', 'N/A').upper()}\n"
            
        if "macro" in reasons:
            macro = reasons["macro"]
            message += f"🌍 매크로: {macro.get('impact', 'N/A').upper()}\n"
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return self.send(message)

    def send_daily_report(self, top_signals: list, market_summary: dict) -> bool:
        """일일 시장 리포트
        
        Args:
            top_signals: 상위 신호 리스트 [(ticker, name, signal, confidence), ...]
            market_summary: 시장 요약 {'kospi': ..., 'kosdaq': ...}
        """
        message = f"""
📊 **MarketSenseAI 일일 리포트**

**시장 현황**:
KOSPI: {market_summary.get('kospi', 'N/A')}
KOSDAQ: {market_summary.get('kosdaq', 'N/A')}

🔥 **오늘의 TOP 신호**:
"""
        
        for i, (ticker, name, signal, conf) in enumerate(top_signals[:5], 1):
            emoji = {"BUY": "🚀", "SELL": "⚠️", "HOLD": "📊"}.get(signal, "📊")
            message += f"{i}. {name} ({ticker}) - {emoji} {signal} ({conf*100:.0f}%)\n"
        
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
_notifier = None


def get_notifier() -> TelegramNotifier:
    """싱글톤 인스턴스 반환"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
