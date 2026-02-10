#!/usr/bin/env python3
"""Telegram 알림 테스트"""
from src.notifications.telegram_notifier import get_notifier

notifier = get_notifier()

# 1. 간단한 메시지
print("1. 간단한 메시지 전송...")
notifier.send("🧪 MarketSenseAI 알림 봇 테스트\n\n시스템이 정상 작동합니다!")

# 2. 투자 신호 알림
print("2. 투자 신호 알림 전송...")
notifier.send_signal_alert(
    ticker="005930",
    stock_name="삼성전자",
    signal="BUY",
    confidence=0.85,
    reasons={
        "news": {"sentiment": "positive"},
        "fundamentals": {"valuation": "undervalued"},
        "dynamics": {"trend": "uptrend"}
    }
)

# 3. 급등 알림
print("3. 급등 알림 전송...")
notifier.send_price_alert(
    ticker="000660",
    stock_name="SK하이닉스",
    change_pct=8.5,
    volume_ratio=320
)

print("\n✅ 테스트 완료! Telegram을 확인하세요.")
