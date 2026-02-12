# 📊 MarketSenseAI 2.0 - 한국 증시 AI 분석 플랫폼

> **논문 기반 구현**: [MarketSenseAI 2.0: Enhancing Stock Analysis through LLM Agents](https://arxiv.org/abs/2502.00415)  
> **한국 증시 완전 특화**: KRX 2,884종목 (KOSPI + KOSDAQ + KONEX)  
> **5개 AI 에이전트 + 백테스팅 + 포트폴리오 최적화**

LLM 멀티 에이전트 시스템으로 한국 주식 시장을 분석하는 **완전한 AI 투자 플랫폼**입니다. 뉴스 감성, 재무 건전성, 기술적 분석, 거시경제를 종합하여 투자 신호를 생성하고, 백테스팅과 포트폴리오 최적화까지 제공합니다.

## 🎯 핵심 기능

### ✅ 5개 AI 에이전트 (Google Gemini)
- **NewsAgent**: 뉴스 감성 분석 (긍정/중립/부정 + 신뢰도) + 공시 정보
- **FundamentalsAgent**: 재무 건전성 평가 (밸류에이션/수익성/성장성/안정성)
  - **4분기 재무 지표 가로 배치**: 모든 지표를 4분기 연속으로 표시하여 추세 파악 용이 🆕
  - **15개 재무 지표**: 손익계산서(5) + 재무상태표(4) + 현금흐름표(4) + 수익성(2)
  - **자동 YoY/QoQ 계산**: 전년 동기 대비, 전분기 대비 증감률 자동 산출
  - **추세 판단**: 상승/하락/횡보 자동 분석
- **DynamicsAgent**: 기술적 분석 (추세/지지저항/모멘텀/RSI/MACD) + **수급 분석 (8개 지표)** 🆕
- **MacroAgent**: 거시경제 영향 분석 (금리/환율/GDP/인플레이션)
- **SignalAgent**: 최종 투자 신호 통합 (**BUY/SELL/HOLD** + 신뢰도)

### ✅ 수급 분석 시스템 (8개 지표) 🆕
- **네이버 증권 API** (2개):
  - 거래량
  - 외국인 보유율
- **한국투자증권 OpenAPI** (6개):
  - 개인 순매수
  - 외국인 순매수
  - 기관 순매수
  - 융자잔고 (신용매수)
  - 대주잔고 (신용매도)
  - 공매도 (수량 + 비중)
- **AI 분석**: 5-10일 추세 분석, 과열 감지, 종합 수급 시그널

### ✅ 백테스팅 엔진 (7개 전략)
- **Buy & Hold**: 기본 벤치마크
- **SMA Crossover**: 골든크로스/데드크로스
- **RSI**: 과매도/과매수
- **MACD**: 크로스오버
- **Bollinger Bands**: 상/하단 돌파
- **Momentum**: 20일 모멘텀
- **AI Signal**: 복합 지표 AI 스코어링

**성과 측정**: 수익률, 연간 수익률, 변동성, 샤프비율, 최대 낙폭(MDD), 승률, 거래 횟수

### ✅ 포트폴리오 최적화
- **샤프비율 최대화**: 리스크 대비 최고 수익 포트폴리오
- **최소 분산**: 변동성 최소화 포트폴리오
- **효율적 투자선**: Efficient Frontier 시뮬레이션
- **비중 제약**: 최소/최대 비중 설정 가능

### ✅ 한국 증시 전용 데이터 (100% 특화)
- **종목**: KRX 2,884개 (FinanceDataReader)
- **뉴스**: 네이버 증권 모바일 API (~20,000건)
- **재무제표**: DART 금융감독원 API (~18,000건)
- **주가**: FinanceDataReader (~700,000건)
- **수급 데이터**: 네이버 + 한국투자증권 KIS API (8개 지표) 🆕
  - 투자자별 매매 (개인/외국인/기관)
  - 공매도 수량 및 비중
  - 신용잔고 (융자/대주)
  - 외국인 보유율 및 거래량
- **공시 정보**: DART 전자공시 실시간 수집 🆕
- **기술지표**: SMA, RSI, MACD, Bollinger Bands, ATR 자동 계산

### ✅ 인프라
- **데이터베이스**: PostgreSQL 14 (동시 읽기/쓰기 지원)
- **대시보드**: Streamlit (데이터 시각화 + AI 분석)
- **자동화**: OpenClaw 크론 (매일 오후 4시 자동 업데이트)
- **CLI 도구**: 분석, 백테스팅, 포트폴리오 최적화

## 🚀 빠른 시작

### 1. 설치

```bash
git clone https://github.com/yrbahn/marketsense-ai.git
cd marketsense-ai
pip install -r requirements.txt
```

### 2. 환경 설정

`.env` 파일 생성:

```env
# Google Gemini API (필수)
GOOGLE_API_KEY=your-gemini-api-key

# DART API (필수 - 재무제표)
DART_API_KEY=your-dart-api-key

# 한국투자증권 KIS OpenAPI (필수 - 수급 데이터) 🆕
KIS_APP_KEY=your-kis-app-key
KIS_APP_SECRET=your-kis-app-secret
KIS_MOCK=false

# 네이버 검색 API (선택 - 뉴스 확장)
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret

# BOK API (선택 - 매크로)
BOK_API_KEY=your-bok-api-key
```

**API 키 발급:**
- **Gemini**: [Google AI Studio](https://aistudio.google.com/app/apikey) (무료)
- **DART**: [DART 오픈API](https://opendart.fss.or.kr/) (무료, 즉시 발급)
- **KIS OpenAPI**: [한국투자증권 API Portal](https://apiportal.koreainvestment.com/) (무료, 계좌 필요 없음) 🆕
- **네이버 검색**: [Naver Developers](https://developers.naver.com/) (무료)
- **BOK**: [한국은행 경제통계시스템](https://ecos.bok.or.kr/) (선택)

### 3. 데이터베이스 초기화

**PostgreSQL 설정:**
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14
createdb marketsense

# Linux (Ubuntu/Debian)
sudo apt install postgresql-14
sudo systemctl start postgresql
sudo -u postgres createdb marketsense
```

**config.yaml 수정:**
```yaml
database:
  url: "postgresql://your-username@localhost:5432/marketsense"
```

### 4. 종목 초기화

```bash
# 전체 KRX 종목 (2,884개)
python3 -m src.init_krx

# 시총 상위 1,000개만
python3 -m src.init_krx --top 1000
```

### 5. 데이터 수집

```bash
# 주요 50개 종목 (빠른 시작)
bash scripts/collect_top100.sh

# 시총 상위 1,000개
bash scripts/collect_1000.sh

# 전체 2,884개 (오래 걸림)
bash scripts/collect_all_remaining.sh
bash scripts/collect_all_fundamentals.sh
```

## 📊 사용법

### AI 종목 분석

```bash
# 개별 에이전트
python3 -m src.analyze --ticker 005930 --agent news
python3 -m src.analyze --ticker 005930 --agent fundamentals
python3 -m src.analyze --ticker 005930 --agent dynamics

# 종합 분석 (5개 에이전트 통합)
python3 -m src.analyze --ticker 005930
```

**출력 예시:**
```json
{
  "ticker": "005930",
  "stock_name": "삼성전자",
  "signal": "BUY",
  "confidence": 0.85,
  "risk_level": "medium",
  "agents": {
    "news": {"sentiment": "positive", "confidence": 0.8},
    "fundamentals": {"valuation": "undervalued", "confidence": 0.9},
    "dynamics": {"trend": "uptrend", "confidence": 0.75},
    "macro": {"impact": "positive", "confidence": 0.7}
  },
  "summary": "메모리 업황 회복 + 실적 개선으로 강한 매수 신호"
}
```

### 백테스팅

**단일 전략:**
```bash
# Buy & Hold (벤치마크)
python3 -m src.run_backtest --ticker 005930 --years 1

# 특정 전략
python3 -m src.run_backtest --ticker 005930 --strategy sma_crossover --years 2
python3 -m src.run_backtest --ticker 000660 --strategy ai_signal --years 1
```

**전략 비교:**
```bash
# 모든 전략 한 번에 비교
python3 -m src.run_backtest --ticker 005930 --compare-strategies --years 1
```

**실제 결과 (삼성전자 1년):**
```
전략                  수익률    샤프비율   최대손실   거래횟수
────────────────────────────────────────────────────────
Buy & Hold          +205.2%     5.31     -14.7%      1회
AI Signal           +180.2%     4.96     -14.6%      3회
SMA Crossover       +175.1%     4.65     -14.6%      3회
Momentum            +132.9%     3.64     -16.3%      5회
MACD                 +76.2%     2.47     -13.2%     22회
Bollinger Bands       +8.1%     1.20      -0.8%      2회
RSI                   +0.0%     0.00       0.0%      0회
```

**JSON 저장:**
```bash
python3 -m src.run_backtest --ticker 005930 --compare-strategies \
  --years 1 --output backtest_results.json
```

### 포트폴리오 최적화

**샤프비율 최대화:**
```bash
# 시총 상위 50개로 최적 포트폴리오
python3 -m src.optimize_portfolio --top 50

# 특정 종목들
python3 -m src.optimize_portfolio --tickers 005930 000660 035420 005380
```

**비중 제약:**
```bash
# 각 종목 5~20%만 허용 (분산 투자)
python3 -m src.optimize_portfolio --top 20 --min-weight 0.05 --max-weight 0.2
```

**최소 분산 포트폴리오:**
```bash
# 변동성 최소화 (안정 중시)
python3 -m src.optimize_portfolio --top 30 --method min_variance
```

**출력 예시:**
```
============================================================
📊 포트폴리오 최적화 결과
============================================================

💰 포트폴리오 통계:
  기대 수익률: 133.99% (연간)
  변동성:      36.61% (연간)
  샤프비율:    3.564

📊 종목별 비중:
  005930   44.96%  ██████████████████████
  000660   31.09%  ███████████████
  005380   23.95%  ███████████
```

### Streamlit 대시보드

```bash
streamlit run src/dashboard.py
```

**기능:**
- 📊 **데이터 대시보드**: 뉴스/재무/주가 시각화
- 🤖 **AI 분석**: 5개 에이전트 실시간 실행
- 📈 **종합 분석**: 최종 투자 신호 확인

### ⚡ 준실시간 주가 모니터링

**계좌 없이 실시간 급등/급락 알림!**

**기본 실행** (주요 10개 종목, 5초 주기):
```bash
python3 -m src.realtime_monitor
```

**특정 종목 감시:**
```bash
# 삼성전자, SK하이닉스
python3 -m src.realtime_monitor --tickers 005930 000660 --interval 3

# 시총 상위 50개
python3 -m src.realtime_monitor --top 50 --interval 5
```

**급변동 기준 조정:**
```bash
# ±1% 변동 시 알림 (민감)
python3 -m src.realtime_monitor --threshold 1.0

# ±5% 변동 시 알림 (둔감)
python3 -m src.realtime_monitor --threshold 5.0
```

**백그라운드 실행:**
```bash
nohup python3 -m src.realtime_monitor --top 50 --interval 5 \
  > logs/realtime.log 2>&1 &
```

**옵션:**
- `--interval`: 체크 주기 (초, 기본: 5)
- `--threshold`: 급변동 기준 (%, 기본: 2.0)
- `--tickers`: 감시할 종목 코드
- `--top`: 시총 상위 N개 감시

**특징:**
- ✅ 증권 계좌 불필요
- ✅ 무료 사용
- ✅ Telegram 자동 알림
- ✅ 장중 (월~금 09:00-15:30) 실시간 작동

### 자동 업데이트 (OpenClaw)

**매일 오후 4시 자동 데이터 수집:**

```bash
# OpenClaw 크론 이미 설정됨
# 수동 실행:
bash scripts/daily_update.sh
```

**수집 내용:**
- 📰 뉴스 (최근 30일)
- 📈 주가 (최신 데이터)
- 💰 재무제표 (분기별)

### ⚡ 백그라운드 실행 (타임아웃 회피) 🆕

**장시간 실행 작업을 백그라운드로 실행하여 5분 타임아웃 회피:**

```bash
# 리포트 수집 (백그라운드)
bash scripts/collect_reports_bg.sh

# 블로그 수집 (백그라운드)
bash scripts/collect_blogs_bg.sh

# 수급 데이터 수집 (백그라운드)
bash scripts/collect_supply_demand_bg.sh

# 일일 리포트 생성 (백그라운드)
bash scripts/daily_report_bg.sh

# 로그 확인
tail -f logs/collect_reports_bg_*.log
```

**백그라운드 스크립트 특징:**
- ✅ `nohup` + `&`로 백그라운드 실행
- ✅ 5분 타임아웃 회피
- ✅ 로그 파일 자동 생성 (`logs/` 디렉토리)
- ✅ PID 파일로 프로세스 관리
- ✅ 완료 시 Telegram 알림 (설정 시)

### 🚀 성능 최적화 🆕

**병렬 처리 최적화:**
```python
# 동적 워커 수 설정 (CPU 코어 수 * 2, 최대 20)
import os
max_workers = min(os.cpu_count() * 2, 20)

# M2 Max (12코어) → 20 workers
# 분석 속도: 14분 → 7분 (50% 단축)
```

**LLM 응답 캐싱:**
```python
# 1일 TTL, MD5 해시 기반 캐싱
# 동일 프롬프트 재사용 시 API 호출 절감
# 예상 비용 절감: 60-80%
```

**RAG 검색 최적화:**
```python
# top_k 최적화: 10 → 5
# 토큰 사용량 감소, 응답 속도 향상
```

**재무 분석 최적화:**
```python
# 8분기 (2년) 재무 데이터로 충분한 추세 파악
# 더 많은 분기 = 더 많은 토큰 ≠ 더 나은 분석
# 최적 밸런스: 8분기
```

### 📱 Telegram 알림 봇

**실시간 투자 알림을 Telegram으로 받을 수 있습니다!**

#### 알림 타입

**1. 투자 신호 알림**
```
🚀 매수 신호!
종목: 삼성전자 (005930)
신호: BUY
신뢰도: 85%

AI 분석:
📰 뉴스: POSITIVE
💰 재무: UNDERVALUED
📈 기술: UPTREND
```

**2. 급등/급락 알림**
```
⚡ 급등 감지!
종목: SK하이닉스 (000660)
변동: +8.5%
거래량: 평균 대비 320% ↑
```

**3. 일일 시장 리포트** (매일 오후 4시)
```
📊 MarketSenseAI 일일 리포트

시장 현황:
KOSPI: +1.2% (2,750)

🔥 오늘의 TOP 신호:
1. 삼성전자 (005930) - 🚀 BUY (85%)
2. SK하이닉스 (000660) - 🚀 BUY (82%)
...
```

#### 사용법

**테스트 알림:**
```bash
python3 test_notification.py
```

**새 채널로 알림 보내기:**

1. **Telegram에서 채널 생성**
   ```
   Telegram → New Channel → 
   - 채널명: "MarketSenseAI 알림"
   - Public 설정
   - Username: @marketsense_alerts
   ```

2. **.env 파일에 채널 설정**
   ```bash
   # .env 파일 수정
   TELEGRAM_ALERT_CHANNEL=@marketsense_alerts
   
   # 또는 채널 ID 사용
   # TELEGRAM_ALERT_CHANNEL=-1001234567890
   ```

3. **테스트**
   ```bash
   # 환경변수 채널로 전송
   python3 test_notification.py
   
   # 또는 직접 지정
   python3 test_notification.py --channel @marketsense_alerts
   ```

**일일 리포트 (수동):**
```bash
python3 src/daily_report.py
```

**급등/급락 모니터링 (백그라운드):**
```bash
nohup python3 src/monitor.py > logs/monitor.log 2>&1 &
```

**자동화 (OpenClaw 크론):**
```bash
# 매일 오후 4시 자동 리포트
openclaw cron add \
  --name "MarketSenseAI 일일 리포트" \
  --schedule "0 16 * * 1-5" \
  --session isolated \
  --delivery announce \
  --task "cd /path/to/marketsense-ai && python3 src/daily_report.py"
```

**상세 가이드:** [docs/AUTOMATION.md](docs/AUTOMATION.md)

## 🏗️ 프로젝트 구조

```
marketsense-ai/
├── README.md
├── requirements.txt
├── .env                     # API 키 설정
├── config/
│   └── config.yaml          # 전체 설정
├── src/
│   ├── init_krx.py          # KRX 종목 초기화
│   ├── pipeline.py          # 데이터 수집 파이프라인
│   ├── analyze.py           # AI 분석 CLI
│   ├── run_backtest.py      # 백테스팅 CLI
│   ├── optimize_portfolio.py # 포트폴리오 최적화 CLI
│   ├── daily_report.py      # 일일 시장 리포트
│   ├── monitor.py           # 급등/급락 모니터링
│   ├── dashboard.py         # Streamlit 대시보드
│   ├── collectors/          # 데이터 수집기
│   │   ├── news_collector.py
│   │   ├── fundamentals_collector.py
│   │   ├── dynamics_collector.py
│   │   └── macro_collector.py
│   ├── agents/              # AI 에이전트
│   │   ├── news_agent.py
│   │   ├── fundamentals_agent.py
│   │   ├── dynamics_agent.py
│   │   ├── macro_agent.py
│   │   └── signal_agent.py
│   ├── notifications/       # Telegram 알림
│   │   └── telegram_notifier.py
│   ├── backtest/            # 백테스팅 엔진
│   │   ├── engine.py
│   │   ├── strategies.py
│   │   └── ai_strategy.py
│   ├── portfolio/           # 포트폴리오 최적화
│   │   └── optimizer.py
│   ├── storage/
│   │   ├── database.py      # PostgreSQL 연결
│   │   └── models.py        # SQLAlchemy 모델
│   └── utils/
│       ├── helpers.py
│       └── dart_client.py
├── scripts/
│   ├── check_status.sh      # 수집 상태 확인
│   ├── daily_update.sh      # 일일 업데이트
│   ├── collect_top100.sh    # 주요 50개 수집
│   ├── collect_1000.sh      # 1,000개 수집
│   └── collect_all_*.sh     # 전체 수집
└── data/
    └── (PostgreSQL에 저장)
```

## 🗄️ 데이터베이스 스키마

### PostgreSQL 테이블

| 테이블 | 설명 | 예상 행 수 |
|--------|------|-----------|
| `stocks` | KRX 종목 마스터 | 2,884 |
| `news_articles` | 네이버 증권 뉴스 | ~20,000 |
| `financial_statements` | DART 재무제표 | ~18,000 |
| `price_data` | 일별 OHLCV | ~700,000 |
| `technical_indicators` | 기술적 지표 | ~700,000 |
| `supply_demand_data` | 수급 데이터 (8개 지표) 🆕 | ~100,000 |
| `disclosure_data` | DART 공시 정보 🆕 | ~10,000 |
| `macro_reports` | 한국은행 보고서 | ~100 |
| `macro_indicators` | BOK 경제통계 | ~1,000 |
| `pipeline_runs` | 수집 이력 | ~100 |

### PostgreSQL 장점
- ✅ **동시 읽기/쓰기** 지원
- ✅ 백그라운드 수집 중에도 AI 분석 가능
- ✅ DB 잠금 없음
- ✅ 확장성 우수

## 📊 실제 성과

### AI 종합 분석 예시 (삼성전자)

```
📊 종합 분석 결과

신호: BUY (매수)
신뢰도: 85%

📰 뉴스: POSITIVE
   - 메모리 반도체 업황 회복
   - HBM3E 공급 확대
   - 신뢰도: 80%

💰 재무: UNDERVALUED
   - 영업이익 80% 증가 (QoQ)
   - 부채비율 30% (우수)
   - 신뢰도: 90%

📈 기술: UPTREND
   - 20일선 돌파
   - RSI 60 (강세)
   - 신뢰도: 75%

🔥 수급: POSITIVE (신규!) 🆕
   - 외국인 5일 순매수: +1.8M주
   - 기관 5일 순매수: +880K주
   - 공매도 비중: 2.21% (감소 중)
   - 신용잔고: 정상 수준
   - 종합: 긍정적

🌍 매크로: POSITIVE
   - 금리 인하 기대
   - 원화 약세 수혜
   - 신뢰도: 70%
```

### 백테스팅 성과 (삼성전자 1년)

**최고 성과: Buy & Hold**
- 수익률: **+205.2%**
- 샤프비율: **5.31**
- 최대 낙폭: -14.7%

**2위: AI Signal**
- 수익률: **+180.2%**
- 샤프비율: **4.96**
- 거래: 3회 (효율적)

### 포트폴리오 최적화 (상위 50개)

**샤프비율 최대화:**
- 기대 수익률: **134%**
- 변동성: **37%**
- 샤프비율: **3.56**
- 주요 비중: 삼성 45%, SK하이닉스 31%, 현대차 24%

## 🔮 로드맵

### ✅ 완료
- [x] 한국 증시 데이터 수집 (Naver, DART, FDR)
- [x] **수급 분석 시스템** (8개 지표: 투자자별 매매, 공매도, 신용잔고) 🆕
- [x] **한국투자증권 KIS OpenAPI 통합** (실시간 수급 데이터) 🆕
- [x] **DynamicsAgent 수급 분석 강화** (5-10일 추세, 과열 감지) 🆕
- [x] **공시 정보 수집** (DART 전자공시) 🆕
- [x] **4분기 재무 지표 가로 배치** (모든 지표 추세를 한눈에) 🆕
- [x] **재무 분석 강화** (15개 지표, YoY/QoQ 자동 계산, 추세 판단) 🆕
- [x] 5개 AI 에이전트 구현 (Google Gemini)
- [x] **백테스팅 엔진** (7개 전략)
- [x] **포트폴리오 최적화** (Markowitz MPT)
- [x] **Telegram 알림 봇** (투자 신호, 급등/급락, 일일 리포트)
- [x] **준실시간 데이터 모니터링** (1~60초 주기, 계좌 불필요)
- [x] **RAG 파이프라인** (뉴스 벡터 DB, ChromaDB) 🆕
- [x] **백그라운드 실행 스크립트** (타임아웃 회피, 로그 관리) 🆕
- [x] **성능 최적화** (병렬 처리, LLM 캐싱, RAG 최적화) 🆕
- [x] Streamlit 대시보드
- [x] CLI 분석 도구
- [x] PostgreSQL 전환 (동시 쓰기)
- [x] 자동화 (OpenClaw cron)

### 🚧 개선 예정
- [ ] 재무제표 벡터 DB (RAG 확장)
- [ ] Discord 알림 봇
- [ ] 기관 세분화 (투신, 연기금, 은행, 보험 등)
- [ ] 추가 AI 전략 (강화학습)
- [ ] 대화형 Telegram 봇 (명령어 인터페이스)
- [ ] 실시간 WebSocket (증권사 API 연동)
- [ ] 12분기 (3년) 재무 데이터 옵션 (선택적 확장)
- [ ] 재무 비율 벤치마킹 (동종업계 평균 비교)

## 🎓 참고 논문

```bibtex
@article{fatouros2025marketsenseai,
  title={MarketSenseAI 2.0: Enhancing Stock Analysis through LLM Agents},
  author={Fatouros, George and Metaxas, Kostas},
  journal={arXiv preprint arXiv:2502.00415},
  year={2025}
}
```

## ⚠️ 면책 조항

- 본 프로젝트는 **연구 및 교육 목적**으로 제작되었습니다.
- AI 분석 결과는 참고용이며, **실제 투자 결정의 근거로 사용하지 마세요**.
- 투자로 인한 손실에 대해 개발자는 책임지지 않습니다.
- DART API 사용 시 [공공데이터 이용약관](https://www.data.go.kr/)을 준수하세요.

## 📄 라이선스

MIT License

## 🤝 기여

이슈 제보 및 PR 환영합니다!

- **GitHub**: [https://github.com/yrbahn/marketsense-ai](https://github.com/yrbahn/marketsense-ai)
- **문의**: yrbahn@gmail.com

---

**Made with ❤️ for Korean Stock Market**
