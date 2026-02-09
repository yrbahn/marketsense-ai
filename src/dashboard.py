"""
MarketSenseAI 2.0 - Data Dashboard

수집된 데이터를 시각화하는 Streamlit 대시보드

Usage:
  streamlit run src/dashboard.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func

from src.storage.database import Database
from src.storage.models import (
    Stock, NewsArticle, FinancialStatement, SECFiling,
    EarningsCall, PriceData, TechnicalIndicator,
    MacroReport, MacroIndicator, PipelineRun
)
from src.utils.helpers import load_config

# ─────────────────────────────────────
# Page Config
# ─────────────────────────────────────
st.set_page_config(
    page_title="MarketSenseAI Dashboard",
    page_icon="📊",
    layout="wide",
)

@st.cache_resource
def get_db():
    config = load_config()
    db_url = config.get("database", {}).get("url", "sqlite:///data/marketsense.db")
    return Database(db_url)


def main():
    st.title("📊 MarketSenseAI 2.0 - Data Dashboard")

    db = get_db()
    session = db.get_new_session()

    try:
        # ═══════════════════════════════════
        # Sidebar: Navigation
        # ═══════════════════════════════════
        page = st.sidebar.radio("📂 Navigation", [
            "🏠 Overview",
            "📰 News",
            "🏦 Fundamentals",
            "📈 Price & Indicators",
            "🌍 Macro",
            "🤖 AI Analysis",
            "⚙️ Pipeline Runs",
        ])

        if page == "🏠 Overview":
            render_overview(session)
        elif page == "📰 News":
            render_news(session)
        elif page == "🏦 Fundamentals":
            render_fundamentals(session)
        elif page == "📈 Price & Indicators":
            render_dynamics(session)
        elif page == "🌍 Macro":
            render_macro(session)
        elif page == "🤖 AI Analysis":
            render_ai_analysis(session)
        elif page == "⚙️ Pipeline Runs":
            render_pipeline_runs(session)

    finally:
        session.close()


# ═══════════════════════════════════════
# Overview Page
# ═══════════════════════════════════════
def render_overview(session):
    st.header("🏠 데이터 수집 현황")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        count = session.query(Stock).filter_by(is_active=True).count()
        st.metric("🏢 종목 수", f"{count:,}")
    with col2:
        count = session.query(NewsArticle).count()
        st.metric("📰 뉴스 기사", f"{count:,}")
    with col3:
        count = session.query(PriceData).count()
        st.metric("📈 주가 데이터", f"{count:,}")
    with col4:
        count = session.query(MacroReport).count()
        st.metric("🌍 매크로 보고서", f"{count:,}")

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        count = session.query(FinancialStatement).count()
        st.metric("📋 재무제표", f"{count:,}")
    with col2:
        count = session.query(SECFiling).count()
        st.metric("📄 SEC Filings", f"{count:,}")
    with col3:
        count = session.query(EarningsCall).count()
        st.metric("🎤 Earnings Calls", f"{count:,}")
    with col4:
        count = session.query(MacroIndicator).count()
        st.metric("📉 매크로 지표", f"{count:,}")

    # Recent pipeline runs
    st.subheader("⚙️ 최근 파이프라인 실행")
    runs = session.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(10).all()
    if runs:
        df = pd.DataFrame([{
            "파이프라인": r.pipeline_name,
            "상태": "✅" if r.status == "success" else "❌" if r.status == "failed" else "🔄",
            "수집 건수": r.records_collected or 0,
            "시작": r.started_at,
            "종료": r.finished_at,
        } for r in runs])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("아직 파이프라인 실행 이력이 없습니다.")

    # Stocks by sector
    st.subheader("🏢 섹터별 종목 분포")
    sectors = session.query(
        Stock.sector, func.count(Stock.id)
    ).filter(Stock.is_active == True).group_by(Stock.sector).all()
    if sectors:
        df = pd.DataFrame(sectors, columns=["섹터", "종목 수"])
        df = df.sort_values("종목 수", ascending=True)
        st.bar_chart(df.set_index("섹터"))


# ═══════════════════════════════════════
# News Page
# ═══════════════════════════════════════
def render_news(session):
    st.header("📰 뉴스 데이터")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        stocks = session.query(Stock).filter_by(is_active=True).order_by(Stock.ticker).all()
        ticker_options = ["전체"] + [f"{s.ticker} - {s.name}" for s in stocks]
        selected = st.selectbox("종목", ticker_options)
    with col2:
        source_filter = st.selectbox("소스", ["전체", "finnhub", "newsapi", "rss"])
    with col3:
        days = st.slider("최근 N일", 1, 30, 7)

    # Query
    query = session.query(NewsArticle)
    if selected != "전체":
        ticker = selected.split(" - ")[0]
        query = query.filter(NewsArticle.ticker == ticker)
    if source_filter != "전체":
        query = query.filter(NewsArticle.source == source_filter)
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = query.filter(NewsArticle.published_at >= cutoff)

    articles = query.order_by(NewsArticle.published_at.desc()).limit(100).all()

    st.info(f"📰 {len(articles)}건 표시 (최대 100건)")

    for a in articles:
        with st.expander(f"[{a.source}] {a.title}", expanded=False):
            st.write(f"**날짜:** {a.published_at}")
            st.write(f"**티커:** {a.ticker}")
            if a.summary:
                st.write(f"**요약:** {a.summary[:500]}")
            if a.url:
                st.write(f"🔗 [원문 링크]({a.url})")


# ═══════════════════════════════════════
# Fundamentals Page
# ═══════════════════════════════════════
def render_fundamentals(session):
    st.header("🏦 재무 데이터")

    stocks = session.query(Stock).filter_by(is_active=True).order_by(Stock.ticker).all()
    selected = st.selectbox("종목 선택", [f"{s.ticker} - {s.name}" for s in stocks])
    ticker = selected.split(" - ")[0]
    stock = session.query(Stock).filter_by(ticker=ticker).first()

    if not stock:
        return

    tab1, tab2, tab3 = st.tabs(["📋 재무제표", "📄 SEC Filings", "🎤 Earnings Calls"])

    with tab1:
        stmts = session.query(FinancialStatement).filter_by(
            stock_id=stock.id
        ).order_by(FinancialStatement.period_end.desc()).all()

        if stmts:
            df = pd.DataFrame([{
                "유형": s.statement_type,
                "기간": s.period_end,
                "매출": f"${s.revenue/1e9:.1f}B" if s.revenue else "N/A",
                "순이익": f"${s.net_income/1e9:.1f}B" if s.net_income else "N/A",
                "영업이익": f"${s.operating_income/1e9:.1f}B" if s.operating_income else "N/A",
                "EPS": f"${s.eps:.2f}" if s.eps else "N/A",
            } for s in stmts])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("재무제표 데이터 없음")

    with tab2:
        filings = session.query(SECFiling).filter_by(
            stock_id=stock.id
        ).order_by(SECFiling.filing_date.desc()).all()

        if filings:
            for f in filings:
                with st.expander(f"[{f.filing_type}] {f.filing_date} (Accession: {f.accession_number})"):
                    if f.file_url:
                        st.write(f"🔗 [SEC 원문]({f.file_url})")
                    if f.raw_text:
                        st.text_area("본문 (일부)", f.raw_text[:3000], height=200)
        else:
            st.info("SEC Filing 데이터 없음")

    with tab3:
        calls = session.query(EarningsCall).filter_by(
            stock_id=stock.id
        ).order_by(EarningsCall.call_date.desc()).all()

        if calls:
            for c in calls:
                with st.expander(f"{c.call_date} - {c.title or 'Earnings Call'}"):
                    if c.full_transcript:
                        st.text_area("트랜스크립트", c.full_transcript[:5000], height=300)
        else:
            st.info("Earnings Call 데이터 없음")


# ═══════════════════════════════════════
# Price & Indicators Page
# ═══════════════════════════════════════
def render_dynamics(session):
    st.header("📈 주가 & 기술적 지표")

    stocks = session.query(Stock).filter_by(is_active=True).order_by(Stock.ticker).all()
    selected = st.selectbox("종목 선택", [f"{s.ticker} - {s.name}" for s in stocks])
    ticker = selected.split(" - ")[0]
    stock = session.query(Stock).filter_by(ticker=ticker).first()

    if not stock:
        return

    days = st.slider("기간 (일)", 30, 365, 90)
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Price chart
    prices = session.query(PriceData).filter(
        PriceData.stock_id == stock.id,
        PriceData.date >= cutoff.date()
    ).order_by(PriceData.date).all()

    if prices:
        df = pd.DataFrame([{
            "date": p.date,
            "Close": p.close,
            "Volume": p.volume,
        } for p in prices]).set_index("date")

        st.subheader(f"💰 {ticker} 주가")
        st.line_chart(df["Close"])

        st.subheader("📊 거래량")
        st.bar_chart(df["Volume"])

        # Technical indicators
        indicators = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id,
            TechnicalIndicator.date >= cutoff.date()
        ).order_by(TechnicalIndicator.date).all()

        if indicators:
            ti_df = pd.DataFrame([{
                "date": t.date,
                "RSI(14)": t.rsi_14,
                "MACD": t.macd,
                "Signal": t.macd_signal,
                "Volatility(20d)": t.volatility_20d,
            } for t in indicators]).set_index("date")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("RSI (14)")
                st.line_chart(ti_df["RSI(14)"])
            with col2:
                st.subheader("MACD")
                st.line_chart(ti_df[["MACD", "Signal"]])

            # Latest indicators
            latest = indicators[-1]
            st.subheader("📋 최신 지표")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("RSI(14)", f"{latest.rsi_14:.1f}" if latest.rsi_14 else "N/A")
            with col2:
                st.metric("SMA(20)", f"${latest.sma_20:,.2f}" if latest.sma_20 else "N/A")
            with col3:
                st.metric("ATR(14)", f"${latest.atr_14:,.2f}" if latest.atr_14 else "N/A")
            with col4:
                st.metric("변동성(20d)", f"{latest.volatility_20d:.1%}" if latest.volatility_20d else "N/A")
    else:
        st.info("주가 데이터 없음")


# ═══════════════════════════════════════
# Macro Page
# ═══════════════════════════════════════
def render_macro(session):
    st.header("🌍 매크로 경제 데이터")

    tab1, tab2 = st.tabs(["📉 경제 지표", "📄 보고서"])

    with tab1:
        series_list = session.query(
            MacroIndicator.series_id, MacroIndicator.series_name
        ).distinct().all()

        if series_list:
            options = {f"{s[0]} - {s[1] or s[0]}": s[0] for s in series_list}
            selected = st.multiselect("지표 선택", list(options.keys()), default=list(options.keys())[:3])

            for sel in selected:
                series_id = options[sel]
                data = session.query(MacroIndicator).filter_by(
                    series_id=series_id
                ).order_by(MacroIndicator.date).all()

                if data:
                    df = pd.DataFrame([{"date": d.date, "value": d.value} for d in data]).set_index("date")
                    st.subheader(sel)
                    st.line_chart(df)
        else:
            st.info("매크로 지표 데이터 없음")

    with tab2:
        reports = session.query(MacroReport).order_by(MacroReport.published_at.desc()).limit(50).all()
        if reports:
            for r in reports:
                with st.expander(f"[{r.source_name}] {r.title} ({r.published_at})"):
                    if r.summary:
                        st.write(f"**요약:** {r.summary[:1000]}")
                    if r.raw_text:
                        st.text_area("본문", r.raw_text[:3000], height=200, key=f"macro_{r.id}")
                    if r.source_url:
                        st.write(f"🔗 [원문]({r.source_url})")
        else:
            st.info("매크로 보고서 없음")


# ═══════════════════════════════════════
# Pipeline Runs Page
# ═══════════════════════════════════════
def render_pipeline_runs(session):
    st.header("⚙️ 파이프라인 실행 이력")

    runs = session.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(50).all()
    if runs:
        df = pd.DataFrame([{
            "ID": r.id,
            "파이프라인": r.pipeline_name,
            "상태": r.status,
            "수집 건수": r.records_collected or 0,
            "시작": r.started_at,
            "종료": r.finished_at,
            "에러": r.error_message or "",
        } for r in runs])
        st.dataframe(df, use_container_width=True)

        # Stats
        st.subheader("📊 수집 통계")
        stats_df = df.groupby("파이프라인").agg(
            실행횟수=("ID", "count"),
            총수집=("수집 건수", "sum"),
            성공률=("상태", lambda x: f"{(x=='success').mean():.0%}"),
        )
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("파이프라인 실행 이력 없음")


# ═══════════════════════════════════════
# AI Analysis Page
# ═══════════════════════════════════════
def render_ai_analysis(session):
    st.header("🤖 AI 에이전트 분석")
    
    st.info("💡 Gemini API를 사용하여 종목을 분석합니다")
    
    # Load agents (lazy import)
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        from src.agents import NewsAgent, FundamentalsAgent, DynamicsAgent, MacroAgent, SignalAgent
        
        # Ticker selection
        stocks = session.query(Stock).filter_by(is_active=True).order_by(Stock.name).all()
        ticker_options = {f"{s.name} ({s.ticker})": s.ticker for s in stocks[:100]}  # 상위 100개만
        
        selected = st.selectbox("📊 종목 선택", options=ticker_options.keys())
        ticker = ticker_options[selected] if selected else None
        
        if not ticker:
            st.warning("종목을 선택하세요")
            return
        
        # Agent selection
        agent_type = st.radio(
            "🤖 분석 에이전트 선택",
            ["📰 뉴스 분석", "💰 재무 분석", "📈 기술적 분석", "🎯 종합 분석"],
            horizontal=True
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            analyze_btn = st.button("▶️ 분석 시작", type="primary", use_container_width=True)
        
        if analyze_btn:
            config = load_config()
            db = get_db()
            
            with st.spinner("🤖 AI 분석 중..."):
                try:
                    if agent_type == "📰 뉴스 분석":
                        agent = NewsAgent(config, db)
                        result = agent.analyze(ticker)
                        
                        if "error" not in result:
                            st.success("✅ 뉴스 분석 완료")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                sentiment_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}
                                st.metric("감성", f"{sentiment_emoji.get(result.get('sentiment'), '?')} {result.get('sentiment', 'N/A')}")
                            with col2:
                                st.metric("신뢰도", f"{result.get('confidence', 0):.0%}")
                            with col3:
                                st.metric("영향도", result.get('impact', 'N/A'))
                            
                            st.subheader("📝 요약")
                            st.write(result.get('summary', 'N/A'))
                            
                            st.subheader("🔑 주요 이벤트")
                            for event in result.get('key_events', []):
                                st.markdown(f"- {event}")
                            
                            st.subheader("🧠 분석 근거")
                            st.write(result.get('reasoning', 'N/A'))
                            
                            with st.expander("📄 전체 JSON 결과"):
                                st.json(result)
                        else:
                            st.error(f"❌ 오류: {result['error']}")
                    
                    elif agent_type == "💰 재무 분석":
                        agent = FundamentalsAgent(config, db)
                        result = agent.analyze(ticker)
                        
                        if "error" not in result:
                            st.success("✅ 재무 분석 완료")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("밸류에이션", result.get('valuation', 'N/A'))
                            with col2:
                                st.metric("재무 건전성", result.get('financial_health', 'N/A'))
                            with col3:
                                st.metric("신뢰도", f"{result.get('confidence', 0):.0%}")
                            
                            st.subheader("📊 핵심 지표")
                            metrics = result.get('key_metrics', {})
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**수익성**: {metrics.get('profitability', 'N/A')}")
                            with col2:
                                st.write(f"**성장성**: {metrics.get('growth', 'N/A')}")
                            with col3:
                                st.write(f"**안정성**: {metrics.get('stability', 'N/A')}")
                            
                            st.subheader("📝 요약")
                            st.write(result.get('summary', 'N/A'))
                            
                            st.subheader("🧠 분석 근거")
                            st.write(result.get('reasoning', 'N/A'))
                            
                            with st.expander("📄 전체 JSON 결과"):
                                st.json(result)
                        else:
                            st.error(f"❌ 오류: {result['error']}")
                    
                    elif agent_type == "📈 기술적 분석":
                        agent = DynamicsAgent(config, db)
                        result = agent.analyze(ticker)
                        
                        if "error" not in result:
                            st.success("✅ 기술적 분석 완료")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("현재가", f"{result.get('current_price', 0):,.0f}원")
                            with col2:
                                trend_emoji = {"uptrend": "📈", "downtrend": "📉", "sideways": "➡️"}
                                st.metric("추세", f"{trend_emoji.get(result.get('trend'), '?')} {result.get('trend', 'N/A')}")
                            with col3:
                                signal_emoji = {"buy": "💚", "sell": "🔴", "hold": "🟡"}
                                st.metric("신호", f"{signal_emoji.get(result.get('signal'), '?')} {result.get('signal', 'N/A')}")
                            with col4:
                                st.metric("신뢰도", f"{result.get('confidence', 0):.0%}")
                            
                            st.subheader("🎯 주요 가격대")
                            levels = result.get('key_levels', {})
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**지지선**")
                                for level in levels.get('support', []):
                                    st.write(f"- {level:,.0f}원")
                            with col2:
                                st.write("**저항선**")
                                for level in levels.get('resistance', []):
                                    st.write(f"- {level:,.0f}원")
                            
                            st.subheader("📊 지표 해석")
                            st.write(result.get('indicators_summary', 'N/A'))
                            
                            st.subheader("🧠 분석 근거")
                            st.write(result.get('reasoning', 'N/A'))
                            
                            with st.expander("📄 전체 JSON 결과"):
                                st.json(result)
                        else:
                            st.error(f"❌ 오류: {result['error']}")
                    
                    elif agent_type == "🎯 종합 분석":
                        st.info("🔄 4개 에이전트 순차 실행 중...")
                        
                        # News
                        with st.spinner("📰 뉴스 분석 중..."):
                            news_agent = NewsAgent(config, db)
                            news_result = news_agent.analyze(ticker)
                        st.success("✅ 뉴스 분석 완료")
                        
                        # Fundamentals
                        with st.spinner("💰 재무 분석 중..."):
                            fund_agent = FundamentalsAgent(config, db)
                            fund_result = fund_agent.analyze(ticker)
                        st.success("✅ 재무 분석 완료")
                        
                        # Dynamics
                        with st.spinner("📈 기술적 분석 중..."):
                            dyn_agent = DynamicsAgent(config, db)
                            dyn_result = dyn_agent.analyze(ticker)
                        st.success("✅ 기술적 분석 완료")
                        
                        # Macro
                        with st.spinner("🌍 거시경제 분석 중..."):
                            macro_agent = MacroAgent(config, db)
                            macro_result = macro_agent.analyze()
                        st.success("✅ 거시경제 분석 완료")
                        
                        # Signal aggregation
                        with st.spinner("🎯 최종 신호 통합 중..."):
                            signal_agent = SignalAgent(config, db)
                            final_result = signal_agent.aggregate(
                                ticker,
                                news_result=news_result,
                                fundamentals_result=fund_result,
                                dynamics_result=dyn_result,
                                macro_result=macro_result,
                            )
                        
                        st.success("✅ 종합 분석 완료!")
                        
                        st.divider()
                        
                        # Final signal
                        st.subheader("🎯 최종 투자 신호")
                        
                        if "error" not in final_result:
                            signal = final_result.get('signal', 'N/A')
                            signal_colors = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("신호", f"{signal_colors.get(signal, '?')} {signal}")
                            with col2:
                                st.metric("신뢰도", f"{final_result.get('confidence', 0):.0%}")
                            with col3:
                                st.metric("리스크", final_result.get('risk_level', 'N/A'))
                            with col4:
                                st.metric("투자기간", final_result.get('time_horizon', 'N/A'))
                            
                            if final_result.get('target_price'):
                                st.metric("🎯 목표가", f"{final_result['target_price']:,.0f}원")
                            
                            st.subheader("📝 투자 의견")
                            st.write(final_result.get('summary', 'N/A'))
                            
                            st.subheader("🧠 통합 분석 근거")
                            st.write(final_result.get('reasoning', 'N/A'))
                            
                            # Individual results
                            with st.expander("📰 뉴스 분석 상세"):
                                st.json(news_result)
                            with st.expander("💰 재무 분석 상세"):
                                st.json(fund_result)
                            with st.expander("📈 기술적 분석 상세"):
                                st.json(dyn_result)
                            with st.expander("🌍 거시경제 분석 상세"):
                                st.json(macro_result)
                        else:
                            st.error(f"❌ 통합 분석 오류: {final_result.get('error')}")
                
                except Exception as e:
                    st.error(f"❌ 분석 실패: {e}")
                    import traceback
                    with st.expander("🐛 에러 상세"):
                        st.code(traceback.format_exc())
    
    except ImportError as e:
        st.error(f"❌ 에이전트 모듈 로드 실패: {e}")
        st.info("💡 `GOOGLE_API_KEY` 환경변수를 설정했는지 확인하세요")


if __name__ == "__main__":
    main()
