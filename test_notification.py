#!/usr/bin/env python3
"""Telegram 알림 테스트

환경변수 설정:
  export TELEGRAM_ALERT_CHANNEL="@channel_name"  # 또는 채널 ID

사용법:
  python3 test_notification.py
  python3 test_notification.py --channel @my_channel
"""
import sys
import os
from src.notifications.telegram_notifier import TelegramNotifier

# 명령행 인자로 채널 지정 가능
target = None
if len(sys.argv) > 2 and sys.argv[1] == "--channel":
    target = sys.argv[2]
    print(f"📱 타겟 채널: {target}")

notifier = TelegramNotifier(target=target)

# 1. 간단한 메시지
print("\n1. 간단한 메시지 전송...")
notifier.send("🧪 **MarketSenseAI 알림 봇 테스트**\n\n시스템이 정상 작동합니다! ✅")

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
print(f"📱 전송 채널: {target if target else '현재 대화'}")
