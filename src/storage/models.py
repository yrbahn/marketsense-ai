"""SQLAlchemy 데이터베이스 모델 - MarketSenseAI 데이터 파이프라인

4개 에이전트에 필요한 모든 raw 데이터를 저장하기 위한 테이블 정의:
1. News Agent: NewsArticle
2. Fundamentals Agent: FinancialStatement, SECFiling, EarningsCall
3. Dynamics Agent: PriceData, TechnicalIndicator
4. Macroeconomic Agent: MacroReport, MacroIndicator
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date,
    Boolean, ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ═══════════════════════════════════════════
# Core: Stock Universe
# ═══════════════════════════════════════════
class Stock(Base):
    """종목 마스터 테이블"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100))
    industry = Column(String(200))
    market_cap = Column(Float)
    index_membership = Column(String(50))  # SP100, SP500
    cik = Column(String(20))  # SEC CIK number
    is_active = Column(Boolean, default=True)
    raw_data = Column(JSON)  # 확장 데이터 (LLM 키워드 캐시 등)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    news = relationship("NewsArticle", back_populates="stock")
    financials = relationship("FinancialStatement", back_populates="stock")
    filings = relationship("SECFiling", back_populates="stock")
    earnings_calls = relationship("EarningsCall", back_populates="stock")
    prices = relationship("PriceData", back_populates="stock")
    indicators = relationship("TechnicalIndicator", back_populates="stock")


# ═══════════════════════════════════════════
# 1. News Agent Data
# ═══════════════════════════════════════════
class NewsArticle(Base):
    """금융 뉴스 기사"""
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("url", name="uq_news_url"),
        Index("ix_news_stock_date", "stock_id", "published_at"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True, index=True)
    ticker = Column(String(10), index=True)  # 여러 종목 관련 뉴스용

    title = Column(String(500), nullable=False)
    summary = Column(Text)
    content = Column(Text)  # 전체 기사 본문
    url = Column(String(1000), nullable=False)
    source = Column(String(100))  # finnhub, newsapi, rss
    author = Column(String(200))
    published_at = Column(DateTime, index=True)
    sentiment_raw = Column(Float)  # 원시 감성 점수 (있는 경우)

    # 메타데이터
    category = Column(String(100))
    related_tickers = Column(JSON)  # ["AAPL", "MSFT", ...]
    collected_at = Column(DateTime, default=datetime.utcnow)
    source_id = Column(String(200))  # 소스별 고유 ID

    stock = relationship("Stock", back_populates="news")


# ═══════════════════════════════════════════
# 2. Fundamentals Agent Data
# ═══════════════════════════════════════════
class FinancialStatement(Base):
    """재무제표 (Income Statement, Balance Sheet, Cash Flow)"""
    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint("stock_id", "statement_type", "period_end", "period_type",
                         name="uq_financial_stmt"),
        Index("ix_fin_stock_period", "stock_id", "period_end"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)

    statement_type = Column(String(50), nullable=False)  # income, balance_sheet, cash_flow
    period_type = Column(String(10), nullable=False)  # quarterly, annual
    period_end = Column(Date, nullable=False)
    fiscal_quarter = Column(String(10))  # Q1, Q2, Q3, Q4

    # Raw data as JSON (모든 항목 보존)
    raw_data = Column(JSON, nullable=False)

    # 주요 지표 (빠른 조회용)
    revenue = Column(Float)
    net_income = Column(Float)
    operating_income = Column(Float)
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)
    operating_cash_flow = Column(Float)
    free_cash_flow = Column(Float)
    eps = Column(Float)

    collected_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), default="yfinance")

    stock = relationship("Stock", back_populates="financials")


class SECFiling(Base):
    """SEC 공시 (10-K, 10-Q)"""
    __tablename__ = "sec_filings"
    __table_args__ = (
        UniqueConstraint("accession_number", name="uq_sec_accession"),
        Index("ix_sec_stock_type", "stock_id", "filing_type"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)

    filing_type = Column(String(20), nullable=False)  # 10-K, 10-Q
    accession_number = Column(String(50), nullable=False)
    filing_date = Column(Date, nullable=False, index=True)
    period_of_report = Column(Date)
    fiscal_year = Column(Integer)
    fiscal_quarter = Column(String(10))

    # 문서 내용
    raw_text = Column(Text)  # 전체 텍스트
    risk_factors = Column(Text)  # Item 1A
    md_and_a = Column(Text)  # Item 7 (MD&A)
    notes = Column(Text)  # 주석/공시
    file_url = Column(String(500))
    file_size_bytes = Column(Integer)

    # 처리 상태
    is_parsed = Column(Boolean, default=False)
    parsed_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="filings")


