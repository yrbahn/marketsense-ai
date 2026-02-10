# 자동화 설정 가이드

MarketSenseAI Telegram 알림 봇 자동화 설정

## OpenClaw 크론 작업

### 1. 일일 시장 리포트 (매일 오후 4시)

```bash
openclaw cron add \
  --name "MarketSenseAI 일일 리포트" \
  --schedule "0 16 * * 1-5" \
  --session isolated \
  --delivery announce \
  --task "cd /Users/yrbahn/.openclaw/workspace/marketsense-ai && python3 src/daily_report.py"
```

**설명:**
- **schedule**: 월~금 오후 4시 (장 마감 후)
- **session**: isolated (독립 실행)
- **delivery**: announce (결과를 현재 채널로 전송)
- **task**: 일일 리포트 스크립트 실행

### 2. 실시간 급등/급락 모니터링 (장중 5분마다)

**장 운영 시간만 실행하려면 별도 스크립트 필요**

```bash
# 임시로 수동 실행
cd /Users/yrbahn/.openclaw/workspace/marketsense-ai
python3 src/monitor.py
```

**백그라운드 실행:**
```bash
nohup python3 src/monitor.py > logs/monitor.log 2>&1 &
```

### 3. 데이터 수집 + 알림 (이미 설정됨)

기존 `daily_update.sh`에 알림 추가 가능

## Python 스크립트 직접 실행

### 일일 리포트

```bash
cd /Users/yrbahn/.openclaw/workspace/marketsense-ai
python3 src/daily_report.py
```

### 급등/급락 모니터링

```bash
python3 src/monitor.py
```

### 테스트 알림

```bash
python3 test_notification.py
```

## 알림 커스터마이징

`src/notifications/telegram_notifier.py` 수정:

```python
# 신뢰도 임계값 변경
if signal == "BUY" and confidence >= 0.8:  # 80% → 원하는 값

# 급등/급락 기준 변경
monitor = PriceMonitor(
    price_threshold=5.0,   # ±5% → 원하는 값
    volume_threshold=2.0   # 2배 → 원하는 값
)
```

## 로그 확인

```bash
# 일일 리포트 로그
tail -f logs/daily_report_*.log

# 모니터링 로그
tail -f logs/monitor.log

# 데이터 수집 로그
tail -f logs/collect_*.log
```

## 문제 해결

### "Telegram 전송 실패"

- OpenClaw 설정 확인
- Telegram 채널 연결 확인
- 로그 확인

### "AI 분석 실패"

- Gemini API 키 확인 (`.env`)
- 데이터베이스에 데이터 있는지 확인
- 로그에서 상세 오류 확인

### "모니터링이 멈춤"

- 프로세스 확인: `ps aux | grep monitor`
- 재시작: `python3 src/monitor.py`
