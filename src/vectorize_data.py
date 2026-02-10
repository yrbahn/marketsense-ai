#!/usr/bin/env python3
"""데이터 벡터화 스크립트

DB의 뉴스와 재무제표를 ChromaDB로 벡터화
"""
import sys
import logging
from src.storage.database import init_db
from src.storage.models import NewsArticle, FinancialStatement
from src.utils.helpers import load_config
from src.rag import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("marketsense")


def vectorize_news(db, vs: VectorStore, limit: int = None):
    """뉴스 벡터화
    
    Args:
        db: 데이터베이스
        vs: VectorStore
        limit: 처리할 개수 (None=전체)
    """
    logger.info("뉴스 벡터화 시작...")
    
    with db.get_session() as session:
        query = session.query(NewsArticle)
        
        if limit:
            query = query.limit(limit)
        
        articles = query.all()
        
        logger.info(f"뉴스 {len(articles)}개 로드 완료")
        
        # 배치 처리
        batch_size = 100
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            
            # Dict 변환
            article_dicts = []
            for article in batch:
                article_dicts.append({
                    'id': str(article.id),
                    'ticker': article.ticker or '',
                    'title': article.title or '',
                    'content': article.content or article.summary or '',
                    'source': article.source or '',
                    'published_at': article.published_at,
                    'url': article.url or ''
                })
            
            # 벡터화
            vs.add_news(article_dicts)
            
            logger.info(f"진행: {min(i+batch_size, len(articles))}/{len(articles)}")
    
    logger.info("✅ 뉴스 벡터화 완료!")


def vectorize_financials(db, vs: VectorStore, limit: int = None):
    """재무제표 벡터화
    
    Args:
        db: 데이터베이스
        vs: VectorStore
        limit: 처리할 개수 (None=전체)
    """
    logger.info("재무제표 벡터화 시작...")
    
    with db.get_session() as session:
        query = session.query(FinancialStatement).filter(
            FinancialStatement.statement_type == 'income'  # 손익계산서만
        )
        
        if limit:
            query = query.limit(limit)
        
        statements = query.all()
        
        logger.info(f"재무제표 {len(statements)}개 로드 완료")
        
        # 배치 처리
        batch_size = 50
        for i in range(0, len(statements), batch_size):
            batch = statements[i:i+batch_size]
            
            # Dict 변환 + 요약 생성
            stmt_dicts = []
            for stmt in batch:
                # 종목 조회
                stock = stmt.stock
                ticker = stock.ticker if stock else ''
                name = stock.name if stock else ''
                
                # 요약 텍스트 생성
                summary = f"{name} ({ticker}) {stmt.period_end} 재무제표\n"
                
                if stmt.revenue:
                    summary += f"매출: {stmt.revenue:,.0f}원\n"
                if stmt.operating_income:
                    summary += f"영업이익: {stmt.operating_income:,.0f}원\n"
                if stmt.net_income:
                    summary += f"당기순이익: {stmt.net_income:,.0f}원\n"
                if stmt.total_assets:
                    summary += f"총자산: {stmt.total_assets:,.0f}원\n"
                if stmt.total_liabilities:
                    summary += f"총부채: {stmt.total_liabilities:,.0f}원\n"
                if stmt.total_equity:
                    summary += f"자본총계: {stmt.total_equity:,.0f}원\n"
                
                stmt_dicts.append({
                    'id': str(stmt.id),
                    'ticker': ticker,
                    'period': str(stmt.period_end),
                    'statement_type': stmt.statement_type,
                    'summary': summary
                })
            
            # 벡터화
            vs.add_financials(stmt_dicts)
            
            logger.info(f"진행: {min(i+batch_size, len(statements))}/{len(statements)}")
    
    logger.info("✅ 재무제표 벡터화 완료!")


def main():
    """메인"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--news', action='store_true', help='뉴스 벡터화')
    parser.add_argument('--financials', action='store_true', help='재무제표 벡터화')
    parser.add_argument('--all', action='store_true', help='전체 벡터화')
    parser.add_argument('--limit', type=int, help='처리 개수 제한')
    
    args = parser.parse_args()
    
    # 설정 로드
    config = load_config()
    db = init_db(config)
    vs = VectorStore()
    
    # 실행
    if args.all or args.news:
        vectorize_news(db, vs, limit=args.limit)
    
    if args.all or args.financials:
        vectorize_financials(db, vs, limit=args.limit)
    
    # 통계
    stats = vs.get_stats()
    print()
    print("=" * 60)
    print("📊 벡터 DB 통계")
    print("=" * 60)
    print(f"뉴스: {stats['news_count']:,}개")
    print(f"재무: {stats['financials_count']:,}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