class EarningsCall(Base):
    """실적 발표 컨퍼런스 콜 트랜스크립트"""
    __tablename__ = "earnings_calls"
    __table_args__ = (
        UniqueConstraint("stock_id", "call_date", name="uq_earnings_call"),
        Index("ix_ec_stock_date", "stock_id", "call_date"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)

    call_date = Column(Date, nullable=False)
    fiscal_year = Column(Integer)
    fiscal_quarter = Column(String(10))  # Q1, Q2, Q3, Q4
    title = Column(String(500))

    # 트랜스크립트 내용
    prepared_remarks = Column(Text)  # 경영진 발표 부분
    qa_session = Column(Text)  # Q&A 세션
    full_transcript = Column(Text)  # 전체 트랜스크립트

    # 메타데이터
    participants = Column(JSON)  # 참석자 목록
    source = Column(String(50))  # rapidapi, seekingalpha
    source_url = Column(String(500))

    is_parsed = Column(Boolean, default=False)
    collected_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="earnings_calls")


# ═══════════════════════════════════════════
# 3. Dynamics Agent Data
# ═══════════════════════════════════════════
class PriceData(Base):
    """일별 주가 데이터"""
    __tablename__ = "price_data"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_price_date"),
        Index("ix_price_stock_date", "stock_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)

    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(Float)

    # 추가 정보
    dividend = Column(Float, default=0)
    stock_split = Column(Float, default=0)

    collected_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="prices")


class TechnicalIndicator(Base):
    """기술적 지표 (일별)"""
    __tablename__ = "technical_indicators"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_tech_date"),
        Index("ix_tech_stock_date", "stock_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)

    date = Column(Date, nullable=False)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr_14 = Column(Float)
    volume_sma_20 = Column(Float)

    # 수익률 & 리스크
    daily_return = Column(Float)
    volatility_20d = Column(Float)
    sharpe_ratio_20d = Column(Float)
    max_drawdown_20d = Column(Float)

    collected_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="indicators")


# ═══════════════════════════════════════════
# 4. Macroeconomic Agent Data
# ═══════════════════════════════════════════
class MacroReport(Base):
    """매크로 경제 보고서 (중앙은행, 투자은행, IMF 등)"""
    __tablename__ = "macro_reports"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_macro_url"),
        Index("ix_macro_source_date", "source_name", "published_at"),
    )

    id = Column(Integer, primary_key=True)

    title = Column(String(500), nullable=False)
    source_name = Column(String(100), nullable=False)  # fed, ecb, imf, jpmorgan, blackrock
    source_url = Column(String(1000))
    published_at = Column(DateTime, index=True)
    report_type = Column(String(100))  # speech, outlook, minutes, research

    # 내용
    raw_text = Column(Text)  # 원본 텍스트
    cleaned_text = Column(Text)  # 정제된 텍스트
    summary = Column(Text)  # LLM 요약 (선택)
    page_count = Column(Integer)
    file_path = Column(String(500))  # 로컬 파일 경로

    # 메타데이터
    author = Column(String(200))
    tags = Column(JSON)  # ["monetary_policy", "inflation", ...]
    is_relevant = Column(Boolean, default=True)  # LLM 필터 결과
    is_processed = Column(Boolean, default=False)

    collected_at = Column(DateTime, default=datetime.utcnow)


class MacroIndicator(Base):
    """매크로 경제 지표 시계열 (FRED 등)"""
    __tablename__ = "macro_indicators"
    __table_args__ = (
        UniqueConstraint("series_id", "date", name="uq_macro_ind_date"),
        Index("ix_macro_ind_series", "series_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    series_id = Column(String(50), nullable=False)  # GDP, CPIAUCSL, FEDFUNDS
    series_name = Column(String(200))
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50))
    frequency = Column(String(20))  # daily, monthly, quarterly
    source = Column(String(50), default="fred")

    collected_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════
# Supply & Demand Data (수급 데이터)
# ═══════════════════════════════════════════
class SupplyDemandData(Base):
    """수급 지표 (공매도, 신용잔고, 투자자별 매매)"""
    __tablename__ = "supply_demand_data"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_supply_demand_date"),
        Index("ix_supply_demand_stock_date", "stock_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # 공매도 (Short Selling)
    short_volume = Column(Float)          # 공매도 거래량
    short_amount = Column(Float)          # 공매도 거래대금
    short_balance = Column(Float)         # 공매도 잔량
    short_ratio = Column(Float)           # 공매도 비중 (%)
    
    # 신용거래 (Margin Trading)
    credit_buy_balance = Column(Float)    # 신용매수 잔고
    credit_sell_balance = Column(Float)   # 신용매도 잔고
    margin_balance = Column(Float)        # 융자 잔고
    margin_ratio = Column(Float)          # 신용잔고율 (%)
    
    # 투자자별 매매 (Investor Trading)
    foreign_net_buy = Column(Float)       # 외국인 순매수
    institution_net_buy = Column(Float)   # 기관 순매수
    individual_net_buy = Column(Float)    # 개인 순매수
    foreign_ownership = Column(Float)     # 외국인 보유비중 (%)
    
    # 거래량/대금
    volume = Column(Float)                # 거래량
    trading_value = Column(Float)         # 거래대금
    
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    stock = relationship("Stock")


# ═══════════════════════════════════════════
# Disclosure Data (공시 정보)
# ═══════════════════════════════════════════
class DisclosureData(Base):
    """DART 공시 정보"""
    __tablename__ = "disclosure_data"
    __table_args__ = (
        UniqueConstraint("rcept_no", name="uq_disclosure_rcept"),
        Index("ix_disclosure_stock_date", "stock_id", "rcept_dt"),
    )

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    
    # DART 기본 정보
    rcept_no = Column(String(50), nullable=False, unique=True)  # 접수번호
    rcept_dt = Column(Date, nullable=False, index=True)         # 접수일자
    corp_code = Column(String(10))                              # 회사 코드
    corp_name = Column(String(200))                             # 회사명
    
    # 공시 정보
    report_nm = Column(String(500))                             # 보고서명
    flr_nm = Column(String(200))                                # 공시제출인명
    rm = Column(Text)                                           # 비고
    
    # 분류
    disclosure_type = Column(String(100), index=True)           # 공시 유형 (실적, 증자, 자사주 등)
    disclosure_category = Column(String(50))                    # 대분류 (major, regular 등)
    
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    stock = relationship("Stock")


# ═══════════════════════════════════════════
# Research Reports (증권사 리포트)
# ═══════════════════════════════════════════
class ResearchReport(Base):
    """증권사 리포트"""
    __tablename__ = "research_reports"
    __table_args__ = (
        UniqueConstraint("stock_id", "firm", "report_date", "title", name="uq_report"),
        Index("ix_report_stock_date", "stock_id", "report_date"),
        Index("ix_report_firm", "firm"),
    )
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    
    # 리포트 정보
    firm = Column(String(100), nullable=False)      # 증권사
    analyst = Column(String(100))                   # 애널리스트
    report_date = Column(Date, nullable=False, index=True)  # 발행일
    
    # 투자 의견
    opinion = Column(String(20))                    # 매수/중립/매도/BUY/HOLD/SELL
    target_price = Column(Float)                    # 목표주가
    current_price = Column(Float)                   # 발행 시점 현재가
    
    # 내용
    title = Column(String(500), nullable=False)
    summary = Column(Text)                          # 요약
    pdf_url = Column(String(500))                   # PDF 링크
    source_url = Column(String(500))                # 원문 링크
    
    # 메타데이터
    is_processed = Column(Boolean, default=False)   # AI 분석 여부
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    stock = relationship("Stock")


# ═══════════════════════════════════════════
# Pipeline Tracking
# ═══════════════════════════════════════════
class PipelineRun(Base):
    """파이프라인 실행 이력"""
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    pipeline_name = Column(String(50), nullable=False)  # news, fundamentals, dynamics, macro
    status = Column(String(20), nullable=False)  # running, success, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    records_collected = Column(Integer, default=0)
    error_message = Column(Text)
    config_snapshot = Column(JSON)  # 실행 시 설정 스냅샷
